"""Conformance tests: implementation vs. formal spec — Sprint 5.2.3.

Drives the real advance_stage() / _check_guard() code from transitions.py and
asserts the implementation's reachable-edge set exactly matches the spec.

Three-part structure:
  1. TestEdgeSetConformance  — _VALID_EDGES count and exact set vs. spec's 11 edges
  2. TestValidEdgesAccepted  — every valid edge accepted with a satisfying context
  3. TestInvalidEdgesRejected — every invalid edge rejected regardless of context
  4. TestGuardBoundaries     — guard boundary conditions mirror spec predicates exactly
  5. TestTerminalStageConformance — CLOSED is terminal with no outbound edges
"""
from __future__ import annotations

import pytest

from agent_system.orchestrator.transitions import (
    ClaimStage,
    TERMINAL_STAGE,
    TransitionGuardContext,
    TransitionViolationError,
    _VALID_EDGES,
    advance_stage,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(**kwargs) -> TransitionGuardContext:
    return TransitionGuardContext(**kwargs)


# Full-pass context: satisfies every guard.  Used to ensure invalid-edge
# failures come from the edge check, not a guard check.
_FULL_CTX = TransitionGuardContext(
    intake_complete=True,
    identity_verified=True,
    damage_assessment="assessed",
    coverage_calculation="calculated",
    fraud_decision="CLEAR",
    settlement_amount=5_000.0,
    complaint_captured=True,
)

# ---------------------------------------------------------------------------
# Constants derived from the spec (workflow.tla)
# ---------------------------------------------------------------------------

_SPEC_EDGES: frozenset[tuple[str, str]] = frozenset({
    ("INTAKE",            "IDENTITY_PENDING"),
    ("IDENTITY_PENDING",  "IDENTITY_VERIFIED"),
    ("IDENTITY_VERIFIED", "PROCESSING"),
    ("IDENTITY_VERIFIED", "ESCALATED"),
    ("PROCESSING",        "DECIDED"),
    ("DECIDED",           "SETTLED"),
    ("DECIDED",           "ESCALATED"),
    ("DECIDED",           "DENIED"),
    ("SETTLED",           "CLOSED"),
    ("ESCALATED",         "CLOSED"),
    ("DENIED",            "CLOSED"),
})

_RANK: dict[str, int] = {
    "INTAKE": 0, "IDENTITY_PENDING": 1, "IDENTITY_VERIFIED": 2,
    "PROCESSING": 3, "DECIDED": 4, "SETTLED": 5,
    "ESCALATED": 5, "DENIED": 5, "CLOSED": 6,
}

# All (src, dst) pairs whose edge is not in _VALID_EDGES.
_ALL_INVALID_EDGES: list[tuple[ClaimStage, ClaimStage]] = [
    (s, d)
    for s in ClaimStage
    for d in ClaimStage
    if (s, d) not in _VALID_EDGES
]

# ---------------------------------------------------------------------------
# 1. Edge set conformance
# ---------------------------------------------------------------------------


class TestEdgeSetConformance:
    """The implementation's _VALID_EDGES must match the spec's 11 edges exactly."""

    def test_valid_edges_count(self) -> None:
        assert len(_VALID_EDGES) == 11

    def test_implementation_edges_match_spec(self) -> None:
        impl = frozenset((s.value, d.value) for s, d in _VALID_EDGES)
        extra = impl - _SPEC_EDGES
        missing = _SPEC_EDGES - impl
        assert not extra and not missing, (
            f"Edge mismatch — extra in impl: {extra}; missing from impl: {missing}"
        )


# ---------------------------------------------------------------------------
# 2. Valid edges accepted
# ---------------------------------------------------------------------------

# Minimal satisfying context for each of the 11 edges.
_SATISFYING: dict[tuple[ClaimStage, ClaimStage], TransitionGuardContext] = {
    (ClaimStage.INTAKE,            ClaimStage.IDENTITY_PENDING):  _ctx(intake_complete=True),
    (ClaimStage.IDENTITY_PENDING,  ClaimStage.IDENTITY_VERIFIED): _ctx(identity_verified=True),
    (ClaimStage.IDENTITY_VERIFIED, ClaimStage.PROCESSING):        _ctx(),
    (ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED):         _ctx(complaint_captured=True),
    (ClaimStage.PROCESSING,        ClaimStage.DECIDED):           _ctx(
        damage_assessment="ok",
        coverage_calculation="ok",
        fraud_decision="CLEAR",
    ),
    (ClaimStage.DECIDED, ClaimStage.SETTLED):   _ctx(fraud_decision="CLEAR",  settlement_amount=5_000.0),
    (ClaimStage.DECIDED, ClaimStage.ESCALATED): _ctx(fraud_decision="FLAG",   settlement_amount=5_000.0),
    (ClaimStage.DECIDED, ClaimStage.DENIED):    _ctx(),
    (ClaimStage.SETTLED,   ClaimStage.CLOSED):  _ctx(),
    (ClaimStage.ESCALATED, ClaimStage.CLOSED):  _ctx(),
    (ClaimStage.DENIED,    ClaimStage.CLOSED):  _ctx(),
}


class TestValidEdgesAccepted:
    @pytest.mark.parametrize(
        "edge",
        sorted(_SATISFYING.keys(), key=lambda e: (e[0].value, e[1].value)),
        ids=lambda e: f"{e[0].value}->{e[1].value}",
    )
    def test_advance_stage_accepts_valid_edge(
        self, edge: tuple[ClaimStage, ClaimStage]
    ) -> None:
        src, dst = edge
        assert advance_stage(src, dst, _SATISFYING[edge]) == dst


# ---------------------------------------------------------------------------
# 3. Invalid edges rejected
# ---------------------------------------------------------------------------


class TestInvalidEdgesRejected:
    """All 9×9 − 11 = 70 invalid pairs raise TransitionViolationError."""

    @pytest.mark.parametrize(
        "edge",
        _ALL_INVALID_EDGES,
        ids=lambda e: f"{e[0].value}->{e[1].value}",
    )
    def test_invalid_edge_raises(self, edge: tuple[ClaimStage, ClaimStage]) -> None:
        src, dst = edge
        with pytest.raises(TransitionViolationError):
            # _FULL_CTX satisfies every guard; only edge-graph check can fail here.
            advance_stage(src, dst, _FULL_CTX)


# ---------------------------------------------------------------------------
# 4. Guard boundary conditions
# ---------------------------------------------------------------------------


class TestGuardBoundaries:
    """Guard semantics match spec predicates at exact boundary values."""

    # DECIDED → SETTLED: settlement_amount ≤ AUTO_APPROVE_LIMIT
    def test_settled_at_limit_allowed(self) -> None:
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=10_000.0, auto_approve_limit=10_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx) == ClaimStage.SETTLED

    def test_settled_over_limit_rejected(self) -> None:
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=10_001.0, auto_approve_limit=10_000.0)
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx)

    # DECIDED → ESCALATED triggers
    def test_escalated_by_fraud_flag(self) -> None:
        ctx = _ctx(fraud_decision="FLAG", settlement_amount=1_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) == ClaimStage.ESCALATED

    def test_escalated_by_fraud_deny(self) -> None:
        ctx = _ctx(fraud_decision="DENY", settlement_amount=1_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) == ClaimStage.ESCALATED

    def test_escalated_by_high_amount(self) -> None:
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=15_000.0, auto_approve_limit=10_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) == ClaimStage.ESCALATED

    def test_escalated_requires_trigger(self) -> None:
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=5_000.0, auto_approve_limit=10_000.0)
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx)

    # IDENTITY_VERIFIED → ESCALATED (complaint path)
    def test_complaint_path_requires_complaint_captured(self) -> None:
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED, _ctx())

    def test_complaint_path_allowed_when_captured(self) -> None:
        ctx = _ctx(complaint_captured=True)
        assert (
            advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED, ctx)
            == ClaimStage.ESCALATED
        )

    # DECIDED → DENIED has no guard (admin override)
    def test_denied_requires_no_guard(self) -> None:
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.DENIED, _ctx()) == ClaimStage.DENIED


# ---------------------------------------------------------------------------
# 5. Terminal stage conformance
# ---------------------------------------------------------------------------


class TestTerminalStageConformance:
    def test_terminal_stage_is_closed(self) -> None:
        assert TERMINAL_STAGE == ClaimStage.CLOSED

    @pytest.mark.parametrize("dst", list(ClaimStage), ids=lambda d: d.value)
    def test_no_transition_from_closed(self, dst: ClaimStage) -> None:
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.CLOSED, dst, _FULL_CTX)
