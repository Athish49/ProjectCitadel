"""Unit tests for draft_summary tool (Sprint 4.2.3)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.settlement_tools import (
    _SUMMARY_TEMPLATES,
    draft_summary,
)
from agent_system.tools.registry import ToolRegistry


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


@pytest.mark.unit
class TestDraftSummaryPure:
    def test_returns_labeled_dict(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref-abc")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = draft_summary("CLM-001", "SETTLED", 7000.0, "ref-abc")
        b = draft_summary("CLM-001", "SETTLED", 7000.0, "ref-abc")
        assert a.value == b.value

    def test_claim_id_echoed(self):
        result = draft_summary("CLM-echo", "ESCALATED", 0.0, "")
        assert result.value["claim_id"] == "CLM-echo"

    def test_outcome_echoed(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref")
        assert result.value["outcome"] == "SETTLED"

    def test_offered_amount_echoed(self):
        result = draft_summary("CLM-001", "SETTLED", 1234.56, "ref")
        assert result.value["offered_amount"] == 1234.56

    def test_payout_reference_echoed(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref-xyz")
        assert result.value["payout_reference"] == "ref-xyz"

    def test_value_has_required_keys(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref")
        assert {
            "claim_id",
            "outcome",
            "offered_amount",
            "payout_reference",
            "summary",
        } <= result.value.keys()

    def test_ifc_label_is_confidential(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref")
        assert result.label.untrusted is False

    def test_settled_summary_contains_amount(self):
        result = draft_summary("CLM-001", "SETTLED", 7_000.0, "ref-abc")
        assert "7,000.00" in result.value["summary"]

    def test_settled_summary_contains_payout_reference(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "ref-unique-123")
        assert "ref-unique-123" in result.value["summary"]

    def test_settled_summary_contains_claim_id(self):
        result = draft_summary("CLM-999", "SETTLED", 7000.0, "ref")
        assert "CLM-999" in result.value["summary"]

    def test_escalated_summary_contains_claim_id(self):
        result = draft_summary("CLM-777", "ESCALATED", 0.0, "")
        assert "CLM-777" in result.value["summary"]

    def test_escalated_summary_no_payment_text(self):
        result = draft_summary("CLM-001", "ESCALATED", 0.0, "")
        assert "payment" not in result.value["summary"].lower()
        assert "approved" not in result.value["summary"].lower()

    def test_unknown_outcome_uses_escalated_template(self):
        result = draft_summary("CLM-001", "UNKNOWN_STATUS", 0.0, "")
        escalated_result = draft_summary("CLM-001", "ESCALATED", 0.0, "")
        assert result.value["summary"] == escalated_result.value["summary"]

    def test_empty_payout_reference_replaced_with_na(self):
        result = draft_summary("CLM-001", "SETTLED", 7000.0, "")
        assert "N/A" in result.value["summary"]

    def test_settled_template_is_in_templates(self):
        assert "SETTLED" in _SUMMARY_TEMPLATES
        assert "ESCALATED" in _SUMMARY_TEMPLATES

    def test_offered_amount_zero_for_escalated_non_breaking(self):
        result = draft_summary("CLM-001", "ESCALATED", 0.0, "")
        assert isinstance(result.value["summary"], str)
        assert len(result.value["summary"]) > 0

    def test_large_offered_amount_formatted(self):
        result = draft_summary("CLM-001", "SETTLED", 22_000.0, "ref")
        assert "22,000.00" in result.value["summary"]


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def summary_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("draft_summary", draft_summary)
    return r


@pytest.fixture()
def summary_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="settlement_actor",
        tool="draft_summary",
        scope={"claim_id": "CLM-token-001"},
    )


def _invoke_summary(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {
            "claim_id":          "CLM-token-001",
            "outcome":           "ESCALATED",
            "offered_amount":    0.0,
            "payout_reference":  "",
        }
    conn = _make_conn(used_at=used_at, row_exists=row_exists)
    with (
        patch("agent_system.tools.registry.append_log", return_value=55) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="draft_summary",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


@pytest.mark.unit
class TestDraftSummaryRegistry:
    def test_valid_invocation_succeeds(self, summary_registry, summary_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_summary(
            summary_registry, summary_token, orchestrator_km
        )
        assert result
        assert result.log_id == 55
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, summary_registry, summary_token, orchestrator_km):
        result, _, _ = _invoke_summary(summary_registry, summary_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_inner_dict_keys(self, summary_registry, summary_token, orchestrator_km):
        result, _, _ = _invoke_summary(summary_registry, summary_token, orchestrator_km)
        inner = result.value.value
        assert {
            "claim_id",
            "outcome",
            "offered_amount",
            "payout_reference",
            "summary",
        } <= inner.keys()

    def test_result_ifc_label_confidential(self, summary_registry, summary_token, orchestrator_km):
        result, _, _ = _invoke_summary(summary_registry, summary_token, orchestrator_km)
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_audit_label_is_confidential(self, summary_registry, summary_token, orchestrator_km):
        result, mock_log, _ = _invoke_summary(summary_registry, summary_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"

    def test_audit_params_keys_not_values(self, summary_registry, summary_token, orchestrator_km):
        result, mock_log, _ = _invoke_summary(summary_registry, summary_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim_id" not in details

    def test_replay_denied(self, summary_registry, summary_token, orchestrator_km):
        result, _, _ = _invoke_summary(
            summary_registry, summary_token, orchestrator_km, used_at="2026-01-01T00:00:00"
        )
        assert not result
        assert result.deny_reason is not None

    def test_unissued_token_denied_security_event(self, summary_registry, summary_token, orchestrator_km):
        result, mock_log, _ = _invoke_summary(
            summary_registry, summary_token, orchestrator_km, row_exists=False
        )
        assert not result
        assert mock_log.call_args.kwargs["security_event"] is True

    def test_settled_path_params_accepted(self, summary_registry, summary_token, orchestrator_km):
        result, _, _ = _invoke_summary(
            summary_registry,
            summary_token,
            orchestrator_km,
            params={
                "claim_id":         "CLM-token-001",
                "outcome":          "SETTLED",
                "offered_amount":   7000.0,
                "payout_reference": "ref-abc-123",
            },
        )
        assert result
        inner = result.value.value
        assert inner["outcome"] == "SETTLED"
        assert "7,000.00" in inner["summary"]
