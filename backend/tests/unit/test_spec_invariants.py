"""TLA+ spec invariant tests — Sprint 5.2.2.

Runs formal/check_spec.py's BFS exhaustively and asserts:
  TypeOK           — all vars stay in declared domains across all reachable states
  ClosedIsAbsorbing — CLOSED stage never transitions to a different stage
  ForwardProgress  — every stage change increases topological rank
  EventualClosure  — every reachable state can reach CLOSED
  Coverage         — all 9 stages appear in the reachable state space
"""
from __future__ import annotations

import pytest

from formal.check_spec import (
    AMOUNT_DOMAIN,
    FRAUD_DECISIONS,
    INIT,
    RANK,
    STAGES,
    WorkflowState,
    check_spec,
    check_closed_is_absorbing,
    check_forward_progress,
    check_type_ok,
    successors,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def spec_result() -> dict:
    """Run BFS once per test session; all tests share the cached result."""
    return check_spec()


class TestTypeOK:
    def test_init_state_is_type_ok(self) -> None:
        assert check_type_ok(INIT) is None

    def test_no_typeok_violations(self, spec_result: dict) -> None:
        violations = [v for v in spec_result["violations"] if "∉" in v]
        assert not violations, violations

    def test_stages_seen_subset_of_domain(self, spec_result: dict) -> None:
        assert spec_result["stages_seen"] <= STAGES


class TestClosedIsAbsorbing:
    def test_no_absorbing_violations(self, spec_result: dict) -> None:
        violations = [v for v in spec_result["violations"] if "ClosedIsAbsorbing" in v]
        assert not violations, violations

    def test_closed_with_all_guards_set_has_no_stage_change(self) -> None:
        """Even when every env flag is True, CLOSED produces no stage transition."""
        closed = WorkflowState(
            stage="CLOSED",
            intake_complete=True,
            identity_verified=True,
            damage_assessed=True,
            coverage_calculated=True,
            complaint_captured=True,
            fraud_decision="CLEAR",
            settlement_amount=10_000,
        )
        stage_changes = [s2 for s2 in successors(closed) if s2.stage != "CLOSED"]
        assert stage_changes == []

    def test_absorbing_check_helper_catches_violation(self) -> None:
        """Sanity-check the helper itself flags a stage change from CLOSED."""
        s = WorkflowState(
            stage="CLOSED",
            intake_complete=True, identity_verified=True, damage_assessed=True,
            coverage_calculated=True, complaint_captured=True,
            fraud_decision="CLEAR", settlement_amount=10_000,
        )
        s2 = WorkflowState(
            stage="INTAKE",
            intake_complete=False, identity_verified=False, damage_assessed=False,
            coverage_calculated=False, complaint_captured=False,
            fraud_decision="NONE", settlement_amount=0,
        )
        assert check_closed_is_absorbing(s, s2) is not None


class TestForwardProgress:
    def test_no_forward_progress_violations(self, spec_result: dict) -> None:
        violations = [v for v in spec_result["violations"] if "ForwardProgress" in v]
        assert not violations, violations

    @pytest.mark.parametrize("stage", sorted(STAGES))
    def test_rank_defined_for_every_stage(self, stage: str) -> None:
        assert stage in RANK

    def test_forward_progress_helper_catches_backward(self) -> None:
        """Helper must flag a lateral same-stage non-transition."""
        base = WorkflowState(
            stage="DECIDED",
            intake_complete=True, identity_verified=True, damage_assessed=True,
            coverage_calculated=True, complaint_captured=False,
            fraud_decision="CLEAR", settlement_amount=10_000,
        )
        # Fabricate an illegal backward stage change for the helper test
        earlier = WorkflowState(
            stage="INTAKE",
            intake_complete=True, identity_verified=True, damage_assessed=True,
            coverage_calculated=True, complaint_captured=False,
            fraud_decision="CLEAR", settlement_amount=10_000,
        )
        assert check_forward_progress(base, earlier) is not None


class TestEventualClosure:
    def test_no_eventual_closure_violations(self, spec_result: dict) -> None:
        violations = [v for v in spec_result["violations"] if "EventualClosure" in v]
        assert not violations, violations

    def test_closed_state_itself_can_reach_closed(self) -> None:
        """Trivial liveness: CLOSED trivially satisfies <>(stage = CLOSED)."""
        closed = WorkflowState(
            stage="CLOSED",
            intake_complete=True, identity_verified=True, damage_assessed=True,
            coverage_calculated=True, complaint_captured=True,
            fraud_decision="CLEAR", settlement_amount=10_000,
        )
        assert closed.stage == "CLOSED"


class TestStateSpaceCoverage:
    """Every stage must appear in the reachable state space."""

    @pytest.mark.parametrize("stage", sorted(STAGES))
    def test_stage_is_reachable(self, stage: str, spec_result: dict) -> None:
        assert stage in spec_result["stages_seen"], (
            f"Stage {stage!r} never reached — dead code in spec or missed transition."
        )

    def test_state_count_bounded(self, spec_result: dict) -> None:
        """Upper bound: 9 stages × 4 fraud decisions × 3 amounts × 2^5 booleans = 3456."""
        assert 1 <= spec_result["visited"] <= 3456

    def test_no_violations(self, spec_result: dict) -> None:
        assert spec_result["violations"] == [], (
            "Spec invariant violations:\n"
            + "\n".join(f"  {v}" for v in spec_result["violations"])
        )
