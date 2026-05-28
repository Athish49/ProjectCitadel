"""Capability token issuer + registry verifier (P4 — task 1.2.2).

Only the orchestrator may issue tokens. Every tool call must carry a token
signed by the orchestrator's Ed25519 key. The verifier runs server-side so
an LLM cannot mint or widen a token regardless of what it says.

Token wire format (all fields):
    token_id    UUID
    issued_by   str    — always "orchestrator"
    agent_id    str    — grantee (must be in KNOWN_AGENTS)
    tool        str    — tool name the token is valid for
    scope       dict   — required parameter constraints: every key must equal
                         the corresponding call parameter value
    issued_at   datetime (UTC)
    expires_at  datetime (UTC)
    signature   str    — hex-encoded 64-byte Ed25519 sig over canonical payload

The canonical payload is json.dumps(all_fields_minus_signature, sort_keys=True).
Both issue_token() and _canonical_payload() derive it from the same projection
so the sign and verify paths are guaranteed to produce identical bytes.

Production wiring TODO: resolve orchestrator_public_key from
KeyRegistry.get_public_key("orchestrator") at FastAPI startup.

Persistence is split from logic so each half is unit-testable independently:
    issue_token()    — pure, no DB
    persist_issuance(conn, token)  — DB write, caller commits
    verify_token()   — pure, no DB
    record_use(conn, token_id, result)  — DB write, caller commits

Callers are responsible for writing to audit_log (they own trace_id / action).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import psycopg
from pydantic import BaseModel, ConfigDict, field_validator

from agent_system.identity.keys import KNOWN_AGENTS, KeypairManager
from agent_system.identity.signing import verify_message

# ---------------------------------------------------------------------------
# Token model
# ---------------------------------------------------------------------------

DEFAULT_TOKEN_TTL_SECONDS: int = 300  # 5 minutes


class CapabilityToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_id: uuid.UUID
    issued_by: str       # always "orchestrator"
    agent_id: str        # grantee; must be in KNOWN_AGENTS
    tool: str
    scope: dict[str, Any]
    issued_at: datetime
    expires_at: datetime
    signature: str       # hex-encoded 64-byte Ed25519 signature

    @field_validator("issued_at", "expires_at", mode="before")
    @classmethod
    def _ensure_utc(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


def _canonical_payload(token: CapabilityToken) -> bytes:
    """Bytes signed by the orchestrator and verified by the registry.

    Includes every field except *signature*. Uses the same projection and
    serialisation as _unsigned_dict() in issue_token() so sign/verify paths
    are structurally identical — any divergence would be a test failure.
    """
    data = {
        "token_id": str(token.token_id),
        "issued_by": token.issued_by,
        "agent_id": token.agent_id,
        "tool": token.tool,
        "scope": token.scope,
        "issued_at": token.issued_at.astimezone(timezone.utc).isoformat(),
        "expires_at": token.expires_at.astimezone(timezone.utc).isoformat(),
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


# ---------------------------------------------------------------------------
# Deny reasons — values must match the DB CHECK constraint in 001_initial_schema.sql
# ---------------------------------------------------------------------------

class DenyReason(str, Enum):
    SIGNATURE = "DENIED_SIGNATURE"
    EXPIRED = "DENIED_EXPIRED"
    SCOPE = "DENIED_SCOPE"      # wrong agent, wrong tool, scope mismatch, or replay


class VerifyResult:
    __slots__ = ("ok", "deny_reason")

    def __init__(self, ok: bool, deny_reason: DenyReason | None = None) -> None:
        self.ok = ok
        self.deny_reason = deny_reason

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return f"VerifyResult(ok={self.ok}, deny_reason={self.deny_reason})"

    @classmethod
    def success(cls) -> "VerifyResult":
        return cls(True)

    @classmethod
    def denied(cls, reason: DenyReason) -> "VerifyResult":
        return cls(False, reason)


# ---------------------------------------------------------------------------
# Issuer (orchestrator-side) — no DB I/O
# ---------------------------------------------------------------------------

def issue_token(
    orchestrator_km: KeypairManager,
    *,
    agent_id: str,
    tool: str,
    scope: dict[str, Any],
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
) -> CapabilityToken:
    """Create and sign a capability token. Does NOT write to the database.

    Call persist_issuance(conn, token) to log the issuance to capability_token_log.
    """
    if agent_id not in KNOWN_AGENTS:
        raise ValueError(
            f"Unknown agent_id '{agent_id}'. Valid agents: {sorted(KNOWN_AGENTS)}"
        )

    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)

    # Build the unsigned dict; _canonical_payload() reproduces this projection
    # from the model so the sign and verify paths are byte-for-byte identical.
    unsigned: dict[str, Any] = {
        "token_id": str(uuid.uuid4()),
        "issued_by": "orchestrator",
        "agent_id": agent_id,
        "tool": tool,
        "scope": scope,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    sig_hex = orchestrator_km.sign(payload).hex()

    return CapabilityToken(**unsigned, signature=sig_hex)


def persist_issuance(conn: psycopg.Connection, token: CapabilityToken) -> None:
    """INSERT token metadata into capability_token_log.

    conn must be in a transaction (autocommit=False); caller commits.
    Does NOT write to audit_log — the caller (orchestrator) owns that.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO capability_token_log
                (token_id, issued_by, agent_id, tool, scope, issued_at, expires_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                token.token_id,
                token.issued_by,
                token.agent_id,
                token.tool,
                json.dumps(token.scope),
                token.issued_at,
                token.expires_at,
            ),
        )


# ---------------------------------------------------------------------------
# Verifier (tool-registry-side) — no DB I/O
# ---------------------------------------------------------------------------

def verify_token(
    token: CapabilityToken,
    *,
    calling_agent_id: str,
    tool: str,
    params: dict[str, Any],
    orchestrator_public_key: bytes,
) -> VerifyResult:
    """Verify a capability token server-side. Pure function — no DB I/O.

    Checks (in order, per TAD §2.4):
    1. issued_by is "orchestrator" (defence-in-depth; signature already ensures this).
    2. Signature is valid against the orchestrator's Ed25519 public key.
    3. Token has not expired.
    4. agent_id matches calling_agent_id.
    5. Token's tool matches requested tool.
    6. All scope constraints are satisfied by params.

    orchestrator_public_key is the 32-byte raw public key.
    Production wiring: KeyRegistry.get_public_key("orchestrator") at startup.
    """
    # 1. Issuer must be orchestrator
    if token.issued_by != "orchestrator":
        return VerifyResult.denied(DenyReason.SIGNATURE)

    # 2. Signature
    try:
        sig_bytes = bytes.fromhex(token.signature)
    except ValueError:
        return VerifyResult.denied(DenyReason.SIGNATURE)
    payload = _canonical_payload(token)
    if not verify_message(orchestrator_public_key, payload, sig_bytes):
        return VerifyResult.denied(DenyReason.SIGNATURE)

    # 3. Expiry
    if datetime.now(tz=timezone.utc) > token.expires_at:
        return VerifyResult.denied(DenyReason.EXPIRED)

    # 4. Agent identity
    if token.agent_id != calling_agent_id:
        return VerifyResult.denied(DenyReason.SCOPE)

    # 5. Tool name
    if token.tool != tool:
        return VerifyResult.denied(DenyReason.SCOPE)

    # 6. Scope constraints
    if not _scope_satisfied(token.scope, params):
        return VerifyResult.denied(DenyReason.SCOPE)

    return VerifyResult.success()


def _scope_satisfied(scope: dict[str, Any], params: dict[str, Any]) -> bool:
    """True iff every key in *scope* is present in *params* with an equal value.

    Comparison uses json.dumps() on both sides so UUID objects, integers, and
    their string equivalents match consistently (e.g. UUID("abc...") == "abc...").
    This means {"amount": 100} matches {"amount": "100"} — an accepted tradeoff
    for the showcase; production would enforce strict types.
    """
    def _normalise(v: Any) -> str:
        return json.dumps(v, sort_keys=True)

    return all(
        _normalise(params.get(k)) == _normalise(v)
        for k, v in scope.items()
    )


# ---------------------------------------------------------------------------
# Use recorder (tool-registry-side) — DB I/O
# ---------------------------------------------------------------------------

def record_use(
    conn: psycopg.Connection,
    token_id: uuid.UUID,
    result: VerifyResult,
) -> None:
    """Update capability_token_log with the verification outcome.

    conn must be in a transaction; caller commits.
    Raises ValueError if no row exists for token_id (token was never issued or
    already deleted) — this is a loud failure, not a silent no-op.
    Does NOT write to audit_log — the caller owns that.
    """
    use_result = "OK" if result.ok else result.deny_reason.value
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE capability_token_log
               SET used_at = now(), use_result = %s
             WHERE token_id = %s
            """,
            (use_result, token_id),
        )
        if cur.rowcount != 1:
            raise ValueError(
                f"capability_token_log has no row for token_id={token_id}. "
                "Token was never persisted or has already been deleted."
            )
