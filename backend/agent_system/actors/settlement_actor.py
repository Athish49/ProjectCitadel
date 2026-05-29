"""Stub settlement actor (task 2.1.6).

Public API:
  run_settlement_actor_stub(*, claim_id, session_id, audit_fn) -> SettlementEnvelope

Design:
  - Stub implementation for the vertical slice (Sprint 2.1).  No LLM call; returns
    deterministic hardcoded settlement values so the pipeline can advance through
    DECIDED → SETTLED → CLOSED without a real tool suite.
  - The real actor (Sprint 4.1) will replace the stub body with Claude Sonnet 4.6 +
    capability-token-gated tools (calculate_settlement, request_payout, draft_summary).
  - Hardcoded values are chosen to satisfy the DECIDED → SETTLED transition guard:
      fraud_signal must be "CLEAR" (supplied by ProcessorEnvelope; not re-checked here)
      settlement_amount must be ≤ auto_approve_limit (10,000.0)  ← _STUB_SETTLEMENT_AMOUNT
  - Bank details are never present in the stub; session-bound payee resolution is
    the responsibility of the real request_payout tool.
  - data_label="CONFIDENTIAL" per TAD §2.3.4.

SettlementEnvelope.settlement_amount maps to TransitionGuardContext.settlement_amount.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

ACTOR_AGENT_ID = "settlement_actor"

# Hardcoded stub values.
_STUB_SETTLEMENT_AMOUNT: float = 4_500.0   # within the 10,000 auto_approve_limit
_STUB_PAYOUT_STATUS = "approved"
_STUB_SUMMARY = (
    "Stub settlement: collision claim approved for $4,500.00 under full coverage. "
    "Payment will be processed to the account on file within 5–7 business days."
)


# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettlementEnvelope:
    """Structured output from the settlement actor.

    settlement_amount : approved payout amount (maps to ctx.settlement_amount)
    payout_status     : "approved" | "pending_payout" | "escalated"
    summary           : customer-facing settlement summary (egress-filtered before display)
    claim_id          : claim identifier scoped to this session
    session_id        : session identifier for audit correlation
    """

    settlement_amount: float
    payout_status: str
    summary: str
    claim_id: str
    session_id: str


# ---------------------------------------------------------------------------
# AuditFn protocol
# ---------------------------------------------------------------------------


class AuditFn(Protocol):
    def __call__(
        self,
        *,
        agent_id: str,
        action: str,
        target: str,
        data_label: str,
        trace_id: str | None = None,
        details: dict | None = None,
        security_event: bool = False,
    ) -> None: ...


def _noop_audit(
    *,
    agent_id: str,
    action: str,
    target: str,
    data_label: str,
    trace_id: str | None = None,
    details: dict | None = None,
    security_event: bool = False,
) -> None:
    pass


# ---------------------------------------------------------------------------
# Stub actor
# ---------------------------------------------------------------------------


def run_settlement_actor_stub(
    *,
    claim_id: str,
    session_id: str = "unknown",
    audit_fn: AuditFn | None = None,
) -> SettlementEnvelope:
    """Return a hardcoded SettlementEnvelope and emit a settlement_issued audit event.

    Stub placeholder for Sprint 2.1 vertical slice.  Replace with the real
    LLM-backed actor in Sprint 4.1.
    """
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    envelope = SettlementEnvelope(
        settlement_amount=_STUB_SETTLEMENT_AMOUNT,
        payout_status=_STUB_PAYOUT_STATUS,
        summary=_STUB_SUMMARY,
        claim_id=claim_id,
        session_id=session_id,
    )

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="settlement_issued",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "settlement_amount": envelope.settlement_amount,
            "payout_status": envelope.payout_status,
            "stub": True,
        },
        security_event=False,
    )

    return envelope
