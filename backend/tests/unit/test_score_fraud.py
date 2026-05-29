"""Unit tests for score_fraud tool and the registry dynamic-label fix (Sprint 4.1.3)."""
from __future__ import annotations

import uuid
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
class TestScoreFraudPure:
    def test_returns_labeled_dict(self):
        result = score_fraud("CLM-001")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = score_fraud("CLM-determinism")
        b = score_fraud("CLM-determinism")
        assert a.value == b.value

    def test_claim_id_echoed(self):
        result = score_fraud("CLM-echo")
        assert result.value["claim_id"] == "CLM-echo"

    def test_value_has_required_keys(self):
        result = score_fraud("CLM-keys")
        assert {"claim_id", "risk_score", "risk_factors", "decision"} <= result.value.keys()

    def test_risk_score_in_range(self):
        result = score_fraud("CLM-score-range")
        assert 0 <= result.value["risk_score"] <= 100

    def test_risk_score_is_integer(self):
        result = score_fraud("CLM-score-int")
        assert isinstance(result.value["risk_score"], int)

    def test_risk_factors_is_list(self):
        result = score_fraud("CLM-factors-type")
        assert isinstance(result.value["risk_factors"], list)

    def test_risk_factors_non_empty(self):
        result = score_fraud("CLM-factors-nonempty")
        assert len(result.value["risk_factors"]) >= 1

    def test_risk_factors_no_duplicates(self):
        for i in range(50):
            factors = score_fraud(f"CLM-dedup-{i:03d}").value["risk_factors"]
            assert len(factors) == len(set(factors)), f"duplicates in {factors}"

    def test_decision_valid(self):
        result = score_fraud("CLM-decision")
        assert result.value["decision"] in {"CLEAR", "FLAG", "DENY"}

    def test_clear_threshold(self):
        """score < 30 → CLEAR; find a claim that hits CLEAR."""
        clears = [score_fraud(f"CLM-thresh-{i:04d}") for i in range(200)
                  if score_fraud(f"CLM-thresh-{i:04d}").value["decision"] == "CLEAR"]
        assert clears, "no CLEAR result found in 200 probes"
        for r in clears:
            assert r.value["risk_score"] < 30

    def test_flag_threshold(self):
        flags = [score_fraud(f"CLM-flag-{i:04d}") for i in range(200)
                 if score_fraud(f"CLM-flag-{i:04d}").value["decision"] == "FLAG"]
        assert flags, "no FLAG result found in 200 probes"
        for r in flags:
            assert 30 <= r.value["risk_score"] < 60

    def test_deny_threshold(self):
        denies = [score_fraud(f"CLM-deny-{i:04d}") for i in range(200)
                  if score_fraud(f"CLM-deny-{i:04d}").value["decision"] == "DENY"]
        assert denies, "no DENY result found in 200 probes"
        for r in denies:
            assert r.value["risk_score"] >= 60

    def test_all_three_decisions_reachable(self):
        decisions = {score_fraud(f"CLM-all-{i:04d}").value["decision"] for i in range(200)}
        assert decisions == {"CLEAR", "FLAG", "DENY"}

    def test_clear_factors_from_catalogue(self):
        for i in range(200):
            r = score_fraud(f"CLM-cfact-{i:04d}")
            if r.value["decision"] == "CLEAR":
                for f in r.value["risk_factors"]:
                    assert f in _FACTORS_CLEAR
                break

    def test_flag_factors_from_catalogue(self):
        for i in range(200):
            r = score_fraud(f"CLM-ffact-{i:04d}")
            if r.value["decision"] == "FLAG":
                for f in r.value["risk_factors"]:
                    assert f in _FACTORS_FLAG
                break

    def test_deny_factors_from_catalogue(self):
        for i in range(200):
            r = score_fraud(f"CLM-dfact-{i:04d}")
            if r.value["decision"] == "DENY":
                for f in r.value["risk_factors"]:
                    assert f in _FACTORS_DENY
                break

    def test_deny_has_at_least_two_factors(self):
        for i in range(200):
            r = score_fraud(f"CLM-dmin-{i:04d}")
            if r.value["decision"] == "DENY":
                assert len(r.value["risk_factors"]) >= 2
                break

    def test_ifc_label_is_secret(self):
        result = score_fraud("CLM-label")
        assert result.label.level == DataLabel.SECRET

    def test_ifc_label_not_untrusted(self):
        result = score_fraud("CLM-untrusted")
        assert result.label.untrusted is False


# ---------------------------------------------------------------------------
# ToolRegistry integration tests — SECRET label propagation to audit row
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


def _invoke_fraud(registry, token, orchestrator_km, *, params=None):
    if params is None:
        params = {"claim_id": "CLM-token-001"}
    conn = _make_conn()
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
        """Registry must record SECRET in the audit row, not hardcoded CONFIDENTIAL."""
        _, mock_log = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "SECRET"

    def test_result_value_is_labeled(self, fraud_registry, fraud_token, orchestrator_km):
        result, _ = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_label_is_secret(self, fraud_registry, fraud_token, orchestrator_km):
        result, _ = _invoke_fraud(fraud_registry, fraud_token, orchestrator_km)
        assert result.value.label.level == DataLabel.SECRET


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
        conn = _make_conn()
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
