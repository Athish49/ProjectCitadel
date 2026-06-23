"""Unit tests for search_fraud_rules tool (Sprint 4.1.5)."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.rag_retrievers import (
    _FRAUD_CORPUS,
    _N_FRAUD_CORPUS,
    search_fraud_rules,
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
class TestSearchFraudRulesPure:
    def test_returns_labeled_dict(self):
        result = search_fraud_rules("claim velocity multiple submissions")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = search_fraud_rules("policy inception proximity new policy")
        b = search_fraud_rules("policy inception proximity new policy")
        assert a.value == b.value

    def test_query_echoed(self):
        q = "staged accident indicators rear-end"
        result = search_fraud_rules(q)
        assert result.value["query"] == q

    def test_value_has_required_keys(self):
        result = search_fraud_rules("ghost vehicle VIN")
        assert {"query", "n_results", "chunks"} <= result.value.keys()

    def test_chunks_is_list(self):
        result = search_fraud_rules("repair shop collusion estimate")
        assert isinstance(result.value["chunks"], list)

    def test_n_results_default_is_three(self):
        result = search_fraud_rules("inflated estimate benchmark")
        assert result.value["n_results"] == 3
        assert len(result.value["chunks"]) == 3

    def test_n_results_respected(self):
        result = search_fraud_rules("evidence anomaly photo timestamp", n_results=2)
        assert result.value["n_results"] == 2
        assert len(result.value["chunks"]) == 2

    def test_n_results_clamped_low(self):
        result = search_fraud_rules("cross claim identity pattern", n_results=0)
        assert result.value["n_results"] == 1
        assert len(result.value["chunks"]) == 1

    def test_n_results_clamped_high(self):
        result = search_fraud_rules("SIU referral threshold", n_results=999)
        assert result.value["n_results"] == _N_FRAUD_CORPUS
        assert len(result.value["chunks"]) == _N_FRAUD_CORPUS

    def test_each_chunk_has_required_keys(self):
        result = search_fraud_rules("claim velocity rule threshold")
        for chunk in result.value["chunks"]:
            assert {"doc_id", "source", "text", "score", "data_label"} <= chunk.keys()

    def test_each_chunk_data_label_is_secret(self):
        result = search_fraud_rules("policy inception proximity risk uplift")
        for chunk in result.value["chunks"]:
            assert chunk["data_label"] == "SECRET"

    def test_score_in_valid_range(self):
        result = search_fraud_rules("evidence anomaly detection")
        for chunk in result.value["chunks"]:
            assert isinstance(chunk["score"], float)
            assert 0.0 < chunk["score"] <= 1.0

    def test_doc_ids_from_corpus(self):
        corpus_ids = {doc["doc_id"] for doc in _FRAUD_CORPUS}
        result = search_fraud_rules("ghost vehicle VIN registration")
        for chunk in result.value["chunks"]:
            assert chunk["doc_id"] in corpus_ids

    def test_no_duplicate_chunks_in_full_result(self):
        result = search_fraud_rules("inflated repair estimate shop", n_results=_N_FRAUD_CORPUS)
        doc_ids = [c["doc_id"] for c in result.value["chunks"]]
        assert len(doc_ids) == len(set(doc_ids))

    def test_ifc_label_is_secret(self):
        result = search_fraud_rules("staged accident collision pattern")
        assert result.label.level == DataLabel.SECRET

    def test_ifc_label_not_untrusted(self):
        result = search_fraud_rules("cross claim identity network")
        assert result.label.untrusted is False

    def test_different_queries_produce_valid_output(self):
        r1 = search_fraud_rules("velocity rule")
        r2 = search_fraud_rules("ghost vehicle")
        for r in (r1, r2):
            assert r.value["n_results"] >= 1
            assert len(r.value["chunks"]) >= 1


# ---------------------------------------------------------------------------
# ToolRegistry integration tests — SECRET label propagation to audit row
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def fraud_rules_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("search_fraud_rules", search_fraud_rules)
    return r


@pytest.fixture()
def fraud_rules_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="search_fraud_rules",
        scope={"query": "claim velocity SIU referral"},
    )


def _invoke_fraud_rules(registry, token, orchestrator_km, *, params=None):
    if params is None:
        params = {"query": "claim velocity SIU referral"}
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
            tool_name="search_fraud_rules",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log


@pytest.mark.unit
class TestSearchFraudRulesRegistry:
    def test_invocation_succeeds(self, fraud_rules_registry, fraud_rules_token, orchestrator_km):
        result, _ = _invoke_fraud_rules(fraud_rules_registry, fraud_rules_token, orchestrator_km)
        assert result

    def test_audit_row_data_label_is_secret(
        self, fraud_rules_registry, fraud_rules_token, orchestrator_km
    ):
        """Registry must record SECRET in the audit row (dynamic-label fix, task 4.1.3)."""
        _, mock_log = _invoke_fraud_rules(
            fraud_rules_registry, fraud_rules_token, orchestrator_km
        )
        assert mock_log.call_args.kwargs["data_label"] == "SECRET"

    def test_result_value_is_labeled(
        self, fraud_rules_registry, fraud_rules_token, orchestrator_km
    ):
        result, _ = _invoke_fraud_rules(fraud_rules_registry, fraud_rules_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_label_is_secret(
        self, fraud_rules_registry, fraud_rules_token, orchestrator_km
    ):
        result, _ = _invoke_fraud_rules(fraud_rules_registry, fraud_rules_token, orchestrator_km)
        assert result.value.label.level == DataLabel.SECRET

    def test_n_results_extra_param_allowed(self, fraud_rules_registry, orchestrator_km):
        """n_results is not in scope — registry must still allow it as extra param."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="search_fraud_rules",
            scope={"query": "policy inception proximity"},
        )
        result, _ = _invoke_fraud_rules(
            fraud_rules_registry,
            token,
            orchestrator_km,
            params={"query": "policy inception proximity", "n_results": 2},
        )
        assert result
        assert result.value.value["n_results"] == 2
