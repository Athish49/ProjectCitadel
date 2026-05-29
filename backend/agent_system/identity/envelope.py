"""Signed inter-agent message envelope (P8 — task 2.2.2).

Public API:
  sign_envelope(km, *, target_agent, message_type, claim_id, payload,
                trace_id=None) -> SignedEnvelope
  verify_envelope(envelope, registry, *, replay_store=None) -> EnvelopeVerifyResult
  ReplayStore  — injectable in-memory nonce store (swap for Redis/DB in prod)

Wire format (TAD §3.1 subset):
  message_id   UUID — replay-protection nonce; unique per message
  trace_id     UUID | None
  source_agent str  — signer's agent_id (must be in KNOWN_AGENTS)
  target_agent str  — recipient's agent_id (must be in KNOWN_AGENTS)
  message_type str  — "task" | "task_result" | "event"
  claim_id     str
  payload      dict — actor output data (must be JSON-primitive)
  timestamp    datetime (UTC)
  signature    str  — hex-encoded 64-byte Ed25519 sig

Canonical payload for sign/verify:
  json.dumps(all_fields_except_signature, sort_keys=True, separators=(",",":"))
  with datetime → UTC isoformat and UUID → str(uuid).

Replay protection (attacks #40, #47):
  verify_envelope() checks, in order:
    1. source_agent's public key is in the registry; signature is valid.
    2. |now - timestamp| ≤ TIMESTAMP_WINDOW_SECONDS.
    3. message_id has not been seen before in this replay_store.

The default module-level ReplayStore is cleared on process restart.
In production, swap it for a Redis- or DB-backed implementation.

Callers must pass JSON-primitive payload values only (str, int, float, bool, None,
list, dict with primitive values). Non-primitive types (datetime, UUID) will cause
json.dumps to fail or produce non-deterministic output.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from agent_system.identity.keys import KNOWN_AGENTS, KeypairManager, KeyRegistry
from agent_system.identity.signing import verify_message


TIMESTAMP_WINDOW_SECONDS: int = 60


# ---------------------------------------------------------------------------
# Envelope model
# ---------------------------------------------------------------------------


class SignedEnvelope(BaseModel):
    """Signed inter-agent message (TAD §3.1 subset).

    All fields except *signature* form the canonical payload that is signed
    by the source agent's Ed25519 private key.

    payload must contain only JSON-primitive values (str, int, float, bool,
    None, list, nested dict). Non-primitive types will produce non-deterministic
    serialisation and break signature verification.
    """

    model_config = ConfigDict(frozen=True)

    message_id: uuid.UUID
    trace_id: uuid.UUID | None
    source_agent: str
    target_agent: str
    message_type: Literal["task", "task_result", "event"]
    claim_id: str
    payload: dict[str, Any]
    timestamp: datetime
    signature: str  # hex-encoded 64-byte Ed25519 sig

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ensure_utc(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @field_validator("source_agent", "target_agent")
    @classmethod
    def _known_agent(cls, v: str) -> str:
        if v not in KNOWN_AGENTS:
            raise ValueError(f"Unknown agent '{v}'. Valid: {sorted(KNOWN_AGENTS)}")
        return v


# ---------------------------------------------------------------------------
# Canonical serialisation (sign path and verify path share this projection)
# ---------------------------------------------------------------------------


def _canonical_bytes(envelope: SignedEnvelope) -> bytes:
    """Return the bytes signed by the source agent.

    Excludes the *signature* field. All other fields are included with
    deterministic serialisation: datetime → UTC isoformat, UUID → str.

    Must match the serialisation in sign_envelope() field-for-field and
    key-for-key; any divergence breaks signature verification.
    """
    def _ser(v: Any) -> Any:
        if isinstance(v, datetime):
            return v.astimezone(timezone.utc).isoformat()
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    data: dict[str, Any] = {
        "message_id": _ser(envelope.message_id),
        "trace_id": _ser(envelope.trace_id),
        "source_agent": envelope.source_agent,
        "target_agent": envelope.target_agent,
        "message_type": envelope.message_type,
        "claim_id": envelope.claim_id,
        "payload": envelope.payload,
        "timestamp": _ser(envelope.timestamp),
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


# ---------------------------------------------------------------------------
# Signing (source agent side)
# ---------------------------------------------------------------------------


def sign_envelope(
    km: KeypairManager,
    *,
    target_agent: str,
    message_type: Literal["task", "task_result", "event"],
    claim_id: str,
    payload: dict[str, Any],
    trace_id: uuid.UUID | None = None,
) -> SignedEnvelope:
    """Create and sign an inter-agent message envelope.

    source_agent is derived from km.agent_id.
    message_id and timestamp are assigned here (caller cannot supply them).

    payload must contain only JSON-primitive values — see module docstring.
    Raises pydantic.ValidationError if target_agent is not in KNOWN_AGENTS.
    """
    now = datetime.now(tz=timezone.utc)

    # Build the unsigned projection — _canonical_bytes() reproduces this from
    # the SignedEnvelope model so both paths are byte-for-byte identical.
    unsigned: dict[str, Any] = {
        "message_id": str(uuid.uuid4()),
        "trace_id": str(trace_id) if trace_id is not None else None,
        "source_agent": km.agent_id,
        "target_agent": target_agent,
        "message_type": message_type,
        "claim_id": claim_id,
        "payload": payload,
        "timestamp": now.isoformat(),
    }
    payload_bytes = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    sig_hex = km.sign(payload_bytes).hex()

    return SignedEnvelope(**unsigned, signature=sig_hex)


# ---------------------------------------------------------------------------
# Verification (recipient side)
# ---------------------------------------------------------------------------


class EnvelopeDenyReason(str, Enum):
    SIGNATURE = "DENIED_SIGNATURE"  # bad sig or source agent not in registry
    EXPIRED = "DENIED_EXPIRED"      # timestamp outside TIMESTAMP_WINDOW_SECONDS
    REPLAY = "DENIED_REPLAY"        # message_id already seen in this store


class EnvelopeVerifyResult:
    __slots__ = ("ok", "deny_reason")

    def __init__(self, ok: bool, deny_reason: EnvelopeDenyReason | None = None) -> None:
        self.ok = ok
        self.deny_reason = deny_reason

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self) -> str:
        return f"EnvelopeVerifyResult(ok={self.ok}, deny_reason={self.deny_reason})"

    @classmethod
    def success(cls) -> "EnvelopeVerifyResult":
        return cls(True)

    @classmethod
    def denied(cls, reason: EnvelopeDenyReason) -> "EnvelopeVerifyResult":
        return cls(False, reason)


class ReplayStore:
    """Thread-unsafe in-memory nonce store (single-process demo).

    Pass a fresh instance to each independent test or session to prevent
    cross-context pollution. In production, replace with a Redis- or
    DB-backed store that persists across processes.
    """

    def __init__(self) -> None:
        self._seen: set[uuid.UUID] = set()

    def check_and_record(self, message_id: uuid.UUID) -> bool:
        """Return True iff *message_id* is new; record it to block future replays."""
        if message_id in self._seen:
            return False
        self._seen.add(message_id)
        return True


# Module-level default; cleared on process restart (single-process demo).
_DEFAULT_REPLAY_STORE = ReplayStore()


def verify_envelope(
    envelope: SignedEnvelope,
    registry: KeyRegistry,
    *,
    replay_store: ReplayStore | None = None,
) -> EnvelopeVerifyResult:
    """Verify an inter-agent message envelope.

    Checks (in order):
    1. source_agent is in *registry* and signature is valid (attack #40 — impersonation).
    2. |now - timestamp| ≤ TIMESTAMP_WINDOW_SECONDS (stale/future message guard).
    3. message_id not already in *replay_store* (attack #47 — replay).

    Uses the module-level _DEFAULT_REPLAY_STORE if replay_store is None.
    Pass an explicit ReplayStore() in tests and per-session handlers to
    avoid cross-context pollution.
    """
    store = replay_store if replay_store is not None else _DEFAULT_REPLAY_STORE

    # 1. Signature
    try:
        pub_key = registry.get_public_key(envelope.source_agent)
    except KeyError:
        return EnvelopeVerifyResult.denied(EnvelopeDenyReason.SIGNATURE)

    try:
        sig_bytes = bytes.fromhex(envelope.signature)
    except ValueError:
        return EnvelopeVerifyResult.denied(EnvelopeDenyReason.SIGNATURE)

    canonical = _canonical_bytes(envelope)
    if not verify_message(pub_key, canonical, sig_bytes):
        return EnvelopeVerifyResult.denied(EnvelopeDenyReason.SIGNATURE)

    # 2. Timestamp freshness
    now = datetime.now(tz=timezone.utc)
    age_seconds = abs((now - envelope.timestamp.astimezone(timezone.utc)).total_seconds())
    if age_seconds > TIMESTAMP_WINDOW_SECONDS:
        return EnvelopeVerifyResult.denied(EnvelopeDenyReason.EXPIRED)

    # 3. Replay
    if not store.check_and_record(envelope.message_id):
        return EnvelopeVerifyResult.denied(EnvelopeDenyReason.REPLAY)

    return EnvelopeVerifyResult.success()
