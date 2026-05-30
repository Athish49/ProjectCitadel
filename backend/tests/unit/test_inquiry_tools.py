"""Unit tests for inquiry tools (Sprint 4.1.8–4.1.9).

Tests cover:
  - lookup_claim_status: pure function and ToolRegistry integration
  - capture_complaint: pure function and ToolRegistry integration
"""
from __future__ import annotations

import uuid
from datetime import date
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

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(used_at=None, row_exists=True):
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = (used_at,) if row_exists else None
    conn.cursor.return_value = cur
    return conn


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestLookupClaimStatusPure:
    def test_returns_labeled_dict(self):
        result = lookup_claim_status("claim-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_ifc_label_is_confidential(self):
        result = lookup_claim_status("claim-label-check")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = lookup_claim_status("claim-untrusted-check")
        assert result.label.untrusted is False

    def test_required_keys_present(self):
        result = lookup_claim_status("claim-keys")
        expected = {"claim_id", "claim_number", "claim_stage", "incident_type",
                    "incident_date", "total_claim_amount"}
        assert expected <= result.value.keys()

    def test_claim_id_echoed(self):
        cid = "claim-echo-abc123"
        result = lookup_claim_status(cid)
        assert result.value["claim_id"] == cid

    def test_claim_number_format(self):
        result = lookup_claim_status("claim-number-fmt")
        cn = result.value["claim_number"]
        assert cn.startswith("CLM-")
        assert len(cn) == 12  # "CLM-" + 8 digits

    def test_claim_stage_is_valid(self):
        result = lookup_claim_status("claim-stage-valid")
        assert result.value["claim_stage"] in _CLAIM_STAGES

    def test_incident_type_is_valid(self):
        result = lookup_claim_status("claim-incident-valid")
        assert result.value["incident_type"] in _INCIDENT_TYPES

    def test_incident_date_is_iso8601(self):
        result = lookup_claim_status("claim-date-iso")
        d = date.fromisoformat(result.value["incident_date"])
        assert 2024 <= d.year <= 2025

    def test_total_claim_amount_in_range(self):
        result = lookup_claim_status("claim-amount-range")
        amt = result.value["total_claim_amount"]
        assert 500.0 <= amt <= 50_000.0

    def test_deterministic(self):
        a = lookup_claim_status("claim-determinism")
        b = lookup_claim_status("claim-determinism")
        assert a.value == b.value

    def test_different_ids_may_differ(self):
        stages = {lookup_claim_status(f"claim-diff-{i}").value["claim_stage"] for i in range(20)}
        assert len(stages) > 1

    def test_all_stages_reachable(self):
        seen: set[str] = set()
        for i in range(500):
            seen.add(lookup_claim_status(f"probe-stage-{i:04d}").value["claim_stage"])
            if len(seen) == len(_CLAIM_STAGES):
                break
        assert seen == set(_CLAIM_STAGES), f"Missing stages: {set(_CLAIM_STAGES) - seen}"

    def test_all_incident_types_reachable(self):
        seen: set[str] = set()
        for i in range(200):
            seen.add(lookup_claim_status(f"probe-incident-{i:04d}").value["incident_type"])
            if len(seen) == len(_INCIDENT_TYPES):
                break
        assert seen == set(_INCIDENT_TYPES), f"Missing types: {set(_INCIDENT_TYPES) - seen}"


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
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


def _invoke_status(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {"claim_id": "claim-token-001"}
    conn = _make_conn(used_at=used_at, row_exists=row_exists)
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
        result, mock_log, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_audit_params_keys_not_values(self, inquiry_registry, status_token, orchestrator_km):
        result, mock_log, _ = _invoke_status(inquiry_registry, status_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim-token-001" not in str(details)


# ---------------------------------------------------------------------------
# capture_complaint — pure function tests
# ---------------------------------------------------------------------------


class TestCaptureComplaintPure:
    def test_returns_labeled_dict(self):
        result = capture_complaint("sess-001", "service", "Agent was rude.")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_ifc_label_is_confidential(self):
        result = capture_complaint("sess-002", "coverage", "Claim was denied unfairly.")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = capture_complaint("sess-003", "decision", "Wrong decision made.")
        assert result.label.untrusted is False

    def test_required_keys_present(self):
        result = capture_complaint("sess-004", "process", "Process took too long.")
        assert {"complaint_id", "session_id", "category", "status"} <= result.value.keys()

    def test_session_id_echoed(self):
        result = capture_complaint("sess-echo-99", "other", "Some complaint.")
        assert result.value["session_id"] == "sess-echo-99"

    def test_status_is_escalated(self):
        result = capture_complaint("sess-005", "service", "Bad service.")
        assert result.value["status"] == "ESCALATED"

    def test_category_preserved(self):
        for cat in _COMPLAINT_CATEGORIES:
            result = capture_complaint("sess-cat", cat, "Description.")
            assert result.value["category"] == cat

    def test_unknown_category_coerced_to_other(self):
        result = capture_complaint("sess-unk", "invalid_category", "Something.")
        assert result.value["category"] == "other"

    def test_complaint_id_is_valid_uuid(self):
        result = capture_complaint("sess-uuid", "coverage", "My complaint.")
        cid = result.value["complaint_id"]
        parsed = uuid.UUID(cid)
        assert str(parsed) == cid

    def test_deterministic(self):
        a = capture_complaint("sess-det", "process", "Slow process.")
        b = capture_complaint("sess-det", "process", "Slow process.")
        assert a.value == b.value

    def test_different_inputs_produce_different_ids(self):
        a = capture_complaint("sess-diff", "service", "Issue A.")
        b = capture_complaint("sess-diff", "service", "Issue B.")
        assert a.value["complaint_id"] != b.value["complaint_id"]


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


def _invoke_complaint(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {"session_id": "sess-reg-001", "category": "service", "description": "Rude agent."}
    conn = _make_conn(used_at=used_at, row_exists=row_exists)
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
        result, mock_log, _ = _invoke_complaint(complaint_registry, complaint_token, orchestrator_km)
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"
