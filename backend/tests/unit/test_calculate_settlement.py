"""Unit tests for calculate_settlement tool (Sprint 4.2.1)."""
from __future__ import annotations

import hashlib
import uuid
from unittest.mock import MagicMock, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.claims_tools import (
    AUTO_APPROVE_LIMITS,
    DEDUCTIBLES,
    lookup_coverage,
)
from agent_system.tools.implementations.settlement_tools import (
    _CLAIM_AMOUNTS,
    calculate_settlement,
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
class TestCalculateSettlementPure:
    def test_returns_labeled_dict(self):
        result = calculate_settlement("CLM-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = calculate_settlement("CLM-determinism")
        b = calculate_settlement("CLM-determinism")
        assert a.value == b.value

    def test_claim_id_echoed(self):
        result = calculate_settlement("CLM-echo-test")
        assert result.value["claim_id"] == "CLM-echo-test"

    def test_value_has_required_keys(self):
        result = calculate_settlement("CLM-keys")
        assert {
            "claim_id",
            "raw_claim_amount",
            "deductible_applied",
            "offered_amount",
            "auto_approve_limit",
        } <= result.value.keys()

    def test_ifc_label_is_confidential(self):
        result = calculate_settlement("CLM-label")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = calculate_settlement("CLM-untrusted")
        assert result.label.untrusted is False

    def test_raw_claim_amount_in_catalogue(self):
        result = calculate_settlement("CLM-raw")
        assert result.value["raw_claim_amount"] in _CLAIM_AMOUNTS

    def test_deductible_in_catalogue(self):
        result = calculate_settlement("CLM-deductible")
        assert result.value["deductible_applied"] in [float(d) for d in DEDUCTIBLES]

    def test_auto_approve_limit_in_catalogue(self):
        result = calculate_settlement("CLM-limit")
        assert result.value["auto_approve_limit"] in [float(lim) for lim in AUTO_APPROVE_LIMITS]

    def test_offered_amount_non_negative(self):
        for i in range(100):
            result = calculate_settlement(f"CLM-nonneg-{i:04d}")
            assert result.value["offered_amount"] >= 0.0

    def test_offered_amount_equals_raw_minus_deductible(self):
        for i in range(50):
            result = calculate_settlement(f"CLM-math-{i:04d}")
            v = result.value
            expected = max(0.0, v["raw_claim_amount"] - v["deductible_applied"])
            assert v["offered_amount"] == expected

    def test_different_claim_ids_produce_variety(self):
        amounts = {calculate_settlement(f"CLM-var-{i}").value["raw_claim_amount"] for i in range(30)}
        assert len(amounts) > 1

    def test_all_claim_amounts_reachable(self):
        seen: set[float] = set()
        for i in range(500):
            seen.add(calculate_settlement(f"probe-amt-{i:04d}").value["raw_claim_amount"])
            if len(seen) == len(_CLAIM_AMOUNTS):
                break
        assert seen == set(_CLAIM_AMOUNTS)

    def test_all_deductibles_reachable(self):
        seen: set[float] = set()
        target = {float(d) for d in DEDUCTIBLES}
        for i in range(500):
            seen.add(calculate_settlement(f"probe-ded-{i:04d}").value["deductible_applied"])
            if seen == target:
                break
        assert seen == target

    def test_all_auto_approve_limits_reachable(self):
        seen: set[float] = set()
        target = {float(lim) for lim in AUTO_APPROVE_LIMITS}
        for i in range(500):
            seen.add(calculate_settlement(f"probe-lim-{i:04d}").value["auto_approve_limit"])
            if seen == target:
                break
        assert seen == target


# ---------------------------------------------------------------------------
# Path coverage: SETTLED vs ESCALATED
#
# DECIDED → SETTLED guard: offered_amount <= auto_approve_limit
# DECIDED → ESCALATED guard: offered_amount > auto_approve_limit
# Both paths must be reachable from the tool's output space.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateSettlementPathCoverage:
    def test_both_paths_reachable(self):
        """Sweep CLM-001…CLM-100; confirm both under-limit and over-limit claims exist."""
        under_limit = False
        over_limit = False
        for i in range(1, 101):
            result = calculate_settlement(f"CLM-{i:03d}")
            v = result.value
            if v["offered_amount"] <= v["auto_approve_limit"]:
                under_limit = True
            else:
                over_limit = True
            if under_limit and over_limit:
                break
        assert under_limit, "No claim found where offered_amount <= auto_approve_limit (SETTLED path)"
        assert over_limit, "No claim found where offered_amount > auto_approve_limit (ESCALATED path)"

    def test_settled_path_example(self):
        """At least one claim in CLM-001…CLM-100 satisfies the SETTLED guard."""
        settled = [
            f"CLM-{i:03d}"
            for i in range(1, 101)
            if (lambda v: v["offered_amount"] <= v["auto_approve_limit"])(
                calculate_settlement(f"CLM-{i:03d}").value
            )
        ]
        assert len(settled) > 0

    def test_escalated_path_example(self):
        """At least one claim in CLM-001…CLM-100 satisfies the ESCALATED guard."""
        escalated = [
            f"CLM-{i:03d}"
            for i in range(1, 101)
            if (lambda v: v["offered_amount"] > v["auto_approve_limit"])(
                calculate_settlement(f"CLM-{i:03d}").value
            )
        ]
        assert len(escalated) > 0


# ---------------------------------------------------------------------------
# Cross-tool consistency with lookup_coverage
#
# Both tools derive deductible and auto_approve_limit from the same hash
# bit ranges (h >> 16 and h >> 24 respectively).  They must agree.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateSettlementCrossToolConsistency:
    def test_deductible_matches_lookup_coverage(self):
        for i in range(1, 51):
            cid = f"CLM-{i:03d}"
            settlement = calculate_settlement(cid).value
            coverage = lookup_coverage(cid).value
            assert settlement["deductible_applied"] == float(coverage["deductible"]), (
                f"Deductible mismatch for {cid}: "
                f"settlement={settlement['deductible_applied']}, "
                f"coverage={coverage['deductible']}"
            )

    def test_auto_approve_limit_matches_lookup_coverage(self):
        for i in range(1, 51):
            cid = f"CLM-{i:03d}"
            settlement = calculate_settlement(cid).value
            coverage = lookup_coverage(cid).value
            assert settlement["auto_approve_limit"] == float(coverage["auto_approve_limit"]), (
                f"auto_approve_limit mismatch for {cid}: "
                f"settlement={settlement['auto_approve_limit']}, "
                f"coverage={coverage['auto_approve_limit']}"
            )


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def settlement_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("calculate_settlement", calculate_settlement)
    return r


@pytest.fixture()
def settlement_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="settlement_actor",
        tool="calculate_settlement",
        scope={"claim_id": "CLM-token-001"},
    )


def _invoke_settlement(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {"claim_id": "CLM-token-001"}
    conn = _make_conn(used_at=used_at, row_exists=row_exists)
    with (
        patch("agent_system.tools.registry.append_log", return_value=99) as mock_log,
        patch("agent_system.tools.registry.record_use") as mock_record,
        patch("agent_system.tools.registry._try_record_use"),
    ):
        result = registry.invoke(
            conn,
            token=token,
            calling_agent_id=token.agent_id,
            tool_name="calculate_settlement",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


@pytest.mark.unit
class TestCalculateSettlementRegistry:
    def test_valid_invocation_succeeds(self, settlement_registry, settlement_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_settlement(
            settlement_registry, settlement_token, orchestrator_km
        )
        assert result
        assert result.log_id == 99
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, settlement_registry, settlement_token, orchestrator_km):
        result, _, _ = _invoke_settlement(settlement_registry, settlement_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_inner_dict_keys(self, settlement_registry, settlement_token, orchestrator_km):
        result, _, _ = _invoke_settlement(settlement_registry, settlement_token, orchestrator_km)
        inner = result.value.value
        assert {
            "claim_id",
            "raw_claim_amount",
            "deductible_applied",
            "offered_amount",
            "auto_approve_limit",
        } <= inner.keys()

    def test_result_ifc_label_confidential(self, settlement_registry, settlement_token, orchestrator_km):
        result, _, _ = _invoke_settlement(settlement_registry, settlement_token, orchestrator_km)
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_audit_label_is_confidential(self, settlement_registry, settlement_token, orchestrator_km):
        result, mock_log, _ = _invoke_settlement(settlement_registry, settlement_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"

    def test_audit_params_keys_not_values(self, settlement_registry, settlement_token, orchestrator_km):
        result, mock_log, _ = _invoke_settlement(settlement_registry, settlement_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "claim_id" not in details

    def test_replay_denied(self, settlement_registry, settlement_token, orchestrator_km):
        result, _, _ = _invoke_settlement(
            settlement_registry, settlement_token, orchestrator_km, used_at="2026-01-01T00:00:00"
        )
        assert not result
        assert result.deny_reason is not None

    def test_unissued_token_denied_security_event(self, settlement_registry, settlement_token, orchestrator_km):
        result, mock_log, _ = _invoke_settlement(
            settlement_registry, settlement_token, orchestrator_km, row_exists=False
        )
        assert not result
        assert mock_log.call_args.kwargs["security_event"] is True
