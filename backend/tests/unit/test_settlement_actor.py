"""Unit tests for the stub settlement actor (task 2.1.6).

Run via:
  make test-settlement-actor
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_system.actors.settlement_actor import (
    ACTOR_AGENT_ID,
    SettlementEnvelope,
    _STUB_PAYOUT_STATUS,
    _STUB_SETTLEMENT_AMOUNT,
    _STUB_SUMMARY,
    run_settlement_actor_stub,
)
from agent_system.orchestrator.transitions import (
    ClaimStage,
    TransitionGuardContext,
    advance_stage,
)

pytestmark = pytest.mark.unit


def _audit_mock() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# SettlementEnvelope — dataclass contract
# ---------------------------------------------------------------------------


class TestSettlementEnvelope:
    def test_is_frozen(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        with pytest.raises((TypeError, AttributeError)):
            env.settlement_amount = 99999.0  # type: ignore[misc]

    def test_claim_id_preserved(self):
        env = run_settlement_actor_stub(claim_id="CLM-55")
        assert env.claim_id == "CLM-55"

    def test_session_id_preserved(self):
        env = run_settlement_actor_stub(claim_id="CLM-001", session_id="sess-12")
        assert env.session_id == "sess-12"

    def test_session_id_default_unknown(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert env.session_id == "unknown"


# ---------------------------------------------------------------------------
# Hardcoded settlement values
# ---------------------------------------------------------------------------


class TestHardcodedValues:
    def test_settlement_amount_is_stub_value(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert env.settlement_amount == _STUB_SETTLEMENT_AMOUNT

    def test_payout_status_is_stub_value(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert env.payout_status == _STUB_PAYOUT_STATUS

    def test_summary_is_stub_value(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert env.summary == _STUB_SUMMARY

    def test_settlement_amount_is_positive(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert env.settlement_amount > 0

    def test_summary_is_non_empty_string(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert isinstance(env.summary, str)
        assert len(env.summary) > 0

    def test_payout_status_is_non_empty_string(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert isinstance(env.payout_status, str)
        assert len(env.payout_status) > 0


# ---------------------------------------------------------------------------
# Orchestrator guard context compatibility
# ---------------------------------------------------------------------------


class TestGuardContextCompatibility:
    def test_settlement_amount_within_auto_approve_limit(self):
        """settlement_amount must be ≤ 10,000 to pass the DECIDED → SETTLED guard."""
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert env.settlement_amount <= 10_000.0

    def test_satisfies_decided_to_settled_guard(self):
        """Combined with fraud_signal=CLEAR, envelope satisfies DECIDED → SETTLED."""
        env = run_settlement_actor_stub(claim_id="CLM-001")
        ctx = TransitionGuardContext(
            fraud_decision="CLEAR",
            settlement_amount=env.settlement_amount,
        )
        result = advance_stage(ClaimStage.DECIDED, ClaimStage.SETTLED, ctx)
        assert result == ClaimStage.SETTLED

    def test_settled_to_closed_allowed(self):
        """Pipeline can advance SETTLED → CLOSED after settlement."""
        ctx = TransitionGuardContext()
        result = advance_stage(ClaimStage.SETTLED, ClaimStage.CLOSED, ctx)
        assert result == ClaimStage.CLOSED


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_audit_called_once(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        audit.assert_called_once()

    def test_audit_action_settlement_issued(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["action"] == "settlement_issued"

    def test_audit_agent_id(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["agent_id"] == ACTOR_AGENT_ID

    def test_audit_target_is_session_id(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", session_id="sess-abc", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["target"] == "sess-abc"

    def test_audit_data_label_confidential(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["data_label"] == "CONFIDENTIAL"

    def test_audit_not_security_event(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["security_event"] is False

    def test_audit_details_has_claim_id(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-999", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["details"]["claim_id"] == "CLM-999"

    def test_audit_details_has_settlement_amount(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert "settlement_amount" in kwargs["details"]

    def test_audit_details_has_payout_status(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert "payout_status" in kwargs["details"]

    def test_audit_details_stub_flag_is_true(self):
        audit = _audit_mock()
        run_settlement_actor_stub(claim_id="CLM-001", audit_fn=audit)
        _, kwargs = audit.call_args
        assert kwargs["details"]["stub"] is True

    def test_no_audit_fn_does_not_raise(self):
        run_settlement_actor_stub(claim_id="CLM-001")

    def test_returns_envelope_instance(self):
        env = run_settlement_actor_stub(claim_id="CLM-001")
        assert isinstance(env, SettlementEnvelope)
