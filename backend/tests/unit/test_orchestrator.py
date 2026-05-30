"""Unit tests for Sprint 1.3.5 — deterministic orchestrator skeleton.

Covers:
  transitions.py  — ClaimStage, _VALID_EDGES, _check_guard, advance_stage,
                    allowed_next_stages, TransitionViolationError
  budgets.py      — SessionBudget, BudgetConfig, consume_tokens,
                    consume_tool_call, BudgetExceededError
  state.py        — Orchestrator.request_transition, .record_token_use,
                    .record_tool_call, audit event shapes

Run via:
  make test-orchestrator
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from agent_system.parser.schemas.intake import ClaimIntent
from agent_system.orchestrator.budgets import (
    BudgetConfig,
    BudgetExceededError,
    SessionBudget,
    consume_tokens,
    consume_tool_call,
)
from agent_system.orchestrator.intent_routing import IntentRoute, dispatch_intent
from agent_system.orchestrator.state import Orchestrator
from agent_system.orchestrator.transitions import (
    ClaimStage,
    TransitionGuardContext,
    TransitionViolationError,
    advance_stage,
    allowed_next_stages,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ctx(**kwargs: Any) -> TransitionGuardContext:
    return TransitionGuardContext(**kwargs)


def _full_processing_ctx() -> TransitionGuardContext:
    return TransitionGuardContext(
        damage_assessment="moderate",
        coverage_calculation="full",
        fraud_decision="CLEAR",
        settlement_amount=5_000.0,
    )


def _new_budget(session_id: str = "sess-1") -> SessionBudget:
    return SessionBudget(session_id=session_id)


def _new_config(**kwargs: Any) -> BudgetConfig:
    return BudgetConfig(**kwargs)


# ---------------------------------------------------------------------------
# ClaimStage enum
# ---------------------------------------------------------------------------


class TestClaimStage:
    def test_all_stages_are_strings(self):
        for stage in ClaimStage:
            assert isinstance(stage.value, str)

    def test_closed_is_terminal(self):
        from agent_system.orchestrator.transitions import TERMINAL_STAGE
        assert TERMINAL_STAGE is ClaimStage.CLOSED

    def test_closed_has_no_outbound_edges(self):
        assert allowed_next_stages(ClaimStage.CLOSED) == frozenset()

    def test_stage_count(self):
        assert len(ClaimStage) == 9


# ---------------------------------------------------------------------------
# allowed_next_stages
# ---------------------------------------------------------------------------


class TestAllowedNextStages:
    def test_intake_next(self):
        assert allowed_next_stages(ClaimStage.INTAKE) == frozenset({ClaimStage.IDENTITY_PENDING})

    def test_decided_has_three_successors(self):
        nxt = allowed_next_stages(ClaimStage.DECIDED)
        assert nxt == frozenset({ClaimStage.SETTLED, ClaimStage.ESCALATED, ClaimStage.DENIED})

    def test_processing_next(self):
        assert allowed_next_stages(ClaimStage.PROCESSING) == frozenset({ClaimStage.DECIDED})

    def test_settled_next(self):
        assert allowed_next_stages(ClaimStage.SETTLED) == frozenset({ClaimStage.CLOSED})

    def test_escalated_next(self):
        assert allowed_next_stages(ClaimStage.ESCALATED) == frozenset({ClaimStage.CLOSED})

    def test_denied_next(self):
        assert allowed_next_stages(ClaimStage.DENIED) == frozenset({ClaimStage.CLOSED})


# ---------------------------------------------------------------------------
# Valid edges — advance_stage happy paths
# ---------------------------------------------------------------------------


class TestAdvanceStageValidEdges:
    def test_intake_to_identity_pending(self):
        ctx = _ctx(intake_complete=True)
        assert advance_stage(ClaimStage.INTAKE, ClaimStage.IDENTITY_PENDING, ctx) is ClaimStage.IDENTITY_PENDING

    def test_identity_pending_to_verified(self):
        ctx = _ctx(identity_verified=True)
        assert advance_stage(ClaimStage.IDENTITY_PENDING, ClaimStage.IDENTITY_VERIFIED, ctx) is ClaimStage.IDENTITY_VERIFIED

    def test_identity_verified_to_processing(self):
        ctx = _ctx()
        assert advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.PROCESSING, ctx) is ClaimStage.PROCESSING

    def test_processing_to_decided(self):
        ctx = _full_processing_ctx()
        assert advance_stage(ClaimStage.PROCESSING, ClaimStage.DECIDED, ctx) is ClaimStage.DECIDED

    def test_decided_to_settled(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=1_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx) is ClaimStage.SETTLED

    def test_decided_to_escalated_fraud_flag(self):
        ctx = _ctx(fraud_decision="FLAG", settlement_amount=500.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) is ClaimStage.ESCALATED

    def test_decided_to_escalated_amount_over_limit(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=20_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) is ClaimStage.ESCALATED

    def test_decided_to_denied_no_guard(self):
        ctx = _ctx()
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.DENIED, ctx) is ClaimStage.DENIED

    def test_settled_to_closed(self):
        assert advance_stage(ClaimStage.SETTLED, ClaimStage.CLOSED, _ctx()) is ClaimStage.CLOSED

    def test_escalated_to_closed(self):
        assert advance_stage(ClaimStage.ESCALATED, ClaimStage.CLOSED, _ctx()) is ClaimStage.CLOSED

    def test_denied_to_closed(self):
        assert advance_stage(ClaimStage.DENIED, ClaimStage.CLOSED, _ctx()) is ClaimStage.CLOSED


# ---------------------------------------------------------------------------
# Invalid edges — edge not in graph
# ---------------------------------------------------------------------------


class TestAdvanceStageInvalidEdge:
    def _assert_violation(self, frm: ClaimStage, to: ClaimStage) -> TransitionViolationError:
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(frm, to, _ctx())
        err = exc_info.value
        assert err.from_stage is frm
        assert err.to_stage is to
        return err

    def test_backward_intake_impossible(self):
        # IDENTITY_PENDING → INTAKE is not a valid edge
        self._assert_violation(ClaimStage.IDENTITY_PENDING, ClaimStage.INTAKE)

    def test_skip_intake_to_processing(self):
        self._assert_violation(ClaimStage.INTAKE, ClaimStage.PROCESSING)

    def test_skip_to_decided(self):
        self._assert_violation(ClaimStage.INTAKE, ClaimStage.DECIDED)

    def test_closed_no_outbound(self):
        self._assert_violation(ClaimStage.CLOSED, ClaimStage.INTAKE)

    def test_settled_to_escalated_not_valid(self):
        self._assert_violation(ClaimStage.SETTLED, ClaimStage.ESCALATED)

    def test_decided_to_identity_pending_invalid(self):
        self._assert_violation(ClaimStage.DECIDED, ClaimStage.INTAKE)

    def test_error_message_contains_stages(self):
        err = self._assert_violation(ClaimStage.INTAKE, ClaimStage.DECIDED)
        assert "INTAKE" in str(err)
        assert "DECIDED" in str(err)


# ---------------------------------------------------------------------------
# Guard failures on valid edges
# ---------------------------------------------------------------------------


class TestGuardFailures:
    def test_intake_guard_fails_when_not_complete(self):
        ctx = _ctx(intake_complete=False)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.INTAKE, ClaimStage.IDENTITY_PENDING, ctx)
        assert "intake_complete" in str(exc_info.value)

    def test_identity_guard_fails_when_not_verified(self):
        ctx = _ctx(identity_verified=False)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.IDENTITY_PENDING, ClaimStage.IDENTITY_VERIFIED, ctx)
        assert "identity_verified" in str(exc_info.value)

    def test_processing_guard_missing_all_fields(self):
        ctx = _ctx()  # damage_assessment, coverage_calculation, fraud_decision all None
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.PROCESSING, ClaimStage.DECIDED, ctx)
        msg = str(exc_info.value)
        assert "damage_assessment" in msg
        assert "coverage_calculation" in msg
        assert "fraud_decision" in msg

    def test_processing_guard_missing_partial(self):
        ctx = _ctx(damage_assessment="minor", coverage_calculation="partial")
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.PROCESSING, ClaimStage.DECIDED, ctx)
        assert "fraud_decision" in str(exc_info.value)

    def test_settled_guard_fails_non_clear_fraud(self):
        ctx = _ctx(fraud_decision="FLAG", settlement_amount=500.0)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx)
        assert "fraud_decision" in str(exc_info.value)

    def test_settled_guard_fails_no_amount(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=None)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx)
        assert "settlement_amount" in str(exc_info.value)

    def test_settled_guard_fails_over_limit(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=15_000.0, auto_approve_limit=10_000.0)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx)
        assert "15000" in str(exc_info.value)

    def test_escalated_guard_fails_no_trigger(self):
        # CLEAR fraud, amount under limit — neither trigger fires
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=500.0)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx)
        assert "no escalation trigger" in str(exc_info.value)

    def test_escalated_guard_fails_no_trigger_no_amount(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=None)
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx)

    def test_violation_error_carries_stages(self):
        ctx = _ctx(intake_complete=False)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.INTAKE, ClaimStage.IDENTITY_PENDING, ctx)
        err = exc_info.value
        assert err.from_stage is ClaimStage.INTAKE
        assert err.to_stage is ClaimStage.IDENTITY_PENDING

    def test_violation_is_value_error_subclass(self):
        with pytest.raises(ValueError):
            advance_stage(ClaimStage.INTAKE, ClaimStage.DECIDED, _ctx())


# ---------------------------------------------------------------------------
# Guard edge cases — escalation triggers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# IDENTITY_VERIFIED → ESCALATED — complaint path (task 4.1.9)
# ---------------------------------------------------------------------------


class TestComplaintEscalationPath:
    def test_identity_verified_to_escalated_happy_path(self):
        ctx = _ctx(complaint_captured=True)
        result = advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED, ctx)
        assert result is ClaimStage.ESCALATED

    def test_identity_verified_to_escalated_guard_fails_without_complaint(self):
        ctx = _ctx(complaint_captured=False)
        with pytest.raises(TransitionViolationError) as exc_info:
            advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED, ctx)
        assert "complaint_captured" in str(exc_info.value)

    def test_identity_verified_to_escalated_guard_default_false(self):
        """Default TransitionGuardContext must block IDENTITY_VERIFIED→ESCALATED."""
        ctx = _ctx()  # complaint_captured defaults to False
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.ESCALATED, ctx)

    def test_identity_verified_to_processing_unaffected(self):
        """Adding the complaint edge must not break the existing processing path."""
        ctx = _ctx()
        assert advance_stage(ClaimStage.IDENTITY_VERIFIED, ClaimStage.PROCESSING, ctx) is ClaimStage.PROCESSING

    def test_identity_verified_allowed_next_includes_escalated(self):
        nxt = allowed_next_stages(ClaimStage.IDENTITY_VERIFIED)
        assert ClaimStage.ESCALATED in nxt
        assert ClaimStage.PROCESSING in nxt

    def test_decided_escalated_guard_still_requires_trigger(self):
        """DECIDED→ESCALATED guard should be unaffected by complaint_captured field."""
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=500.0, complaint_captured=True)
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx)


class TestEscalationGuardEdgeCases:
    def test_deny_fraud_triggers_escalation(self):
        ctx = _ctx(fraud_decision="DENY", settlement_amount=500.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) is ClaimStage.ESCALATED

    def test_amount_exactly_at_limit_does_not_trigger_escalation(self):
        # settlement_amount == auto_approve_limit: NOT > limit, so NOT escalation trigger
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=10_000.0, auto_approve_limit=10_000.0)
        with pytest.raises(TransitionViolationError):
            advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx)

    def test_amount_exactly_at_limit_allows_settled(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=10_000.0, auto_approve_limit=10_000.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx) is ClaimStage.SETTLED

    def test_custom_approve_limit(self):
        ctx = _ctx(fraud_decision="CLEAR", settlement_amount=500.0, auto_approve_limit=100.0)
        assert advance_stage(ClaimStage.DECIDED, ClaimStage.ESCALATED, ctx) is ClaimStage.ESCALATED


# ---------------------------------------------------------------------------
# SessionBudget / consume_tokens
# ---------------------------------------------------------------------------


class TestConsumeTokens:
    def test_normal_consumption(self):
        b = _new_budget()
        cfg = _new_config(max_session_tokens=100)
        consume_tokens(b, 40, cfg)
        assert b.tokens_used == 40
        assert b.halted is False

    def test_multiple_consumptions_accumulate(self):
        b = _new_budget()
        cfg = _new_config(max_session_tokens=100)
        consume_tokens(b, 30, cfg)
        consume_tokens(b, 30, cfg)
        assert b.tokens_used == 60

    def test_exactly_at_limit_does_not_raise(self):
        b = _new_budget()
        cfg = _new_config(max_session_tokens=50)
        consume_tokens(b, 50, cfg)
        assert b.tokens_used == 50
        assert b.halted is False

    def test_exceeds_limit_raises(self):
        b = _new_budget()
        cfg = _new_config(max_session_tokens=50)
        with pytest.raises(BudgetExceededError) as exc_info:
            consume_tokens(b, 51, cfg)
        assert exc_info.value.kind == "tokens"

    def test_exceeds_limit_halts_session(self):
        b = _new_budget()
        cfg = _new_config(max_session_tokens=50)
        with pytest.raises(BudgetExceededError):
            consume_tokens(b, 51, cfg)
        assert b.halted is True

    def test_halted_session_rejects_further_tokens(self):
        b = _new_budget()
        cfg = _new_config(max_session_tokens=50)
        with pytest.raises(BudgetExceededError):
            consume_tokens(b, 51, cfg)
        with pytest.raises(BudgetExceededError) as exc_info:
            consume_tokens(b, 1, cfg)
        assert exc_info.value.kind == "tokens"

    def test_error_message_contains_session_id(self):
        b = _new_budget("my-session")
        cfg = _new_config(max_session_tokens=10)
        with pytest.raises(BudgetExceededError) as exc_info:
            consume_tokens(b, 11, cfg)
        assert "my-session" in str(exc_info.value)


# ---------------------------------------------------------------------------
# consume_tool_call
# ---------------------------------------------------------------------------


class TestConsumeToolCall:
    def test_normal_tool_call(self):
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=5)
        consume_tool_call(b, "agent-a", cfg)
        assert b.tool_calls["agent-a"] == 1

    def test_multiple_agents_tracked_independently(self):
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=5)
        consume_tool_call(b, "agent-a", cfg)
        consume_tool_call(b, "agent-a", cfg)
        consume_tool_call(b, "agent-b", cfg)
        assert b.tool_calls["agent-a"] == 2
        assert b.tool_calls["agent-b"] == 1

    def test_exactly_at_limit_does_not_raise(self):
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=3)
        for _ in range(3):
            consume_tool_call(b, "agent-a", cfg)
        assert b.tool_calls["agent-a"] == 3
        assert b.halted is False

    def test_exceeds_limit_raises(self):
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=3)
        for _ in range(3):
            consume_tool_call(b, "agent-a", cfg)
        with pytest.raises(BudgetExceededError) as exc_info:
            consume_tool_call(b, "agent-a", cfg)
        assert exc_info.value.kind == "tool_calls"
        assert exc_info.value.agent_id == "agent-a"

    def test_exceeds_limit_halts_session(self):
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=1)
        consume_tool_call(b, "agent-a", cfg)
        with pytest.raises(BudgetExceededError):
            consume_tool_call(b, "agent-a", cfg)
        assert b.halted is True

    def test_halted_session_rejects_other_agent(self):
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=1)
        consume_tool_call(b, "agent-a", cfg)
        with pytest.raises(BudgetExceededError):
            consume_tool_call(b, "agent-a", cfg)
        with pytest.raises(BudgetExceededError):
            consume_tool_call(b, "agent-b", cfg)

    def test_per_agent_isolation_at_limit(self):
        # agent-a exhausted but agent-b is still under limit
        b = _new_budget()
        cfg = _new_config(max_tool_calls_per_agent=2)
        consume_tool_call(b, "agent-a", cfg)
        consume_tool_call(b, "agent-a", cfg)
        # agent-a at limit — next call exceeds
        with pytest.raises(BudgetExceededError):
            consume_tool_call(b, "agent-a", cfg)
        # session is now halted, agent-b also blocked
        assert b.halted is True


# ---------------------------------------------------------------------------
# BudgetExceededError structure
# ---------------------------------------------------------------------------


class TestBudgetExceededError:
    def test_is_exception_subclass(self):
        err = BudgetExceededError("msg", "tokens")
        assert isinstance(err, Exception)

    def test_kind_tokens(self):
        err = BudgetExceededError("msg", "tokens")
        assert err.kind == "tokens"

    def test_kind_tool_calls(self):
        err = BudgetExceededError("msg", "tool_calls", agent_id="a")
        assert err.kind == "tool_calls"
        assert err.agent_id == "a"

    def test_agent_id_defaults_none(self):
        err = BudgetExceededError("msg", "tokens")
        assert err.agent_id is None


# ---------------------------------------------------------------------------
# Orchestrator — construction
# ---------------------------------------------------------------------------


class TestOrchestratorConstruction:
    def test_default_stage_is_intake(self):
        orch = Orchestrator("s1")
        assert orch.stage is ClaimStage.INTAKE

    def test_custom_initial_stage(self):
        orch = Orchestrator("s1", initial_stage=ClaimStage.PROCESSING)
        assert orch.stage is ClaimStage.PROCESSING

    def test_session_id_stored(self):
        orch = Orchestrator("abc-123")
        assert orch.session_id == "abc-123"

    def test_budget_initialised(self):
        orch = Orchestrator("s1")
        assert orch.budget.tokens_used == 0
        assert orch.budget.halted is False


# ---------------------------------------------------------------------------
# Orchestrator.request_transition — success path
# ---------------------------------------------------------------------------


class TestOrchestratorRequestTransition:
    def test_happy_path_advances_stage(self):
        orch = Orchestrator("s1")
        ctx = _ctx(intake_complete=True)
        result = orch.request_transition(ClaimStage.IDENTITY_PENDING, ctx)
        assert result is ClaimStage.IDENTITY_PENDING
        assert orch.stage is ClaimStage.IDENTITY_PENDING

    def test_multiple_transitions(self):
        orch = Orchestrator("s1")
        orch.request_transition(ClaimStage.IDENTITY_PENDING, _ctx(intake_complete=True))
        orch.request_transition(ClaimStage.IDENTITY_VERIFIED, _ctx(identity_verified=True))
        assert orch.stage is ClaimStage.IDENTITY_VERIFIED

    def test_audit_called_on_success(self):
        audit = MagicMock()
        orch = Orchestrator("s1", audit_fn=audit)
        orch.request_transition(ClaimStage.IDENTITY_PENDING, _ctx(intake_complete=True))
        audit.assert_called_once()
        call_kwargs = audit.call_args.kwargs
        assert call_kwargs["action"] == "stage_transition"
        assert call_kwargs["security_event"] is False
        assert call_kwargs["details"]["to_stage"] == "IDENTITY_PENDING"

    def test_audit_target_is_session_id(self):
        audit = MagicMock()
        orch = Orchestrator("sess-xyz", audit_fn=audit)
        orch.request_transition(ClaimStage.IDENTITY_PENDING, _ctx(intake_complete=True))
        assert audit.call_args.kwargs["target"] == "sess-xyz"


# ---------------------------------------------------------------------------
# Orchestrator.request_transition — violation path
# ---------------------------------------------------------------------------


class TestOrchestratorTransitionViolation:
    def test_raises_on_invalid_edge(self):
        orch = Orchestrator("s1")
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.DECIDED, _ctx())

    def test_raises_on_guard_failure(self):
        orch = Orchestrator("s1")
        ctx = _ctx(intake_complete=False)
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.IDENTITY_PENDING, ctx)

    def test_audit_called_as_security_event_on_violation(self):
        audit = MagicMock()
        orch = Orchestrator("s1", audit_fn=audit)
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.DECIDED, _ctx())
        audit.assert_called_once()
        call_kwargs = audit.call_args.kwargs
        assert call_kwargs["action"] == "transition_violation"
        assert call_kwargs["security_event"] is True

    def test_stage_unchanged_after_violation(self):
        orch = Orchestrator("s1")
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.DECIDED, _ctx())
        assert orch.stage is ClaimStage.INTAKE

    def test_audit_details_contain_from_and_to(self):
        audit = MagicMock()
        orch = Orchestrator("s1", audit_fn=audit)
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.DECIDED, _ctx())
        details = audit.call_args.kwargs["details"]
        assert details["from_stage"] == "INTAKE"
        assert details["to_stage"] == "DECIDED"


# ---------------------------------------------------------------------------
# Orchestrator.record_token_use
# ---------------------------------------------------------------------------


class TestOrchestratorRecordTokenUse:
    def test_normal_use_accumulates(self):
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_session_tokens=100))
        orch.record_token_use(30)
        orch.record_token_use(20)
        assert orch.budget.tokens_used == 50

    def test_exceeds_raises_budget_exceeded(self):
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_session_tokens=10))
        with pytest.raises(BudgetExceededError) as exc_info:
            orch.record_token_use(11)
        assert exc_info.value.kind == "tokens"

    def test_audit_security_event_on_exceeded(self):
        audit = MagicMock()
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_session_tokens=10), audit_fn=audit)
        with pytest.raises(BudgetExceededError):
            orch.record_token_use(11)
        call_kwargs = audit.call_args.kwargs
        assert call_kwargs["action"] == "budget_exceeded"
        assert call_kwargs["security_event"] is True
        assert call_kwargs["details"]["kind"] == "tokens"

    def test_session_halted_after_exceeded(self):
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_session_tokens=5))
        with pytest.raises(BudgetExceededError):
            orch.record_token_use(6)
        assert orch.budget.halted is True

    def test_no_audit_on_normal_use(self):
        audit = MagicMock()
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_session_tokens=100), audit_fn=audit)
        orch.record_token_use(10)
        audit.assert_not_called()


# ---------------------------------------------------------------------------
# Orchestrator.record_tool_call
# ---------------------------------------------------------------------------


class TestOrchestratorRecordToolCall:
    def test_normal_tool_call_tracked(self):
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_tool_calls_per_agent=5))
        orch.record_tool_call("agent-a")
        assert orch.budget.tool_calls["agent-a"] == 1

    def test_exceeds_raises_budget_exceeded(self):
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_tool_calls_per_agent=1))
        orch.record_tool_call("agent-a")
        with pytest.raises(BudgetExceededError) as exc_info:
            orch.record_tool_call("agent-a")
        assert exc_info.value.kind == "tool_calls"
        assert exc_info.value.agent_id == "agent-a"

    def test_audit_security_event_on_exceeded(self):
        audit = MagicMock()
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_tool_calls_per_agent=1), audit_fn=audit)
        orch.record_tool_call("agent-a")
        with pytest.raises(BudgetExceededError):
            orch.record_tool_call("agent-a")
        call_kwargs = audit.call_args.kwargs
        assert call_kwargs["action"] == "budget_exceeded"
        assert call_kwargs["security_event"] is True
        assert call_kwargs["details"]["kind"] == "tool_calls"
        assert call_kwargs["details"]["agent_id"] == "agent-a"

    def test_no_audit_on_normal_tool_call(self):
        audit = MagicMock()
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_tool_calls_per_agent=5), audit_fn=audit)
        orch.record_tool_call("agent-a")
        audit.assert_not_called()

    def test_halted_session_blocks_transitions_too(self):
        orch = Orchestrator("s1", budget_config=BudgetConfig(max_tool_calls_per_agent=1))
        orch.record_tool_call("agent-a")
        with pytest.raises(BudgetExceededError):
            orch.record_tool_call("agent-a")
        # Budget is halted — token use also rejected
        with pytest.raises(BudgetExceededError):
            orch.record_token_use(1)


# ---------------------------------------------------------------------------
# Orchestrator — audit fn defaults to no-op
# ---------------------------------------------------------------------------


class TestOrchestratorNoOpAudit:
    def test_no_audit_fn_does_not_raise(self):
        orch = Orchestrator("s1")
        # Transition succeeds silently
        orch.request_transition(ClaimStage.IDENTITY_PENDING, _ctx(intake_complete=True))

    def test_violation_with_no_audit_fn_still_raises(self):
        orch = Orchestrator("s1")
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.DECIDED, _ctx())


# ---------------------------------------------------------------------------
# dispatch_intent — pure routing logic (task 4.1.7)
# ---------------------------------------------------------------------------


class TestDispatchIntent:
    def test_new_claim_routes_to_claim_filing(self):
        assert dispatch_intent(ClaimIntent.new_claim) == IntentRoute.claim_filing

    def test_faq_routes_to_faq_response(self):
        assert dispatch_intent(ClaimIntent.faq) == IntentRoute.faq_response

    def test_claim_status_routes_to_inquiry(self):
        assert dispatch_intent(ClaimIntent.claim_status) == IntentRoute.inquiry

    def test_policy_question_routes_to_inquiry(self):
        assert dispatch_intent(ClaimIntent.policy_question) == IntentRoute.inquiry

    def test_complaint_routes_to_complaint_capture(self):
        assert dispatch_intent(ClaimIntent.complaint) == IntentRoute.complaint_capture

    def test_claim_status_and_policy_question_share_route(self):
        assert (
            dispatch_intent(ClaimIntent.claim_status)
            == dispatch_intent(ClaimIntent.policy_question)
        )

    def test_all_intents_are_mapped(self):
        for intent in ClaimIntent:
            route = dispatch_intent(intent)
            assert isinstance(route, IntentRoute)


# ---------------------------------------------------------------------------
# Orchestrator.dispatch_on_intent — audit integration (task 4.1.7)
# ---------------------------------------------------------------------------


class TestOrchestratorDispatchOnIntent:
    def _make_orch(self):
        audit_calls: list[dict] = []

        def _audit(**kwargs):
            audit_calls.append(kwargs)

        orch = Orchestrator("sess-intent-01", audit_fn=_audit)
        return orch, audit_calls

    def test_returns_correct_route(self):
        orch, _ = self._make_orch()
        assert orch.dispatch_on_intent(ClaimIntent.new_claim) == IntentRoute.claim_filing

    def test_claim_status_returns_inquiry(self):
        orch, _ = self._make_orch()
        assert orch.dispatch_on_intent(ClaimIntent.claim_status) == IntentRoute.inquiry

    def test_policy_question_returns_inquiry(self):
        orch, _ = self._make_orch()
        assert orch.dispatch_on_intent(ClaimIntent.policy_question) == IntentRoute.inquiry

    def test_emits_intent_routed_audit_event(self):
        orch, events = self._make_orch()
        orch.dispatch_on_intent(ClaimIntent.faq)
        assert any(e["action"] == "intent_routed" for e in events)

    def test_audit_event_contains_intent_and_route(self):
        orch, events = self._make_orch()
        orch.dispatch_on_intent(ClaimIntent.complaint)
        ev = next(e for e in events if e["action"] == "intent_routed")
        assert ev["details"]["intent"] == "complaint"
        assert ev["details"]["route"] == "complaint_capture"

    def test_audit_event_not_security_event(self):
        orch, events = self._make_orch()
        orch.dispatch_on_intent(ClaimIntent.new_claim)
        ev = next(e for e in events if e["action"] == "intent_routed")
        assert ev["security_event"] is False

    def test_audit_event_agent_id_is_orchestrator(self):
        orch, events = self._make_orch()
        orch.dispatch_on_intent(ClaimIntent.faq)
        ev = next(e for e in events if e["action"] == "intent_routed")
        assert ev["agent_id"] == Orchestrator.AGENT_ID


# ---------------------------------------------------------------------------
# Orchestrator.request_transition — DB-write (task 4.2.4)
# ---------------------------------------------------------------------------


def _make_mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


class TestOrchestratorTransitionDBWrite:
    def _make_orch(self, initial: ClaimStage = ClaimStage.PROCESSING):
        events: list[dict] = []

        def _audit(*, agent_id, action, target, data_label, trace_id=None, details=None, security_event=False):
            events.append({"agent_id": agent_id, "action": action, "target": target,
                           "data_label": data_label, "details": details or {},
                           "security_event": security_event})

        orch = Orchestrator("db-write-sess", initial_stage=initial, audit_fn=_audit)
        return orch, events

    def test_writes_claim_stage_to_db_when_both_provided(self):
        orch, _ = self._make_orch(ClaimStage.PROCESSING)
        conn, cur = _make_mock_conn()
        ctx = _full_processing_ctx()
        orch.request_transition(ClaimStage.DECIDED, ctx, claim_id="CLM-db-001", conn=conn)
        cur.execute.assert_called_once()
        call_args = cur.execute.call_args
        sql, params = call_args[0]
        assert "UPDATE claims" in sql
        assert "claim_stage" in sql
        assert params[0] == ClaimStage.DECIDED.value
        assert params[1] == "CLM-db-001"

    def test_memory_stage_updated_after_db_write(self):
        orch, _ = self._make_orch(ClaimStage.PROCESSING)
        conn, _ = _make_mock_conn()
        ctx = _full_processing_ctx()
        orch.request_transition(ClaimStage.DECIDED, ctx, claim_id="CLM-db-002", conn=conn)
        assert orch.stage == ClaimStage.DECIDED

    def test_no_db_write_when_conn_is_none(self):
        orch, _ = self._make_orch(ClaimStage.PROCESSING)
        ctx = _full_processing_ctx()
        orch.request_transition(ClaimStage.DECIDED, ctx, claim_id="CLM-db-003", conn=None)
        assert orch.stage == ClaimStage.DECIDED

    def test_no_db_write_when_claim_id_is_none(self):
        orch, _ = self._make_orch(ClaimStage.PROCESSING)
        conn, cur = _make_mock_conn()
        ctx = _full_processing_ctx()
        orch.request_transition(ClaimStage.DECIDED, ctx, claim_id=None, conn=conn)
        cur.execute.assert_not_called()

    def test_no_db_write_on_violation(self):
        orch, _ = self._make_orch(ClaimStage.INTAKE)
        conn, cur = _make_mock_conn()
        ctx = _ctx()
        with pytest.raises(TransitionViolationError):
            orch.request_transition(ClaimStage.DECIDED, ctx, claim_id="CLM-db-004", conn=conn)
        cur.execute.assert_not_called()
        assert orch.stage == ClaimStage.INTAKE
