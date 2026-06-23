"""Unit tests for search_public_faq tool (Sprint 4.2.2).

No ContextVar injection needed — RAG retriever, not a DB-backed tool.
Tests verify:
  - Labeled[dict] return type with PUBLIC IFC label
  - Required output keys and chunk structure
  - Stub corpus coverage (all 10 docs reachable)
  - ToolRegistry integration: audit row carries data_label="PUBLIC"
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.ifc.labels import DataLabel, Labeled
from agent_system.tools.capability_tokens import issue_token
from agent_system.tools.implementations.rag_retrievers import (
    _FAQ_CORPUS,
    _N_FAQ_CORPUS,
    search_public_faq,
)
from agent_system.tools.registry import ToolRegistry

pytestmark = pytest.mark.unit


# Force stub path for all tests in this file: the live FAQ collection is not
# accessible with the current scoped JWT (see db/ingest.py NOTE).
@pytest.fixture(autouse=True)
def _force_stub(monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestSearchPublicFaqPure:
    def test_returns_labeled(self):
        result = search_public_faq("How do I file a claim?")
        assert isinstance(result, Labeled)

    def test_value_is_dict(self):
        result = search_public_faq("What is a deductible?")
        assert isinstance(result.value, dict)

    def test_label_is_public(self):
        result = search_public_faq("rental car coverage")
        assert result.label.level == DataLabel.PUBLIC

    def test_label_not_untrusted(self):
        result = search_public_faq("total loss")
        assert result.label.untrusted is False

    def test_required_keys_present(self):
        result = search_public_faq("claims process")
        assert {"query", "n_results", "chunks"} <= result.value.keys()

    def test_query_echoed(self):
        q = "how long does it take"
        result = search_public_faq(q)
        assert result.value["query"] == q

    def test_n_results_matches_chunks_length(self):
        result = search_public_faq("accident steps", n_results=3)
        assert result.value["n_results"] == len(result.value["chunks"])

    def test_default_n_results_is_three(self):
        result = search_public_faq("coverage")
        assert result.value["n_results"] == 3

    def test_n_results_clamped_to_corpus_size(self):
        result = search_public_faq("any query", n_results=9999)
        assert result.value["n_results"] == _N_FAQ_CORPUS

    def test_n_results_clamped_to_one(self):
        result = search_public_faq("any query", n_results=0)
        assert result.value["n_results"] == 1

    def test_chunk_has_required_fields(self):
        result = search_public_faq("deductible waiver")
        for chunk in result.value["chunks"]:
            assert {"doc_id", "source", "text", "score", "data_label"} <= chunk.keys()

    def test_chunk_data_label_is_public(self):
        result = search_public_faq("repair shop")
        for chunk in result.value["chunks"]:
            assert chunk["data_label"] == "PUBLIC"

    def test_chunk_doc_id_starts_with_faq(self):
        result = search_public_faq("rental car")
        for chunk in result.value["chunks"]:
            assert chunk["doc_id"].startswith("faq-")

    def test_deterministic(self):
        a = search_public_faq("accident", n_results=2)
        b = search_public_faq("accident", n_results=2)
        assert a.value == b.value

    def test_different_queries_may_return_different_chunks(self):
        a = search_public_faq("faq-query-alpha-001")
        b = search_public_faq("faq-query-beta-999")
        # Not guaranteed to differ, but the stub distributes by hash —
        # with sufficiently different queries at least one field changes.
        # We just assert both are valid Labeled results.
        assert isinstance(a, Labeled)
        assert isinstance(b, Labeled)

    def test_corpus_size_is_ten(self):
        assert _N_FAQ_CORPUS == 10

    def test_all_faq_docs_reachable(self):
        seen: set[str] = set()
        target = {d["doc_id"] for d in _FAQ_CORPUS}
        for i in range(200):
            result = search_public_faq(f"probe-faq-{i:04d}", n_results=1)
            seen.add(result.value["chunks"][0]["doc_id"])
            if seen == target:
                break
        assert seen == target, f"Not all FAQ docs reached; missing: {target - seen}"


# ---------------------------------------------------------------------------
# ToolRegistry integration tests
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


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def faq_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("search_public_faq", search_public_faq)
    return r


@pytest.fixture()
def faq_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="intake_actor",
        tool="search_public_faq",
        scope={"query": "How do I file a claim?"},
    )


def _invoke_faq(registry, token, orchestrator_km, *, params=None, used_at=None, row_exists=True):
    if params is None:
        params = {"query": "How do I file a claim?"}
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
            tool_name="search_public_faq",
            params=params,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            trace_id=uuid.uuid4(),
        )
    return result, mock_log, mock_record


class TestSearchPublicFaqRegistry:
    def test_valid_invocation_succeeds(self, faq_registry, faq_token, orchestrator_km):
        result, mock_log, mock_record = _invoke_faq(faq_registry, faq_token, orchestrator_km)
        assert result
        assert result.log_id == 42
        mock_record.assert_called_once()
        assert mock_log.call_args.kwargs["action"] == "tool_call_ok"

    def test_result_value_is_labeled(self, faq_registry, faq_token, orchestrator_km):
        result, _, _ = _invoke_faq(faq_registry, faq_token, orchestrator_km)
        assert isinstance(result.value, Labeled)

    def test_result_label_is_public(self, faq_registry, faq_token, orchestrator_km):
        result, _, _ = _invoke_faq(faq_registry, faq_token, orchestrator_km)
        assert result.value.label.level == DataLabel.PUBLIC

    def test_audit_data_label_is_public(self, faq_registry, faq_token, orchestrator_km):
        """Registry must record data_label='PUBLIC', not 'CONFIDENTIAL'."""
        result, mock_log, _ = _invoke_faq(faq_registry, faq_token, orchestrator_km)
        assert mock_log.call_args.kwargs["data_label"] == "PUBLIC"

    def test_result_inner_keys(self, faq_registry, faq_token, orchestrator_km):
        result, _, _ = _invoke_faq(faq_registry, faq_token, orchestrator_km)
        inner = result.value.value
        assert {"query", "n_results", "chunks"} <= inner.keys()

    def test_audit_params_keys_not_values(self, faq_registry, faq_token, orchestrator_km):
        result, mock_log, _ = _invoke_faq(faq_registry, faq_token, orchestrator_km)
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        assert "How do I file a claim?" not in str(details)

    def test_replay_denied(self, faq_registry, faq_token, orchestrator_km):
        result, _, _ = _invoke_faq(
            faq_registry, faq_token, orchestrator_km, used_at="2026-01-01T00:00:00"
        )
        assert not result
        assert result.deny_reason is not None

    def test_unissued_token_denied_security_event(self, faq_registry, faq_token, orchestrator_km):
        result, mock_log, _ = _invoke_faq(
            faq_registry, faq_token, orchestrator_km, row_exists=False
        )
        assert not result
        assert mock_log.call_args.kwargs["security_event"] is True
