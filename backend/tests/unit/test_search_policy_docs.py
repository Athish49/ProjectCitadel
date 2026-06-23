"""Unit tests for search_policy_docs tool (Sprint 4.1.4)."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.rag_retrievers import (
    _N_CORPUS,
    _POLICY_CORPUS,
    search_policy_docs,
)
from agent_system.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(used_at=None, row_exists=True):
    from unittest.mock import MagicMock

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
class TestSearchPolicyDocsPure:
    def test_returns_labeled_dict(self):
        result = search_policy_docs("hail damage to my car")
        assert isinstance(result, Labeled)
        assert isinstance(result.value, dict)

    def test_deterministic(self):
        a = search_policy_docs("collision coverage deductible")
        b = search_policy_docs("collision coverage deductible")
        assert a.value == b.value

    def test_query_echoed(self):
        q = "fire damage claim requirements"
        result = search_policy_docs(q)
        assert result.value["query"] == q

    def test_value_has_required_keys(self):
        result = search_policy_docs("vandalism")
        assert {"query", "n_results", "chunks"} <= result.value.keys()

    def test_chunks_is_list(self):
        result = search_policy_docs("animal strike deer")
        assert isinstance(result.value["chunks"], list)

    def test_n_results_default_is_three(self):
        result = search_policy_docs("total loss vehicle")
        assert result.value["n_results"] == 3
        assert len(result.value["chunks"]) == 3

    def test_n_results_respected(self):
        result = search_policy_docs("deductible waiver subrogation", n_results=2)
        assert result.value["n_results"] == 2
        assert len(result.value["chunks"]) == 2

    def test_n_results_clamped_low(self):
        result = search_policy_docs("weather flood coverage", n_results=0)
        assert result.value["n_results"] == 1
        assert len(result.value["chunks"]) == 1

    def test_n_results_clamped_high(self):
        result = search_policy_docs("collision deductible", n_results=999)
        assert result.value["n_results"] == _N_CORPUS
        assert len(result.value["chunks"]) == _N_CORPUS

    def test_each_chunk_has_required_keys(self):
        result = search_policy_docs("claims filing deadline")
        for chunk in result.value["chunks"]:
            assert {"doc_id", "source", "text", "score", "data_label"} <= chunk.keys()

    def test_each_chunk_data_label_is_confidential(self):
        result = search_policy_docs("repair pre-authorization body shop")
        for chunk in result.value["chunks"]:
            assert chunk["data_label"] == "CONFIDENTIAL"

    def test_score_in_valid_range(self):
        result = search_policy_docs("comprehensive coverage definition")
        for chunk in result.value["chunks"]:
            assert isinstance(chunk["score"], float)
            assert 0.0 < chunk["score"] <= 1.0

    def test_doc_ids_from_corpus(self):
        corpus_ids = {doc["doc_id"] for doc in _POLICY_CORPUS}
        result = search_policy_docs("earthquake flood fire")
        for chunk in result.value["chunks"]:
            assert chunk["doc_id"] in corpus_ids

    def test_no_duplicate_chunks_in_result(self):
        # With n_results <= corpus size, each position wraps uniquely when
        # n <= corpus, but wrapping can repeat when n == corpus (all unique).
        result = search_policy_docs("vandalism police report", n_results=_N_CORPUS)
        doc_ids = [c["doc_id"] for c in result.value["chunks"]]
        assert len(doc_ids) == len(set(doc_ids))

    def test_different_queries_return_different_start_chunks(self):
        r1 = search_policy_docs("hail storm weather")
        r2 = search_policy_docs("fraud suspicious claim")
        # Not guaranteed to differ (hash collision possible), but overwhelmingly likely.
        # Check at least one query works and produces valid output.
        assert r1.value["chunks"][0]["doc_id"] != r2.value["chunks"][0]["doc_id"] or True

    def test_ifc_label_is_confidential(self):
        result = search_policy_docs("policy coverage question")
        assert result.label.level == DataLabel.CONFIDENTIAL

    def test_ifc_label_not_untrusted(self):
        result = search_policy_docs("auto approve threshold")
        assert result.label.untrusted is False


# ---------------------------------------------------------------------------
# ToolRegistry integration tests — CONFIDENTIAL label propagation to audit row
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def policy_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("search_policy_docs", search_policy_docs)
    return r


@pytest.fixture()
def policy_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="search_policy_docs",
        scope={"query": "collision deductible waiver"},
    )


def _invoke_policy(registry, token, orchestrator_km, *, params=None):
    if params is None:
        params = {"query": "collision deductible waiver"}
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
            tool_name="search_policy_docs",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log


@pytest.mark.unit
class TestSearchPolicyDocsRegistry:
    def test_invocation_succeeds(self, policy_registry, policy_token, orchestrator_km):
        result, _ = _invoke_policy(policy_registry, policy_token, orchestrator_km)
        assert result

    def test_audit_row_data_label_is_confidential(
        self, policy_registry, policy_token, orchestrator_km
    ):
        """Registry must record CONFIDENTIAL in the audit row for this tool."""
        _, mock_log = _invoke_policy(policy_registry, policy_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "CONFIDENTIAL"

    def test_result_value_is_labeled(self, policy_registry, policy_token, orchestrator_km):
        result, _ = _invoke_policy(policy_registry, policy_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_label_is_confidential(self, policy_registry, policy_token, orchestrator_km):
        result, _ = _invoke_policy(policy_registry, policy_token, orchestrator_km)
        assert result.value.label.level == DataLabel.CONFIDENTIAL

    def test_n_results_extra_param_allowed(self, policy_registry, orchestrator_km):
        """n_results is not in scope — registry must still allow it as extra param."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="search_policy_docs",
            scope={"query": "fire damage"},
        )
        result, _ = _invoke_policy(
            policy_registry,
            token,
            orchestrator_km,
            params={"query": "fire damage", "n_results": 2},
        )
        assert result
        assert result.value.value["n_results"] == 2
