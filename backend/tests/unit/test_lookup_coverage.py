"""Unit tests for lookup_coverage tool (Sprint 4.1.2)."""
from __future__ import annotations

import uuid
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
class TestLookupCoveragePure:
    def test_returns_labeled_dict(self):
        result = lookup_coverage("CLM-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = lookup_coverage("CLM-determinism")
        b = lookup_coverage("CLM-determinism")
        assert a.value == b.value

    def test_claim_id_echoed(self):
        result = lookup_coverage("CLM-echo-test")
        assert result.value["claim_id"] == "CLM-echo-test"

    def test_value_has_required_keys(self):
        result = lookup_coverage("CLM-keys")
        assert {
            "claim_id", "policy_type", "coverage_type",
            "deductible", "auto_approve_limit", "policy_status",
            "coverage_applicable",
        } <= result.value.keys()

    def test_policy_type_valid(self):
        result = lookup_coverage("CLM-ptype")
        assert result.value["policy_type"] in _POLICY_TYPES

    def test_coverage_type_valid(self):
        result = lookup_coverage("CLM-ctype")
        assert result.value["coverage_type"] in _COVERAGE_TYPES

    def test_deductible_valid(self):
        result = lookup_coverage("CLM-deductible")
        assert result.value["deductible"] in DEDUCTIBLES

    def test_auto_approve_limit_valid(self):
        result = lookup_coverage("CLM-approve")
        assert result.value["auto_approve_limit"] in AUTO_APPROVE_LIMITS

    def test_policy_status_active(self):
        result = lookup_coverage("CLM-status")
        assert result.value["policy_status"] == "ACTIVE"

    def test_coverage_applicable_is_bool(self):
        result = lookup_coverage("CLM-applicable")
        assert isinstance(result.value["coverage_applicable"], bool)

    def test_all_policy_types_reachable(self):
        seen: set[str] = set()
        for i in range(200):
            seen.add(lookup_coverage(f"probe-ptype-{i:04d}").value["policy_type"])
            if len(seen) == len(_POLICY_TYPES):
                break
        assert seen == set(_POLICY_TYPES)

    def test_all_coverage_types_reachable(self):
        seen: set[str] = set()
        for i in range(200):
            seen.add(lookup_coverage(f"probe-ctype-{i:04d}").value["coverage_type"])
            if len(seen) == len(_COVERAGE_TYPES):
                break
        assert seen == set(_COVERAGE_TYPES)

    def test_both_coverage_applicable_values_reachable(self):
        results = {lookup_coverage(f"probe-app-{i:04d}").value["coverage_applicable"] for i in range(50)}
        assert results == {True, False}

    def test_ifc_label_is_confidential(self):
        result = lookup_coverage("CLM-label")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = lookup_coverage("CLM-untrusted")
        assert result.label.untrusted is False

    def test_different_claim_ids_produce_variety(self):
        policy_types = {lookup_coverage(f"CLM-var-{i}").value["policy_type"] for i in range(20)}
        assert len(policy_types) > 1


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


def _invoke_coverage(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {"claim_id": "CLM-token-001"}
    conn = _make_conn(used_at=used_at, row_exists=row_exists)
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

    def test_audit_params_keys_not_values(self, coverage_registry, coverage_token, orchestrator_km):
        result, mock_log, _ = _invoke_coverage(coverage_registry, coverage_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim_id" not in details
