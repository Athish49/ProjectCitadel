"""Unit tests for lookup_coverage tool (Sprint 4.1.2).

The tool reads policy data via claims JOIN policies using a ContextVar-injected
DB connection.  Pure tests set the ContextVar directly; registry tests verify
CONFIDENTIAL-label propagation.
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.claims_tools import (
    AUTO_APPROVE_LIMITS,
    DEDUCTIBLES,
    _COVERAGE_TYPES,
    _POLICY_TYPES,
    lookup_coverage,
)
from agent_system.tools.registry import ToolRegistry
from agent_system.tools.tool_context import _conn_var


# ---------------------------------------------------------------------------
# Seeded policy row — mirrors seed.py ranges
# ---------------------------------------------------------------------------

# (policy_type, coverage_type, policy_deductible, auto_approve_limit, policy_status)
_ROW_ACTIVE = ("COMPREHENSIVE", "STANDARD", 1000, 10000, "ACTIVE")
_ROW_LAPSED = ("COLLISION",     "BASIC",    500,  5000,  "LAPSED")


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
    """Mock conn: first fetchone=replay-check, second=handler row."""
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
class TestLookupCoveragePure:
    def test_returns_labeled_dict(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        with _conn_ctx(_ROW_ACTIVE):
            a = lookup_coverage("CLM-det")
        with _conn_ctx(_ROW_ACTIVE):
            b = lookup_coverage("CLM-det")
        assert a.value == b.value

    def test_claim_id_echoed(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-echo-test")
        assert result.value["claim_id"] == "CLM-echo-test"

    def test_value_has_required_keys(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-keys")
        assert {
            "claim_id", "policy_type", "coverage_type",
            "deductible", "auto_approve_limit", "policy_status",
            "coverage_applicable",
        } <= result.value.keys()

    def test_policy_type_from_db(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-ptype")
        assert result.value["policy_type"] == "COMPREHENSIVE"

    def test_coverage_type_from_db(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-ctype")
        assert result.value["coverage_type"] == "STANDARD"

    def test_deductible_from_db(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-deductible")
        assert result.value["deductible"] == 1000

    def test_deductible_is_int(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-deductible-int")
        assert isinstance(result.value["deductible"], int)

    def test_auto_approve_limit_from_db(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-approve")
        assert result.value["auto_approve_limit"] == 10000

    def test_auto_approve_limit_is_int(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-approve-int")
        assert isinstance(result.value["auto_approve_limit"], int)

    def test_policy_status_active(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-status-active")
        assert result.value["policy_status"] == "ACTIVE"

    def test_coverage_applicable_true_when_active(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-applicable-true")
        assert result.value["coverage_applicable"] is True

    def test_coverage_applicable_false_when_lapsed(self):
        with _conn_ctx(_ROW_LAPSED):
            result = lookup_coverage("CLM-applicable-false")
        assert result.value["coverage_applicable"] is False

    def test_ifc_label_is_confidential(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-label")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        with _conn_ctx(_ROW_ACTIVE):
            result = lookup_coverage("CLM-untrusted")
        assert result.label.untrusted is False

    def test_raises_when_no_row(self):
        conn = _make_mock_conn(None)
        token = _conn_var.set(conn)
        try:
            with pytest.raises(ValueError, match="No policy found"):
                lookup_coverage("CLM-missing")
        finally:
            _conn_var.reset(token)

    def test_no_conn_context_raises_runtime_error(self):
        cv_token = _conn_var.set(None)
        try:
            with pytest.raises(RuntimeError, match="No database connection"):
                lookup_coverage("CLM-no-ctx")
        finally:
            _conn_var.reset(cv_token)


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def coverage_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("lookup_coverage", lookup_coverage)
    return r


@pytest.fixture()
def coverage_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="lookup_coverage",
        scope={"claim_id": "CLM-token-001"},
    )


def _invoke_coverage(registry, token, orchestrator_km, *, params=None, db_row=_ROW_ACTIVE):
    if params is None:
        params = {"claim_id": "CLM-token-001"}
    conn = _make_registry_conn(db_row)
    with (
        patch("agent_system.tools.registry.append_log", return_value=42) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="lookup_coverage",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


@pytest.mark.unit
class TestLookupCoverageRegistry:
    def test_valid_invocation_succeeds(self, coverage_registry, coverage_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_coverage(
            coverage_registry, coverage_token, orchestrator_km
        )
        assert result
        assert result.log_id == 42
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, coverage_registry, coverage_token, orchestrator_km):
        result, _, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_inner_dict_keys(self, coverage_registry, coverage_token, orchestrator_km):
        result, _, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        inner = result.value.value
        assert {"claim_id", "policy_type", "coverage_type", "deductible",
                "auto_approve_limit", "policy_status", "coverage_applicable"} <= inner.keys()

    def test_result_ifc_label_confidential(self, coverage_registry, coverage_token, orchestrator_km):
        result, _, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_audit_data_label_confidential(self, coverage_registry, coverage_token, orchestrator_km):
        _, mock_log, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"

    def test_audit_params_keys_not_values(self, coverage_registry, coverage_token, orchestrator_km):
        _, mock_log, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim_id" not in details

    def test_policy_data_from_db(self, coverage_registry, coverage_token, orchestrator_km):
        """Policy fields must come from the mocked DB row."""
        result, _, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        inner = result.value.value
        assert inner["policy_type"] == "COMPREHENSIVE"
        assert inner["deductible"] == 1000
        assert inner["coverage_applicable"] is True
