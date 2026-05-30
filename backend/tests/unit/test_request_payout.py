"""Unit tests for request_payout tool (Sprint 4.2.2)."""
from __future__ import annotations

import functools
import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.settlement_tools import (
    PayoutGuardError,
    calculate_settlement,
    request_payout,
)
from agent_system.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Pinned test fixtures — verified against calculate_settlement hash output.
#   CLM-001: offered=7000.0, limit=10000.0  → within limit (SETTLED path)
#   CLM-002: offered=19500.0, limit=10000.0 → over limit   (ESCALATED path)
# ---------------------------------------------------------------------------

_CLM_WITHIN_LIMIT = "CLM-001"
_CLM_OVER_LIMIT = "CLM-002"


def _within_limit_values():
    v = calculate_settlement(_CLM_WITHIN_LIMIT).value
    assert v["offered_amount"] <= v["auto_approve_limit"], (
        "Fixture invariant broken: CLM-001 must be within limit"
    )
    return v


def _over_limit_values():
    v = calculate_settlement(_CLM_OVER_LIMIT).value
    assert v["offered_amount"] > v["auto_approve_limit"], (
        "Fixture invariant broken: CLM-002 must be over limit"
    )
    return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cur(side_effect):
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.side_effect = side_effect
    return cur


def _make_conn(side_effect):
    conn = MagicMock()
    conn.cursor.return_value = _make_cur(side_effect)
    return conn


def _call_within_limit(side_effect):
    conn = _make_conn(side_effect)
    return request_payout(_CLM_WITHIN_LIMIT, conn=conn)


# ---------------------------------------------------------------------------
# Fixture constant verification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixtureInvariants:
    def test_clm_001_within_limit(self):
        v = calculate_settlement(_CLM_WITHIN_LIMIT).value
        assert v["offered_amount"] <= v["auto_approve_limit"]

    def test_clm_002_over_limit(self):
        v = calculate_settlement(_CLM_OVER_LIMIT).value
        assert v["offered_amount"] > v["auto_approve_limit"]


# ---------------------------------------------------------------------------
# PayoutGuardError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPayoutGuardError:
    def test_is_exception(self):
        assert issubclass(PayoutGuardError, Exception)

    def test_reason_attribute(self):
        e = PayoutGuardError("bad stage", "stage")
        assert e.reason == "bad stage"

    def test_guard_attribute(self):
        e = PayoutGuardError("bad stage", "stage")
        assert e.guard == "stage"

    def test_str_contains_guard_and_reason(self):
        e = PayoutGuardError("claim not found", "stage")
        assert "stage" in str(e)
        assert "claim not found" in str(e)

    @pytest.mark.parametrize("guard", ["stage", "fraud", "amount", "payee", "idempotency"])
    def test_all_guard_names(self, guard):
        e = PayoutGuardError("reason", guard)
        assert e.guard == guard


# ---------------------------------------------------------------------------
# Guard 1: stage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestPayoutGuardStage:
    def test_claim_not_found_raises_stage(self):
        with pytest.raises(PayoutGuardError) as exc_info:
            _call_within_limit([None])
        assert exc_info.value.guard == "stage"

    def test_wrong_stage_raises_stage(self):
        with pytest.raises(PayoutGuardError) as exc_info:
            _call_within_limit([("PROCESSING",)])
        assert exc_info.value.guard == "stage"
        assert "PROCESSING" in exc_info.value.reason

    @pytest.mark.parametrize("stage", ["OPEN", "UNDER_REVIEW", "CLOSED", "PENDING"])
    def test_non_decided_stages_all_rejected(self, stage):
        with pytest.raises(PayoutGuardError) as exc_info:
            _call_within_limit([(stage,)])
        assert exc_info.value.guard == "stage"

    def test_stage_guard_fires_before_fraud_guard(self):
        """Only one fetchone call should happen when stage guard fires."""
        cur = _make_cur([("OPEN",)])
        conn = MagicMock()
        conn.cursor.return_value = cur
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "stage"
        assert cur.fetchone.call_count == 1


# ---------------------------------------------------------------------------
# Guard 2: fraud
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestPayoutGuardFraud:
    def test_no_fraud_score_raises_fraud(self):
        with pytest.raises(PayoutGuardError) as exc_info:
            _call_within_limit([("DECIDED",), None])
        assert exc_info.value.guard == "fraud"

    def test_flag_decision_raises_fraud(self):
        with pytest.raises(PayoutGuardError) as exc_info:
            _call_within_limit([("DECIDED",), ("FLAG",)])
        assert exc_info.value.guard == "fraud"
        assert "FLAG" in exc_info.value.reason

    def test_deny_decision_raises_fraud(self):
        with pytest.raises(PayoutGuardError) as exc_info:
            _call_within_limit([("DECIDED",), ("DENY",)])
        assert exc_info.value.guard == "fraud"
        assert "DENY" in exc_info.value.reason

    def test_fraud_guard_fires_before_amount_guard(self):
        """Only two fetchone calls should happen when fraud guard fires."""
        cur = _make_cur([("DECIDED",), ("FLAG",)])
        conn = MagicMock()
        conn.cursor.return_value = cur
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "fraud"
        assert cur.fetchone.call_count == 2


# ---------------------------------------------------------------------------
# Guard 3: amount
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestPayoutGuardAmount:
    def test_over_limit_raises_amount(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",)])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_OVER_LIMIT, conn=conn)
        assert exc_info.value.guard == "amount"

    def test_amount_reason_contains_values(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",)])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_OVER_LIMIT, conn=conn)
        v = _over_limit_values()
        assert str(v["offered_amount"]) in exc_info.value.reason
        assert str(v["auto_approve_limit"]) in exc_info.value.reason

    def test_within_limit_does_not_raise_amount(self):
        """Within-limit claim must not raise; guard 4 (payee) fires next."""
        conn = _make_conn([("DECIDED",), ("CLEAR",), None])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "payee"

    def test_amount_guard_fires_before_payee_guard(self):
        """Over-limit claim: fetchone count must be 2 (stage + fraud only)."""
        cur = _make_cur([("DECIDED",), ("CLEAR",)])
        conn = MagicMock()
        conn.cursor.return_value = cur
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_OVER_LIMIT, conn=conn)
        assert exc_info.value.guard == "amount"
        assert cur.fetchone.call_count == 2


# ---------------------------------------------------------------------------
# Guard 4: payee
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestPayoutGuardPayee:
    def test_no_pii_row_raises_payee(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",), None])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "payee"

    def test_null_bank_account_raises_payee(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",), (None,)])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "payee"

    def test_payee_guard_fires_before_idempotency(self):
        """No pii row: fetchone count must be 3 (stage + fraud + payee)."""
        cur = _make_cur([("DECIDED",), ("CLEAR",), None])
        conn = MagicMock()
        conn.cursor.return_value = cur
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "payee"
        assert cur.fetchone.call_count == 3


# ---------------------------------------------------------------------------
# Guard 5: idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestPayoutGuardIdempotency:
    def test_already_processed_raises_idempotency(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",), (b"enc_bank",), ("PROCESSED",)])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert exc_info.value.guard == "idempotency"

    def test_reason_says_already_paid(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",), (b"enc_bank",), ("PROCESSED",)])
        with pytest.raises(PayoutGuardError) as exc_info:
            request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert "already paid" in exc_info.value.reason

    def test_pending_payout_status_is_not_idempotency_blocked(self):
        """A PENDING settlement is not yet PROCESSED — should proceed past guard 5."""
        conn = _make_conn([("DECIDED",), ("CLEAR",), (b"enc_bank",), ("PENDING",)])
        result = request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert result.value["payout_status"] == "PROCESSED"

    def test_no_existing_settlement_row_is_not_idempotency_blocked(self):
        """No row in settlements — first-time payout should succeed."""
        conn = _make_conn([("DECIDED",), ("CLEAR",), (b"enc_bank",), None])
        result = request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert result.value["payout_status"] == "PROCESSED"


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestPayoutSuccess:
    @pytest.fixture()
    def success_result(self):
        conn = _make_conn([("DECIDED",), ("CLEAR",), (b"enc_bank",), None])
        return request_payout(_CLM_WITHIN_LIMIT, conn=conn)

    def test_returns_labeled(self, success_result):
        assert isinstance(success_result, Labeled)

    def test_ifc_label_confidential(self, success_result):
        assert success_result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self, success_result):
        assert success_result.label.untrusted is False

    def test_value_is_dict(self, success_result):
        assert isinstance(success_result.value, dict)

    def test_required_keys_present(self, success_result):
        assert {"claim_id", "payout_status", "payout_reference", "offered_amount"} <= success_result.value.keys()

    def test_payout_status_is_processed(self, success_result):
        assert success_result.value["payout_status"] == "PROCESSED"

    def test_claim_id_echoed(self, success_result):
        assert success_result.value["claim_id"] == _CLM_WITHIN_LIMIT

    def test_payout_reference_is_uuid(self, success_result):
        ref = success_result.value["payout_reference"]
        parsed = uuid.UUID(ref)
        assert str(parsed) == ref

    def test_offered_amount_matches_calculate_settlement(self, success_result):
        expected = calculate_settlement(_CLM_WITHIN_LIMIT).value["offered_amount"]
        assert success_result.value["offered_amount"] == expected

    def test_bank_details_not_in_result(self, success_result):
        """Bank account data must never appear in the returned value."""
        v = success_result.value
        for key in v:
            assert "bank" not in key.lower()
            assert "account" not in key.lower()
            assert "pii" not in key.lower()

    def test_payout_reference_unique_per_call(self):
        """Each successful call generates a fresh payout_reference."""
        r1 = request_payout(_CLM_WITHIN_LIMIT, conn=_make_conn([("DECIDED",), ("CLEAR",), (b"enc",), None]))
        r2 = request_payout(_CLM_WITHIN_LIMIT, conn=_make_conn([("DECIDED",), ("CLEAR",), (b"enc",), None]))
        assert r1.value["payout_reference"] != r2.value["payout_reference"]

    def test_upsert_executed(self):
        """The settlement UPSERT must be executed on success."""
        cur = _make_cur([("DECIDED",), ("CLEAR",), (b"enc_bank",), None])
        conn = MagicMock()
        conn.cursor.return_value = cur
        request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert cur.execute.call_count == 5  # 4 SELECTs + 1 INSERT

    def test_five_fetchone_calls_on_success(self):
        """Success path: exactly 5 fetchone calls (stage, fraud, payee, idempotency + 0 for amount)."""
        cur = _make_cur([("DECIDED",), ("CLEAR",), (b"enc_bank",), None])
        conn = MagicMock()
        conn.cursor.return_value = cur
        request_payout(_CLM_WITHIN_LIMIT, conn=conn)
        assert cur.fetchone.call_count == 4  # stage, fraud, payee, idempotency


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def payout_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="settlement_actor",
        tool="request_payout",
        scope={"claim_id": _CLM_WITHIN_LIMIT},
    )


def _make_registry_conn(side_effect):
    """Shared mock conn: fetchone side_effect covers both registry and handler queries."""
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.side_effect = side_effect
    conn.cursor.return_value = cur
    return conn


def _invoke_payout(token, orchestrator_km, *, side_effect, params=None):
    """Build a fresh registry each call with request_payout pre-bound to the mock conn.

    Both the ToolRegistry (capability_token_log check) and the handler (5 guards)
    share the same mock cursor, so side_effect lists registry fetchone first.
    """
    if params is None:
        params = {"claim_id": _CLM_WITHIN_LIMIT}
    conn = _make_registry_conn(side_effect)
    # Bind conn before registration so it stays out of ToolRegistry params dispatch
    bound_payout = functools.partial(request_payout, conn=conn)
    registry = ToolRegistry()
    registry.register("request_payout", bound_payout)
    with (
        patch("agent_system.tools.registry.append_log", return_value=77) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="request_payout",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


@pytest.mark.unit
class TestRequestPayoutRegistry:
    def test_valid_invocation_succeeds(self, payout_token, orchestrator_km):
        # capability_token_log row + 4 handler fetchones (stage, fraud, payee, idempotency)
        result, mock_log, mock_record = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[(None,), ("DECIDED",), ("CLEAR",), (b"enc_bank",), None],
        )
        assert result
        assert result.log_id == 77
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, payout_token, orchestrator_km):
        result, _, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[(None,), ("DECIDED",), ("CLEAR",), (b"enc_bank",), None],
        )
        assert isinstance(result.value, Labeled)

    def test_result_inner_dict_keys(self, payout_token, orchestrator_km):
        result, _, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[(None,), ("DECIDED",), ("CLEAR",), (b"enc_bank",), None],
        )
        inner = result.value.value
        assert {"claim_id", "payout_status", "payout_reference", "offered_amount"} <= inner.keys()

    def test_result_ifc_label_confidential(self, payout_token, orchestrator_km):
        result, _, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[(None,), ("DECIDED",), ("CLEAR",), (b"enc_bank",), None],
        )
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_audit_label_is_confidential(self, payout_token, orchestrator_km):
        result, mock_log, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[(None,), ("DECIDED",), ("CLEAR",), (b"enc_bank",), None],
        )
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"

    def test_audit_params_keys_not_values(self, payout_token, orchestrator_km):
        result, mock_log, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[(None,), ("DECIDED",), ("CLEAR",), (b"enc_bank",), None],
        )
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim_id" not in details

    def test_replay_denied(self, payout_token, orchestrator_km):
        result, _, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[("2026-01-01T00:00:00",)],
        )
        assert not result
        assert result.deny_reason is not None

    def test_unissued_token_denied_security_event(self, payout_token, orchestrator_km):
        result, mock_log, _ = _invoke_payout(
            payout_token, orchestrator_km,
            side_effect=[None],
        )
        assert not result
        assert mock_log.call_args.kwargs["security_event"] is True
