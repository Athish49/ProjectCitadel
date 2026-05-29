"""Tool registry with server-side capability-token enforcement (P4 — task 1.2.3).

Every tool invocation must carry a CapabilityToken signed by the orchestrator.
The registry verifies the token, checks for replay, dispatches to the handler,
records the outcome in capability_token_log, and writes an audit row — all in
the same database transaction so the audit is always consistent with the outcome.

Replay protection: the row is locked with SELECT … FOR UPDATE before checking
used_at, so concurrent identical invocations both hit the lock; only the first
gets used_at=NULL and proceeds to call the handler.

Invocation flow (section numbers match TAD §2.4):
  1. Tool name must be registered.
  2. verify_token() — pure check (sig, expiry, agent, tool, scope).
  3. SELECT FOR UPDATE on capability_token_log:
       • no row   → security event (unissued/forged token), deny SCOPE
       • used_at set → security event (replay), deny SCOPE
  4. Call handler; wrap exceptions.
  5. record_use() + append_log().

The caller (orchestrator or service layer) must commit conn after invoke()
returns. All DB writes share the same open transaction.

Callers must NOT pass raw params into audit details — they may contain
CONFIDENTIAL data. The registry logs only params_keys and the scope dict
(already non-secret by design).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import psycopg

from audit.chain import append_log
from agent_system.ifc.labels import Labeled
from agent_system.tools.capability_tokens import (
    CapabilityToken,
    DenyReason,
    VerifyResult,
    record_use,
    verify_token,
)


# ---------------------------------------------------------------------------
# Invocation result
# ---------------------------------------------------------------------------

@dataclass
class InvokeResult:
    ok: bool
    value: Any = None
    deny_reason: DenyReason | None = None
    handler_error: Exception | None = None
    log_id: int = 0

    def __bool__(self) -> bool:
        return self.ok

    @classmethod
    def success(cls, value: Any, log_id: int) -> "InvokeResult":
        return cls(ok=True, value=value, log_id=log_id)

    @classmethod
    def denied(cls, reason: DenyReason, log_id: int) -> "InvokeResult":
        return cls(ok=False, deny_reason=reason, log_id=log_id)

    @classmethod
    def error(cls, exc: Exception, log_id: int) -> "InvokeResult":
        return cls(ok=False, handler_error=exc, log_id=log_id)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Registers tool handlers and enforces capability-token access control.

    Usage:
        registry = ToolRegistry()
        registry.register("approve_claim", approve_claim_handler)

        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id="claims_processor",
            tool_name="approve_claim",
            params={"claim_id": "CLM-001", "amount": 4000},
            orchestrator_public_key=pub_key,
        )
        conn.commit()
    """

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a tool handler under *name*."""
        self._tools[name] = handler

    def invoke(
        self,
        conn: psycopg.Connection,
        *,
        token: CapabilityToken,
        calling_agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        orchestrator_public_key: bytes,
        trace_id: uuid.UUID | None = None,
    ) -> InvokeResult:
        """Verify token, dispatch to handler, and record outcome.

        All DB writes share conn's open transaction; caller must commit.
        Never raises — all failure paths return a denied InvokeResult.
        """
        token_id_str = str(token.token_id)
        base_details: dict[str, Any] = {
            "token_id": token_id_str,
            "tool": tool_name,
            "params_keys": sorted(params.keys()),
        }

        # ── Step 1: tool must be registered ─────────────────────────────────
        if tool_name not in self._tools:
            log_id = append_log(
                conn,
                agent_id=calling_agent_id,
                action="tool_call_denied",
                target=f"tools/{tool_name}",
                data_label="CONFIDENTIAL",
                trace_id=trace_id,
                details={**base_details, "deny_reason": DenyReason.SCOPE.value, "cause": "unknown_tool"},
                security_event=False,
            )
            return InvokeResult.denied(DenyReason.SCOPE, log_id=log_id)

        # ── Step 2: verify token (pure — no DB) ─────────────────────────────
        verify_result = verify_token(
            token,
            calling_agent_id=calling_agent_id,
            tool=tool_name,
            params=params,
            orchestrator_public_key=orchestrator_public_key,
        )

        if not verify_result:
            # Best-effort: record the denial in capability_token_log if the
            # row was actually issued by the orchestrator.  Forged tokens have
            # no row; swallow the ValueError silently — audit_log is the
            # authoritative record.
            _try_record_use(conn, token.token_id, verify_result)
            is_security_event = verify_result.deny_reason == DenyReason.SIGNATURE
            log_id = append_log(
                conn,
                agent_id=calling_agent_id,
                action="tool_call_denied",
                target=f"tools/{tool_name}",
                data_label="CONFIDENTIAL",
                trace_id=trace_id,
                details={**base_details, "deny_reason": verify_result.deny_reason.value},
                security_event=is_security_event,
            )
            return InvokeResult.denied(verify_result.deny_reason, log_id=log_id)

        # ── Step 3: replay check (SELECT FOR UPDATE) ─────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                "SELECT used_at FROM capability_token_log WHERE token_id = %s FOR UPDATE",
                (token.token_id,),
            )
            row = cur.fetchone()

        if row is None:
            log_id = append_log(
                conn,
                agent_id=calling_agent_id,
                action="tool_call_denied",
                target=f"tools/{tool_name}",
                data_label="CONFIDENTIAL",
                trace_id=trace_id,
                details={**base_details, "deny_reason": DenyReason.SCOPE.value, "cause": "unissued_token"},
                security_event=True,
            )
            return InvokeResult.denied(DenyReason.SCOPE, log_id=log_id)

        if row[0] is not None:  # used_at already set → replay attempt
            log_id = append_log(
                conn,
                agent_id=calling_agent_id,
                action="tool_call_replay_denied",
                target=f"tools/{tool_name}",
                data_label="CONFIDENTIAL",
                trace_id=trace_id,
                details={**base_details, "deny_reason": DenyReason.SCOPE.value, "cause": "replay"},
                security_event=True,
            )
            return InvokeResult.denied(DenyReason.SCOPE, log_id=log_id)

        # ── Step 4: call handler ─────────────────────────────────────────────
        handler = self._tools[tool_name]
        try:
            value = handler(**params)
        except Exception as exc:
            # Token gate passed; handler error is a tool-side failure, not a
            # security event.  Record the token as used (the gate was satisfied)
            # and audit the error so it is visible in the chain.
            record_use(conn, token.token_id, VerifyResult.success())
            log_id = append_log(
                conn,
                agent_id=calling_agent_id,
                action="tool_call_handler_error",
                target=f"tools/{tool_name}",
                data_label="CONFIDENTIAL",
                trace_id=trace_id,
                details={**base_details, "error": type(exc).__name__},
                security_event=False,
            )
            return InvokeResult.error(exc, log_id=log_id)

        # ── Step 5: record success ───────────────────────────────────────────
        # Use the handler's own IFC label when it returns a Labeled value so
        # the audit row correctly reflects SECRET-labelled tools (e.g. score_fraud).
        audit_label = value.label.level.value if isinstance(value, Labeled) else "CONFIDENTIAL"
        record_use(conn, token.token_id, VerifyResult.success())
        log_id = append_log(
            conn,
            agent_id=calling_agent_id,
            action="tool_call_ok",
            target=f"tools/{tool_name}",
            data_label=audit_label,
            trace_id=trace_id,
            details=base_details,
            security_event=False,
        )
        return InvokeResult.success(value, log_id=log_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _try_record_use(
    conn: psycopg.Connection,
    token_id: uuid.UUID,
    result: VerifyResult,
) -> None:
    """Record a failed verification in capability_token_log if the row exists.

    Silently swallows ValueError — a missing row means the token was never
    issued by the orchestrator (forged), and we should not manufacture a row.
    """
    try:
        record_use(conn, token_id, result)
    except ValueError:
        pass
