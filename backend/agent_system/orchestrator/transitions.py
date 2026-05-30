"""Deterministic claim-workflow state machine (P2 — task 1.3.5).

Public API:
  advance_stage(current, requested, ctx) -> ClaimStage   # raises TransitionViolationError

State graph (§3.2 of TAD — claim filing flow only):

    INTAKE → IDENTITY_PENDING → IDENTITY_VERIFIED → PROCESSING
          → DECIDED → SETTLED  ─┐
                    → ESCALATED─┤→ CLOSED
                    → DENIED   ─┘

No backward transitions.  No stage-skipping.  Attempted violation raises
TransitionViolationError which the Orchestrator converts to a security audit event.

This module is pure logic — no LLM calls, no DB I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClaimStage(str, Enum):
    """Ordered workflow stages for a claim filing session.

    String values are stored in the DB; do not rename without a migration.
    """

    INTAKE = "INTAKE"
    IDENTITY_PENDING = "IDENTITY_PENDING"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    PROCESSING = "PROCESSING"
    DECIDED = "DECIDED"
    SETTLED = "SETTLED"
    ESCALATED = "ESCALATED"
    DENIED = "DENIED"    # Orchestrator-initiated administrative denial
    CLOSED = "CLOSED"


# Terminal stage — no outbound edges.
TERMINAL_STAGE = ClaimStage.CLOSED

# All valid directed edges in the state graph.  No edge not listed here
# is ever permitted, regardless of guard context.
_VALID_EDGES: frozenset[tuple[ClaimStage, ClaimStage]] = frozenset({
    (ClaimStage.INTAKE,              ClaimStage.IDENTITY_PENDING),
    (ClaimStage.IDENTITY_PENDING,    ClaimStage.IDENTITY_VERIFIED),
    (ClaimStage.IDENTITY_VERIFIED,   ClaimStage.PROCESSING),
    (ClaimStage.IDENTITY_VERIFIED,   ClaimStage.ESCALATED),   # complaint capture (task 4.1.9)
    (ClaimStage.PROCESSING,          ClaimStage.DECIDED),
    (ClaimStage.DECIDED,             ClaimStage.SETTLED),
    (ClaimStage.DECIDED,             ClaimStage.ESCALATED),
    (ClaimStage.DECIDED,             ClaimStage.DENIED),
    (ClaimStage.SETTLED,             ClaimStage.CLOSED),
    (ClaimStage.ESCALATED,           ClaimStage.CLOSED),
    (ClaimStage.DENIED,              ClaimStage.CLOSED),
})


@dataclass(frozen=True)
class TransitionGuardContext:
    """Pre-condition data evaluated by each transition guard.

    Callers supply only the fields relevant to the requested transition;
    all others default to their "not satisfied" value so missing data
    cannot accidentally pass a guard.
    """

    # INTAKE → IDENTITY_PENDING
    intake_complete: bool = False

    # IDENTITY_PENDING → IDENTITY_VERIFIED
    identity_verified: bool = False

    # PROCESSING → DECIDED
    damage_assessment: str | None = None
    coverage_calculation: str | None = None
    fraud_decision: str | None = None  # "CLEAR" | "FLAG" | "DENY"

    # DECIDED → SETTLED / ESCALATED
    settlement_amount: float | None = None
    auto_approve_limit: float = 10_000.0

    # IDENTITY_VERIFIED → ESCALATED (complaint path — task 4.1.9)
    complaint_captured: bool = False


class TransitionViolationError(ValueError):
    """Raised when a requested transition violates the state machine.

    Carries from_stage and to_stage for structured audit logging.
    """

    def __init__(
        self,
        message: str,
        from_stage: ClaimStage,
        to_stage: ClaimStage,
    ) -> None:
        super().__init__(message)
        self.from_stage = from_stage
        self.to_stage = to_stage


def _check_guard(
    from_stage: ClaimStage,
    to_stage: ClaimStage,
    ctx: TransitionGuardContext,
) -> str | None:
    """Return a violation reason string if the guard fails, else None.

    Guards implement §3.2 pre-conditions from TAD.
    """
    match (from_stage, to_stage):
        case (ClaimStage.INTAKE, ClaimStage.IDENTITY_PENDING):
            if not ctx.intake_complete:
                return "intake_complete is False"

        case (ClaimStage.IDENTITY_PENDING, ClaimStage.IDENTITY_VERIFIED):
            if not ctx.identity_verified:
                return "identity_verified is False"

        case (ClaimStage.PROCESSING, ClaimStage.DECIDED):
            missing = [
                f for f, v in [
                    ("damage_assessment",   ctx.damage_assessment),
                    ("coverage_calculation", ctx.coverage_calculation),
                    ("fraud_decision",       ctx.fraud_decision),
                ]
                if v is None
            ]
            if missing:
                return f"missing required fields: {', '.join(missing)}"

        case (ClaimStage.DECIDED, ClaimStage.SETTLED):
            if ctx.fraud_decision != "CLEAR":
                return f"fraud_decision={ctx.fraud_decision!r}, expected 'CLEAR'"
            if ctx.settlement_amount is None:
                return "settlement_amount is None"
            if ctx.settlement_amount > ctx.auto_approve_limit:
                return (
                    f"settlement_amount {ctx.settlement_amount} "
                    f"> auto_approve_limit {ctx.auto_approve_limit}"
                )

        case (ClaimStage.DECIDED, ClaimStage.ESCALATED):
            fraud_triggers = ctx.fraud_decision in ("FLAG", "DENY")
            amount_triggers = (
                ctx.settlement_amount is not None
                and ctx.settlement_amount > ctx.auto_approve_limit
            )
            if not (fraud_triggers or amount_triggers):
                return (
                    f"no escalation trigger: fraud_decision={ctx.fraud_decision!r}, "
                    f"settlement_amount={ctx.settlement_amount}, "
                    f"auto_approve_limit={ctx.auto_approve_limit}"
                )

        case (ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED):
            if not ctx.complaint_captured:
                return "complaint_captured is False"

        # DECIDED → DENIED: orchestrator administrative override — no data guard.
        # IDENTITY_VERIFIED → PROCESSING: orchestrator-initiated — no data guard.
        # {SETTLED,ESCALATED,DENIED} → CLOSED: terminal collection — no data guard.

    return None


def allowed_next_stages(stage: ClaimStage) -> frozenset[ClaimStage]:
    """Return the set of stages directly reachable from *stage*."""
    return frozenset(dst for (src, dst) in _VALID_EDGES if src == stage)


def advance_stage(
    current: ClaimStage,
    requested: ClaimStage,
    ctx: TransitionGuardContext,
) -> ClaimStage:
    """Attempt a transition from *current* to *requested*.

    Returns *requested* on success.
    Raises TransitionViolationError if the edge is not in the graph or a
    pre-condition guard fails.
    """
    if (current, requested) not in _VALID_EDGES:
        raise TransitionViolationError(
            f"Invalid transition {current.value} → {requested.value}: "
            "edge not in state graph",
            current,
            requested,
        )

    violation = _check_guard(current, requested, ctx)
    if violation:
        raise TransitionViolationError(
            f"Guard failed {current.value} → {requested.value}: {violation}",
            current,
            requested,
        )

    return requested
