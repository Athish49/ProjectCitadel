"""Stub claims processor (task 2.1.5).

Public API:
  run_claims_processor_stub(*, claim_id, session_id, audit_fn) -> ProcessorEnvelope

Design:
  - Stub implementation for the vertical slice (Sprint 2.1).  No LLM call; returns
    deterministic hardcoded assessment values so the pipeline can advance through
    PROCESSING → DECIDED → SETTLED without a real tool suite.
  - The real actor (Sprint 4.1, task 4.1.6) will replace the stub body with
    Claude Sonnet 4.6 + capability-token-gated tools (classify_damage,
    lookup_coverage, score_fraud, search_policy_docs).
  - Hardcoded values are chosen to satisfy every orchestrator transition guard
    on the happy path:
      damage_assessment    — non-None  (PROCESSING → DECIDED guard)
      coverage_calculation — non-None  (PROCESSING → DECIDED guard)
      fraud_signal         — "CLEAR"   (DECIDED → SETTLED guard + SETTLED invariant)
  - data_label="CONFIDENTIAL" per TAD §2.3.3.

ProcessorEnvelope fields map to TransitionGuardContext as follows:
  envelope.damage_assessment    → ctx.damage_assessment
  envelope.coverage_calculation → ctx.coverage_calculation
  envelope.fraud_signal         → ctx.fraud_decision
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

ACTOR_AGENT_ID = "claims_processor"

# Hardcoded assessment values for the stub.
_STUB_DAMAGE_ASSESSMENT = "collision_minor"
_STUB_COVERAGE_CALCULATION = "full_coverage_applicable"
_STUB_FRAUD_SIGNAL = "CLEAR"


# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessorEnvelope:
    """Structured assessment output from the claims processor.

    damage_assessment    : damage classification label (maps to ctx.damage_assessment)
    coverage_calculation : coverage determination string (maps to ctx.coverage_calculation)
    fraud_signal         : "CLEAR" | "FLAG" | "DENY" (maps to ctx.fraud_decision)
    claim_id             : claim identifier scoped to this session
    session_id           : session identifier for audit correlation
    """

    damage_assessment: str
    coverage_calculation: str
    fraud_signal: str
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


def run_claims_processor_stub(
    *,
    claim_id: str,
    session_id: str = "unknown",
    audit_fn: AuditFn | None = None,
) -> ProcessorEnvelope:
    """Return a hardcoded ProcessorEnvelope and emit a processor_assessment audit event.

    Stub placeholder for Sprint 2.1 vertical slice.  Replace with the real
    LLM-backed actor in Sprint 4.1 (task 4.1.6).
    """
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    envelope = ProcessorEnvelope(
        damage_assessment=_STUB_DAMAGE_ASSESSMENT,
        coverage_calculation=_STUB_COVERAGE_CALCULATION,
        fraud_signal=_STUB_FRAUD_SIGNAL,
        claim_id=claim_id,
        session_id=session_id,
    )

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="processor_assessment",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "damage_assessment": envelope.damage_assessment,
            "fraud_signal": envelope.fraud_signal,
            "stub": True,
        },
        security_event=False,
    )

    return envelope
