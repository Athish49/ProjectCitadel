"""Unit tests for inquiry tools (Sprint 4.1.8–4.1.9).

lookup_claim_status  — reads from claims table via ContextVar-injected conn
capture_complaint    — INSERTs into complaints table; requires customer_id

Pure tests set the ContextVar directly with mock connections.
Registry tests verify CONFIDENTIAL-label propagation through ToolRegistry.
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
from agent_system.tools.implementations.inquiry_tools import (
    _CLAIM_STAGES,
    _COMPLAINT_CATEGORIES,
    _INCIDENT_TYPES,
    capture_complaint,
    lookup_claim_status,
)
from agent_system.tools.registry import ToolRegistry
from agent_system.tools.tool_context import _conn_var

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Seeded rows
# ---------------------------------------------------------------------------

# (claim_number, claim_stage, incident_type, incident_date, total_claim_amount)
_CLAIM_ROW = (
    "CLM-000001",
    "PROCESSING",
    "collision",
    date(2024, 3, 15),
    Decimal("25000.00"),
)

_CUSTOMER_ID = str(uuid.UUID("00000000-0000-0000-0000-000000000042"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_conn(row, execute_ok=True):
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = row
    conn.cursor.return_value = cur
    return conn


def _make_registry_conn_claim(row):
    """Replay-check fetchone first, then handler fetchone."""
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.side_effect = [(None,), row]
    conn.cursor.return_value = cur
    return conn


def _make_registry_conn_complaint():
    """Replay-check fetchone only; handler does INSERT (no fetchone)."""
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = (None,)
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


@contextmanager
def _conn_ctx_write():
    """Context for tools that only write (capture_complaint with customer_id)."""
    conn = _make_mock_conn(None)
    token = _conn_var.set(conn)
    try:
        yield conn
    finally:
        _conn_var.reset(token)


# ---------------------------------------------------------------------------
# lookup_claim_status — pure tests
# ---------------------------------------------------------------------------


class TestLookupClaimStatusPure:
    def test_returns_labeled_dict(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_ifc_label_is_confidential(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-label")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-untrusted")
        assert result.label.untrusted is False

    def test_required_keys_present(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-keys")
        expected = {
            "claim_id", "claim_number", "claim_stage",
            "incident_type", "incident_date", "total_claim_amount",
        }
        assert expected <= result.value.keys()

    def test_claim_id_echoed(self):
        cid = "claim-echo-abc123"
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status(cid)
        assert result.value["claim_id"] == cid

    def test_claim_number_from_db(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-number")
        assert result.value["claim_number"] == "CLM-000001"

    def test_claim_number_starts_with_clm(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-clm")
        assert result.value["claim_number"].startswith("CLM-")

    def test_claim_stage_from_db(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-stage")
        assert result.value["claim_stage"] == "PROCESSING"

    def test_incident_type_from_db(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-incident")
        assert result.value["incident_type"] == "collision"

    def test_incident_date_is_iso8601(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-date")
        d = date.fromisoformat(result.value["incident_date"])
        assert d.year >= 2020

    def test_total_claim_amount_is_float(self):
        with _conn_ctx(_CLAIM_ROW):
            result = lookup_claim_status("claim-amount")
        assert isinstance(result.value["total_claim_amount"], float)
        assert result.value["total_claim_amount"] == pytest.approx(25000.0)

    def test_deterministic(self):
        with _conn_ctx(_CLAIM_ROW):
            a = lookup_claim_status("claim-det")
        with _conn_ctx(_CLAIM_ROW):
            b = lookup_claim_status("claim-det")
        assert a.value == b.value

    def test_raises_when_no_row(self):
        conn = _make_mock_conn(None)
        token = _conn_var.set(conn)
        try:
            with pytest.raises(ValueError, match="No claim found"):
                lookup_claim_status("claim-missing")
        finally:
            _conn_var.reset(token)

    def test_no_conn_context_raises_runtime_error(self):
        cv_token = _conn_var.set(None)
        try:
            with pytest.raises(RuntimeError, match="No database connection"):
                lookup_claim_status("claim-no-ctx")
        finally:
            _conn_var.reset(cv_token)


# ---------------------------------------------------------------------------
# lookup_claim_status — ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def inquiry_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("lookup_claim_status", lookup_claim_status)
    return r


@pytest.fixture()
def status_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="lookup_claim_status",
        scope={"claim_id": "claim-token-001"},
    )


def _invoke_status(registry, token, orchestrator_km, *, params=None, db_row=_CLAIM_ROW):
    if params is None:
        params = {"claim_id": "claim-token-001"}
    conn = _make_registry_conn_claim(db_row)
    with (
        patch("agent_system.tools.registry.append_log", return_value=7) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="lookup_claim_status",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


class TestLookupClaimStatusRegistry:
    def test_valid_invocation_succeeds(self, inquiry_registry, status_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_status(
            inquiry_registry, status_token, orchestrator_km
        )
        assert result
        assert result.log_id == 7
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, inquiry_registry, status_token, orchestrator_km):
        result, _, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_value_inner_keys(self, inquiry_registry, status_token, orchestrator_km):
        result, _, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        inner = result.value.value
        assert {"claim_id", "claim_number", "claim_stage"} <= inner.keys()

    def test_result_value_ifc_label_confidential(self, inquiry_registry, status_token, orchestrator_km):
        result, _, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_audit_action_is_tool_call_ok(self, inquiry_registry, status_token, orchestrator_km):
        _, mock_log, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_audit_params_keys_not_values(self, inquiry_registry, status_token, orchestrator_km):
        _, mock_log, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim-token-001" not in str(details)

    def test_data_from_db_row(self, inquiry_registry, status_token, orchestrator_km):
        result, _, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        inner = result.value.value
        assert inner["claim_stage"] == "PROCESSING"
        assert inner["incident_type"] == "collision"


# ---------------------------------------------------------------------------
# capture_complaint — pure tests
# ---------------------------------------------------------------------------


class TestCaptureComplaintPure:
    def test_returns_labeled_dict(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-001", "service", "Agent was rude.", _CUSTOMER_ID)
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_ifc_label_is_confidential(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-002", "coverage", "Denied unfairly.", _CUSTOMER_ID)
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-003", "decision", "Wrong decision.", _CUSTOMER_ID)
        assert result.label.untrusted is False

    def test_required_keys_present(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-004", "process", "Too slow.", _CUSTOMER_ID)
        assert {"complaint_id", "session_id", "category", "status"} <= result.value.keys()

    def test_session_id_echoed(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-echo-99", "other", "Some complaint.", _CUSTOMER_ID)
        assert result.value["session_id"] == "sess-echo-99"

    def test_status_is_escalated(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-005", "service", "Bad service.", _CUSTOMER_ID)
        assert result.value["status"] == "ESCALATED"

    def test_category_preserved(self):
        for cat in _COMPLAINT_CATEGORIES:
            with _conn_ctx_write():
                result = capture_complaint("sess-cat", cat, "Description.", _CUSTOMER_ID)
            assert result.value["category"] == cat

    def test_unknown_category_coerced_to_other(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-unk", "invalid_category", "Something.", _CUSTOMER_ID)
        assert result.value["category"] == "other"

    def test_complaint_id_is_valid_uuid(self):
        with _conn_ctx_write():
            result = capture_complaint("sess-uuid", "coverage", "My complaint.", _CUSTOMER_ID)
        cid = result.value["complaint_id"]
        parsed = uuid.UUID(cid)
        assert str(parsed) == cid

    def test_deterministic(self):
        """Same inputs → same complaint_id."""
        with _conn_ctx_write():
            a = capture_complaint("sess-det", "process", "Slow process.", _CUSTOMER_ID)
        with _conn_ctx_write():
            b = capture_complaint("sess-det", "process", "Slow process.", _CUSTOMER_ID)
        assert a.value["complaint_id"] == b.value["complaint_id"]

    def test_different_inputs_produce_different_ids(self):
        with _conn_ctx_write():
            a = capture_complaint("sess-diff", "service", "Issue A.", _CUSTOMER_ID)
        with _conn_ctx_write():
            b = capture_complaint("sess-diff", "service", "Issue B.", _CUSTOMER_ID)
        assert a.value["complaint_id"] != b.value["complaint_id"]

    def test_db_insert_called_with_customer_id(self):
        """When customer_id provided, cursor.execute must be called."""
        conn = _make_mock_conn(None)
        token = _conn_var.set(conn)
        try:
            capture_complaint("sess-ins", "service", "Test insert.", _CUSTOMER_ID)
        finally:
            _conn_var.reset(token)
        conn.cursor.return_value.execute.assert_called()

    def test_no_db_insert_without_customer_id(self):
        """When customer_id=None, no DB write occurs (backwards compat)."""
        # No ContextVar set; function skips DB path entirely.
        result = capture_complaint("sess-no-cust", "service", "No cust.", customer_id=None)
        assert result.value["status"] == "ESCALATED"

    def test_no_conn_context_raises_when_customer_id_given(self):
        """With customer_id but no ContextVar → RuntimeError from get_tool_conn()."""
        cv_token = _conn_var.set(None)
        try:
            with pytest.raises(RuntimeError, match="No database connection"):
                capture_complaint("sess-no-ctx", "service", "Test.", _CUSTOMER_ID)
        finally:
            _conn_var.reset(cv_token)


# ---------------------------------------------------------------------------
# capture_complaint — ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def complaint_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("capture_complaint", capture_complaint)
    return r


@pytest.fixture()
def complaint_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="capture_complaint",
        scope={"session_id": "sess-reg-001"},
    )


def _invoke_complaint(registry, token, orchestrator_km, *, params=None):
    if params is None:
        params = {
            "session_id":   "sess-reg-001",
            "category":     "service",
            "description":  "Rude agent.",
            "customer_id":  _CUSTOMER_ID,
        }
    conn = _make_registry_conn_complaint()
    with (
        patch("agent_system.tools.registry.append_log", return_value=11) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="capture_complaint",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


class TestCaptureComplaintRegistry:
    def test_valid_invocation_succeeds(self, complaint_registry, complaint_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_complaint(
            complaint_registry, complaint_token, orchestrator_km
        )
        assert result
        assert result.log_id == 11
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, complaint_registry, complaint_token, orchestrator_km):
        result, _, _ = _invoke_complaint(complaint_registry, complaint_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_status_escalated(self, complaint_registry, complaint_token, orchestrator_km):
        result, _, _ = _invoke_complaint(complaint_registry, complaint_token, orchestrator_km)
        assert result.value.value["status"] == "ESCALATED"

    def test_audit_action_tool_call_ok(self, complaint_registry, complaint_token, orchestrator_km):
        _, mock_log, _ = _invoke_complaint(complaint_registry, complaint_token, orchestrator_km)
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_audit_data_label_confidential(self, complaint_registry, complaint_token, orchestrator_km):
        _, mock_log, _ = _invoke_complaint(complaint_registry, complaint_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"
