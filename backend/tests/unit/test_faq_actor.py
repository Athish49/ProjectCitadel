"""Unit tests for run_faq_actor (Sprint 4.1.9).

Imports from agent_system.actors.intake_actor (FAQ handler lives in intake actor
module per TAD: "handled by intake actor").

Tests cover:
  - Happy path: returns FaqEnvelope with response_text
  - filter_ok defaults True when conn=None
  - filter_ok reflects filter result when conn provided
  - filter_output NOT called when conn=None
  - Security event on missing capability token
  - Fallback response when LLM returns no text
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent_system.actors.intake_actor import (
    ACTOR_AGENT_ID,
    FaqEnvelope,
    run_faq_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import issue_token

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Mock helpers (same pattern as other actor tests)
# ---------------------------------------------------------------------------


def _tool_block(name: str, input_: dict, block_id: str = "tu_faq_001") -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = input_
    b.id = block_id
    return b


def _text_block(text: str) -> MagicMock:
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _response(content: list, stop_reason: str = "tool_use") -> MagicMock:
    r = MagicMock()
    r.content = content
    r.stop_reason = stop_reason
    return r


def _mock_client(*responses) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_QUERY = "How long does the claims process take?"
_SESSION = "session-faq-unit"


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def faq_tokens(orchestrator_km):
    return {
        "search_public_faq": issue_token(
            orchestrator_km,
            agent_id=ACTOR_AGENT_ID,
            tool="search_public_faq",
            scope={},
        )
    }


def _run_faq(orchestrator_km, tokens, client):
    return run_faq_actor(
        _QUERY,
        pre_issued_tokens=tokens,
        orchestrator_public_key=orchestrator_km.public_key_bytes,
        client=client,
        session_id=_SESSION,
        conn=None,
    )


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


class TestFaqActorHappyPath:
    def test_returns_faq_envelope(self, orchestrator_km, faq_tokens):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response(
                [_text_block("Typically 5–7 business days after all documents are received.")],
                "end_turn",
            ),
        )
        envelope = _run_faq(orchestrator_km, faq_tokens, client)
        assert isinstance(envelope, FaqEnvelope)

    def test_response_text_captured(self, orchestrator_km, faq_tokens):
        expected = "Typically 5–7 business days after all documents are received."
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block(expected)], "end_turn"),
        )
        envelope = _run_faq(orchestrator_km, faq_tokens, client)
        assert envelope.response_text == expected

    def test_session_id_preserved(self, orchestrator_km, faq_tokens):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("5–7 days.")], "end_turn"),
        )
        envelope = _run_faq(orchestrator_km, faq_tokens, client)
        assert envelope.session_id == _SESSION

    def test_filter_ok_true_when_conn_none(self, orchestrator_km, faq_tokens):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("5–7 days.")], "end_turn"),
        )
        envelope = _run_faq(orchestrator_km, faq_tokens, client)
        assert envelope.filter_ok is True

    def test_end_turn_no_text_returns_fallback(self, orchestrator_km, faq_tokens):
        """LLM stops with end_turn and no text → fallback message returned."""
        client = _mock_client(
            _response([], "end_turn"),
        )
        envelope = _run_faq(orchestrator_km, faq_tokens, client)
        assert isinstance(envelope.response_text, str)
        assert envelope.response_text != ""


# ---------------------------------------------------------------------------
# Egress filter wiring tests
# ---------------------------------------------------------------------------


def _registry_patches():
    return (
        patch("agent_system.tools.registry.append_log", return_value=99),
        patch("agent_system.tools.registry.record_use"),
        patch("agent_system.tools.registry._try_record_use"),
    )


class TestFaqActorEgressFilter:
    def test_filter_not_called_when_conn_none(self, orchestrator_km, faq_tokens):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("5–7 days.")], "end_turn"),
        )
        with patch("agent_system.actors.intake_actor.filter_output") as mock_filter:
            _run_faq(orchestrator_km, faq_tokens, client)
        mock_filter.assert_not_called()

    def test_filter_called_when_conn_provided(self, orchestrator_km, faq_tokens):
        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = True
        mock_fr.output = "Filtered FAQ answer."

        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("5–7 days.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.intake_actor.filter_output", return_value=mock_fr) as mock_filter:
            envelope = run_faq_actor(
                _QUERY,
                pre_issued_tokens=faq_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        mock_filter.assert_called_once()
        assert envelope.filter_ok is True
        assert envelope.response_text == "Filtered FAQ answer."

    def test_filter_ok_false_when_filter_blocks(self, orchestrator_km, faq_tokens):
        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = False
        mock_fr.output = "Blocked response."

        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("Some answer.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.intake_actor.filter_output", return_value=mock_fr):
            envelope = run_faq_actor(
                _QUERY,
                pre_issued_tokens=faq_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        assert envelope.filter_ok is False

    def test_filter_receives_public_label(self, orchestrator_km, faq_tokens):
        from agent_system.ifc.labels import DataLabel

        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = True
        mock_fr.output = "OK."

        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("Answer.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.intake_actor.filter_output", return_value=mock_fr) as mock_filter:
            run_faq_actor(
                _QUERY,
                pre_issued_tokens=faq_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs["source_label"].level == DataLabel.PUBLIC

    def test_filter_receives_intake_actor_agent_id(self, orchestrator_km, faq_tokens):
        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = True
        mock_fr.output = "OK."

        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("Answer.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.intake_actor.filter_output", return_value=mock_fr) as mock_filter:
            run_faq_actor(
                _QUERY,
                pre_issued_tokens=faq_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        assert mock_filter.call_args.kwargs["calling_agent_id"] == ACTOR_AGENT_ID


# ---------------------------------------------------------------------------
# Security: missing capability token
# ---------------------------------------------------------------------------


class TestFaqActorSecurity:
    def test_missing_token_emits_security_event(self, orchestrator_km):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": _QUERY})],
                "tool_use",
            ),
            _response([_text_block("Answer.")], "end_turn"),
        )
        audit_calls: list[dict] = []

        def _capture_audit(**kwargs):
            audit_calls.append(kwargs)

        run_faq_actor(
            _QUERY,
            pre_issued_tokens={},  # no token
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=_capture_audit,
            session_id=_SESSION,
            conn=None,
        )
        denied = [c for c in audit_calls if c.get("action") == "tool_call_denied"]
        assert len(denied) == 1
        assert denied[0]["security_event"] is True
