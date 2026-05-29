"""Unit tests for the stub claims processor (task 2.1.5).

Run via:
  make test-claims-processor-actor
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_system.actors.claims_processor_actor import (
    ACTOR_AGENT_ID,
    ProcessorEnvelope,
    _STUB_COVERAGE_CALCULATION,
    _STUB_DAMAGE_ASSESSMENT,
    _STUB_FRAUD_SIGNAL,
    run_claims_processor_stub,
)
from agent_system.orchestrator.transitions import TransitionGuardContext

pytestmark = pytest.mark.unit


def _audit_mock() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# ProcessorEnvelope — dataclass contract
# ---------------------------------------------------------------------------


class TestProcessorEnvelope:
    def test_is_frozen(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        with pytest.raises((TypeError, AttributeError)):
            env.fraud_signal = "FLAG"  # type: ignore[misc]

    def test_claim_id_preserved(self):
        env = run_claims_processor_stub(claim_id="CLM-42")
        assert env.claim_id == "CLM-42"

    def test_session_id_preserved(self):
        env = run_claims_processor_stub(claim_id="CLM-001", session_id="sess-7")
        assert env.session_id == "sess-7"

    def test_session_id_default_unknown(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert env.session_id == "unknown"


# ---------------------------------------------------------------------------
# Hardcoded assessment values
# ---------------------------------------------------------------------------


class TestHardcodedValues:
    def test_damage_assessment_is_stub_value(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert env.damage_assessment == _STUB_DAMAGE_ASSESSMENT

    def test_coverage_calculation_is_stub_value(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert env.coverage_calculation == _STUB_COVERAGE_CALCULATION

    def test_fraud_signal_is_clear(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert env.fraud_signal == "CLEAR"

    def test_fraud_signal_is_stub_value(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert env.fraud_signal == _STUB_FRAUD_SIGNAL

    def test_damage_assessment_is_non_empty_string(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert isinstance(env.damage_assessment, str)
        assert len(env.damage_assessment) > 0

    def test_coverage_calculation_is_non_empty_string(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert isinstance(env.coverage_calculation, str)
        assert len(env.coverage_calculation) > 0


# ---------------------------------------------------------------------------
# Orchestrator guard context compatibility
# ---------------------------------------------------------------------------


class TestGuardContextCompatibility:
    def test_satisfies_processing_to_decided_guard(self):
        """All three fields required by PROCESSING → DECIDED must be non-None."""
        env = run_claims_processor_stub(claim_id="CLM-001")
        ctx = TransitionGuardContext(
            damage_assessment=env.damage_assessment,
            coverage_calculation=env.coverage_calculation,
            fraud_decision=env.fraud_signal,
        )
        from agent_system.orchestrator.transitions import ClaimStage, advance_stage
        result = advance_stage(ClaimStage.PROCESSING, ClaimStage.DECIDED, ctx)
        assert result == ClaimStage.DECIDED

    def test_fraud_signal_clear_allows_settled(self):
        """fraud_signal='CLEAR' + settlement_amount within limit allows DECIDED → SETTLED."""
        env = run_claims_processor_stub(claim_id="CLM-001")
        ctx = TransitionGuardContext(
            fraud_decision=env.fraud_signal,
            settlement_amount=5000.0,
        )
        from agent_system.orchestrator.transitions import ClaimStage, advance_stage
        result = advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx)
        assert result == ClaimStage.SETTLED


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_audit_called_once(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        audit.assert_called_once()

    def test_audit_action_processor_assessment(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["action"] == "processor_assessment"

    def test_audit_agent_id(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["agent_id"] == ACTOR_AGENT_ID

    def test_audit_target_is_session_id(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", session_id="sess-xyz", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["target"] == "sess-xyz"

    def test_audit_data_label_confidential(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["data_label"] == "CONFIDENTIAL"

    def test_audit_not_security_event(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["security_event"] is False

    def test_audit_details_has_claim_id(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-007", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["details"]["claim_id"] == "CLM-007"

    def test_audit_details_has_fraud_signal(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert "fraud_signal" in kwargs["details"]

    def test_audit_details_has_damage_assessment(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert "damage_assessment" in kwargs["details"]

    def test_audit_details_stub_flag_is_true(self):
        audit = _audit_mock()
        run_claims_processor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["details"]["stub"] is True

    def test_no_audit_fn_does_not_raise(self):
        run_claims_processor_stub(claim_id="CLM-001")  # audit_fn=None → noop

    def test_returns_envelope_instance(self):
        env = run_claims_processor_stub(claim_id="CLM-001")
        assert isinstance(env, ProcessorEnvelope)
