"""Unit tests for score_fraud tool (Sprint 4.1.3).

score_fraud reads claims+policies via DB and applies amount-based rules
(mirrors seed.py _fraud_decision):
  amount > $40 000 → DENY
  amount > $20 000 → FLAG
  otherwise        → CLEAR  (fast-inception <30 days escalates to FLAG)

Pure tests set the ContextVar directly; registry tests verify SECRET-label
propagation to the audit row.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.claims_tools import (
    _FACTORS_CLEAR,
    _FACTORS_DENY,
    _FACTORS_FLAG,
    score_fraud,
)
from agent_system.tools.implementations.sample_tools import approve_claim
from agent_system.tools.registry import ToolRegistry
from agent_system.tools.tool_context import _conn_var


# ---------------------------------------------------------------------------
# Seeded rows matching seed.py _fraud_decision thresholds
# ---------------------------------------------------------------------------

# (total_claim_amount, incident_date, policy_bind_date)
_ROW_CLEAR  = (Decimal("10000.00"),  date(2024, 6, 1),  date(2023, 1, 1))
_ROW_FLAG   = (Decimal("25000.00"),  date(2024, 6, 1),  date(2023, 1, 1))
_ROW_DENY   = (Decimal("50000.00"),  date(2024, 6, 1),  date(2023, 1, 1))
# Fast-inception: incident within 30 days of policy bind → CLEAR → FLAG
_ROW_FAST   = (Decimal("10000.00"),  date(2024, 1, 15), date(2024, 1, 1))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_conn(row):
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = row
    conn.cursor.return_value = cur
    return conn


def _make_registry_conn(row):
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.side_effect = [(None,), row]
    conn.cursor.return_value = cur
    return conn


@contextmanager
def _conn_ctx(row):
    conn = _make_mock_conn(row)
    token = _conn_var.set(conn)
    try:
        yield conn
    finally:
        _conn_var.reset(token)


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScoreFraudPure:
    def test_returns_labeled_dict(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        with _conn_ctx(_ROW_FLAG):
            a = score_fraud("CLM-det")
        with _conn_ctx(_ROW_FLAG):
            b = score_fraud("CLM-det")
        assert a.value == b.value

    def test_claim_id_echoed(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-echo")
        assert result.value["claim_id"] == "CLM-echo"

    def test_value_has_required_keys(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-keys")
        assert {"claim_id", "risk_score", "risk_factors", "decision"} <= result.value.keys()

    def test_risk_score_in_range(self):
        for row in (_ROW_CLEAR, _ROW_FLAG, _ROW_DENY, _ROW_FAST):
            with _conn_ctx(row):
                result = score_fraud("CLM-range")
            assert 0 <= result.value["risk_score"] <= 100

    def test_risk_score_is_integer(self):
        with _conn_ctx(_ROW_FLAG):
            result = score_fraud("CLM-int")
        assert isinstance(result.value["risk_score"], int)

    def test_risk_factors_is_list(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-list")
        assert isinstance(result.value["risk_factors"], list)

    def test_risk_factors_non_empty(self):
        for row in (_ROW_CLEAR, _ROW_FLAG, _ROW_DENY):
            with _conn_ctx(row):
                result = score_fraud("CLM-nonempty")
            assert len(result.value["risk_factors"]) >= 1

    def test_risk_factors_no_duplicates(self):
        for row in (_ROW_CLEAR, _ROW_FLAG, _ROW_DENY, _ROW_FAST):
            with _conn_ctx(row):
                factors = score_fraud("CLM-dedup").value["risk_factors"]
            assert len(factors) == len(set(factors)), f"duplicates in {factors}"

    def test_decision_valid(self):
        for row in (_ROW_CLEAR, _ROW_FLAG, _ROW_DENY):
            with _conn_ctx(row):
                result = score_fraud("CLM-decision")
            assert result.value["decision"] in {"CLEAR", "FLAG", "DENY"}

    # ── Decision boundary tests ────────────────────────────────────────────

    def test_amount_above_40k_is_deny(self):
        row = (Decimal("40001.00"), date(2024, 6, 1), date(2023, 1, 1))
        with _conn_ctx(row):
            result = score_fraud("CLM-deny-boundary")
        assert result.value["decision"] == "DENY"

    def test_amount_at_40k_is_flag(self):
        row = (Decimal("40000.00"), date(2024, 6, 1), date(2023, 1, 1))
        with _conn_ctx(row):
            result = score_fraud("CLM-40k-flag")
        assert result.value["decision"] == "FLAG"

    def test_amount_above_20k_below_40k_is_flag(self):
        with _conn_ctx(_ROW_FLAG):
            result = score_fraud("CLM-flag-range")
        assert result.value["decision"] == "FLAG"
        assert 30 <= result.value["risk_score"] <= 59

    def test_amount_at_or_below_20k_is_clear(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-clear-range")
        assert result.value["decision"] == "CLEAR"
        assert result.value["risk_score"] < 30

    def test_deny_score_at_least_60(self):
        with _conn_ctx(_ROW_DENY):
            result = score_fraud("CLM-deny-score")
        assert result.value["risk_score"] >= 60

    def test_fast_inception_escalates_clear_to_flag(self):
        """CLEAR amount + claim within 30 days of bind → FLAG."""
        with _conn_ctx(_ROW_FAST):
            result = score_fraud("CLM-fast")
        assert result.value["decision"] == "FLAG"

    def test_deny_has_at_least_two_factors(self):
        with _conn_ctx(_ROW_DENY):
            result = score_fraud("CLM-deny-factors")
        assert len(result.value["risk_factors"]) >= 2

    def test_deny_factors_from_catalogue(self):
        with _conn_ctx(_ROW_DENY):
            result = score_fraud("CLM-deny-cat")
        for f in result.value["risk_factors"]:
            assert f in _FACTORS_DENY

    def test_flag_factors_from_catalogue(self):
        with _conn_ctx(_ROW_FLAG):
            result = score_fraud("CLM-flag-cat")
        for f in result.value["risk_factors"]:
            assert f in _FACTORS_FLAG

    def test_clear_factors_from_catalogue(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-clear-cat")
        for f in result.value["risk_factors"]:
            assert f in _FACTORS_CLEAR

    def test_ifc_label_is_secret(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-label")
        assert result.label.level == DataLabel.SECRET

    def test_ifc_label_not_untrusted(self):
        with _conn_ctx(_ROW_CLEAR):
            result = score_fraud("CLM-untrusted")
        assert result.label.untrusted is False

    def test_raises_when_no_claim(self):
        conn = _make_mock_conn(None)
        token = _conn_var.set(conn)
        try:
            with pytest.raises(ValueError, match="No claim found"):
                score_fraud("CLM-missing")
        finally:
            _conn_var.reset(token)

    def test_no_conn_context_raises_runtime_error(self):
        cv_token = _conn_var.set(None)
        try:
            with pytest.raises(RuntimeError, match="No database connection"):
                score_fraud("CLM-no-ctx")
        finally:
            _conn_var.reset(cv_token)


# ---------------------------------------------------------------------------
# ToolRegistry integration tests — SECRET label propagation
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def fraud_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("score_fraud", score_fraud)
    return r


@pytest.fixture()
def fraud_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="score_fraud",
        scope={"claim_id": "CLM-token-001"},
    )


def _invoke_fraud(registry, token, orchestrator_km, *, params=None, db_row=_ROW_FLAG):
    if params is None:
        params = {"claim_id": "CLM-token-001"}
    conn = _make_registry_conn(db_row)
    with (
        patch("agent_system.tools.registry.append_log", return_value=42) as mock_log,
        patch("agent_system.tools.registry.record_use"),
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="score_fraud",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log


@pytest.mark.unit
class TestScoreFraudRegistry:
    def test_invocation_succeeds(self, fraud_registry, fraud_token, orchestrator_km):
        result, _ = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert result

    def test_audit_row_data_label_is_secret(self, fraud_registry, fraud_token, orchestrator_km):
        """Registry must record SECRET in the audit row."""
        _, mock_log = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "SECRET"

    def test_result_value_is_labeled(self, fraud_registry, fraud_token, orchestrator_km):
        result, _ = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_label_is_secret(self, fraud_registry, fraud_token, orchestrator_km):
        result, _ = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert result.value.label.level == DataLabel.SECRET

    def test_deny_decision_from_db(self, fraud_registry, fraud_token, orchestrator_km):
        """DENY amount row must produce decision=DENY through registry."""
        result, _ = _invoke_fraud(
            fraud_registry, fraud_token, orchestrator_km, db_row=_ROW_DENY
        )
        assert result.value.value["decision"] == "DENY"

    def test_clear_decision_from_db(self, fraud_registry, fraud_token, orchestrator_km):
        result, _ = _invoke_fraud(
            fraud_registry, fraud_token, orchestrator_km, db_row=_ROW_CLEAR
        )
        assert result.value.value["decision"] == "CLEAR"


# ---------------------------------------------------------------------------
# Regression: plain-dict tool still produces CONFIDENTIAL audit label
# ---------------------------------------------------------------------------


@pytest.fixture()
def plain_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("approve_claim", approve_claim)
    return r


@pytest.fixture()
def plain_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="approve_claim",
        scope={"claim_id": "CLM-001", "amount": 4000},
    )


@pytest.mark.unit
class TestRegistryPlainDictFallback:
    def test_plain_dict_tool_audit_label_is_confidential(
        self, plain_registry, plain_token, orchestrator_km
    ):
        """A handler returning a plain dict must still produce data_label=CONFIDENTIAL."""
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = MagicMock(return_value=cur)
        cur.__exit__ = MagicMock(return_value=False)
        cur.fetchone.return_value = (None,)
        conn.cursor.return_value = cur
        with (
            patch("agent_system.tools.registry.append_log", return_value=1) as mock_log,
            patch("agent_system.tools.registry.record_use"),
            patch("agent_system.tools.registry._try_record_use"),
        ):
            result = plain_registry.invoke(
                conn,
                token=plain_token,
                calling_agent_id=plain_token.agent_id,
                tool_name="approve_claim",
                params={"claim_id": "CLM-001", "amount": 4000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                trace_id=uuid.uuid4(),
            )
        assert result
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"
