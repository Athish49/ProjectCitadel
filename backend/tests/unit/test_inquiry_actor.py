"""Unit tests for the inquiry actor (Sprint 4.1.8–4.1.9).

Tests cover:
  - claim_status intent: happy path, tool_call_denied on missing token
  - policy_question intent: happy path, tool_call_denied on missing token
  - complaint intent: happy path, complaint_captured flag, missing token
  - Invalid intent raises ValueError (new_claim, faq)
  - Egress filter wiring: filter_ok=True on pass, filter_ok=False on block
  - Fallback response when LLM returns no text
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent_system.actors.inquiry_actor import (
    ACTOR_AGENT_ID,
    InquiryEnvelope,
    run_inquiry_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.parser.schemas.intake import ClaimIntent
from agent_system.tools.capability_tokens import issue_token

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Mock helpers (mirrors other actor tests)
# ---------------------------------------------------------------------------


def _tool_block(name: str, input_: dict, block_id: str = "tu_001") -> MagicMock:
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

_CLAIM_ID = "claim-inquiry-unit-001"
_SESSION = "session-inquiry-unit"


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def status_tokens(orchestrator_km):
    return {
        "lookup_claim_status": issue_token(
            orchestrator_km,
            agent_id=ACTOR_AGENT_ID,
            tool="lookup_claim_status",
            scope={},
        )
    }


@pytest.fixture()
def policy_tokens(orchestrator_km):
    return {
        name: issue_token(
            orchestrator_km,
            agent_id=ACTOR_AGENT_ID,
            tool=name,
            scope={},
        )
        for name in ("lookup_coverage", "search_policy_docs")
    }


# ---------------------------------------------------------------------------
# Helper: run actor without DB (conn=None, filter skipped)
# ---------------------------------------------------------------------------


def _run_status(orchestrator_km, tokens, client):
    return run_inquiry_actor(
        claim_id=_CLAIM_ID,
        intent=ClaimIntent.claim_status,
        pre_issued_tokens=tokens,
        orchestrator_public_key=orchestrator_km.public_key_bytes,
        client=client,
        session_id=_SESSION,
        conn=None,
    )


def _run_policy(orchestrator_km, tokens, client):
    return run_inquiry_actor(
        claim_id=_CLAIM_ID,
        intent=ClaimIntent.policy_question,
        pre_issued_tokens=tokens,
        orchestrator_public_key=orchestrator_km.public_key_bytes,
        client=client,
        session_id=_SESSION,
        conn=None,
    )


# ---------------------------------------------------------------------------
# claim_status intent tests
# ---------------------------------------------------------------------------


class TestInquiryActorClaimStatus:
    def test_happy_path_returns_envelope(self, orchestrator_km, status_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response(
                [_text_block("Your claim CLM-00000001 is currently in PROCESSING stage.")],
                "end_turn",
            ),
        )
        envelope = _run_status(orchestrator_km, status_tokens, client)
        assert isinstance(envelope, InquiryEnvelope)

    def test_happy_path_intent_preserved(self, orchestrator_km, status_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Your claim is processing.")], "end_turn"),
        )
        envelope = _run_status(orchestrator_km, status_tokens, client)
        assert envelope.intent == ClaimIntent.claim_status

    def test_happy_path_session_id(self, orchestrator_km, status_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Processing.")], "end_turn"),
        )
        envelope = _run_status(orchestrator_km, status_tokens, client)
        assert envelope.session_id == _SESSION

    def test_happy_path_claim_id(self, orchestrator_km, status_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Processing.")], "end_turn"),
        )
        envelope = _run_status(orchestrator_km, status_tokens, client)
        assert envelope.claim_id == _CLAIM_ID

    def test_filter_ok_true_when_conn_none(self, orchestrator_km, status_tokens):
        """filter_ok must default True when conn is None (filter not applied)."""
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Processing.")], "end_turn"),
        )
        envelope = _run_status(orchestrator_km, status_tokens, client)
        assert envelope.filter_ok is True

    def test_response_text_captured(self, orchestrator_km, status_tokens):
        expected_text = "Your claim is in the PROCESSING stage."
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block(expected_text)], "end_turn"),
        )
        envelope = _run_status(orchestrator_km, status_tokens, client)
        assert envelope.response_text == expected_text

    def test_missing_token_emits_security_event(self, orchestrator_km):
        """No token for lookup_claim_status → tool_call_denied + security_event."""
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("I cannot retrieve that information.")], "end_turn"),
        )
        audit_calls: list[dict] = []

        def _capture_audit(**kwargs):
            audit_calls.append(kwargs)

        run_inquiry_actor(
            claim_id=_CLAIM_ID,
            intent=ClaimIntent.claim_status,
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

    def test_end_turn_without_tool_call_returns_fallback(self, orchestrator_km):
        """LLM stops immediately with end_turn and no text → fallback message."""
        client = _mock_client(
            _response([], "end_turn"),
        )
        envelope = run_inquiry_actor(
            claim_id=_CLAIM_ID,
            intent=ClaimIntent.claim_status,
            pre_issued_tokens={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            session_id=_SESSION,
            conn=None,
        )
        assert envelope.response_text != ""
        assert isinstance(envelope.response_text, str)


# ---------------------------------------------------------------------------
# policy_question intent tests
# ---------------------------------------------------------------------------


class TestInquiryActorPolicyQuestion:
    def test_happy_path_returns_envelope(self, orchestrator_km, policy_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_coverage", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response(
                [_text_block("Your policy type is COMPREHENSIVE with STANDARD coverage.")],
                "end_turn",
            ),
        )
        envelope = _run_policy(orchestrator_km, policy_tokens, client)
        assert isinstance(envelope, InquiryEnvelope)

    def test_happy_path_intent_preserved(self, orchestrator_km, policy_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_coverage", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Your coverage is active.")], "end_turn"),
        )
        envelope = _run_policy(orchestrator_km, policy_tokens, client)
        assert envelope.intent == ClaimIntent.policy_question

    def test_filter_ok_true_when_conn_none(self, orchestrator_km, policy_tokens):
        client = _mock_client(
            _response(
                [_tool_block("lookup_coverage", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Coverage active.")], "end_turn"),
        )
        envelope = _run_policy(orchestrator_km, policy_tokens, client)
        assert envelope.filter_ok is True

    def test_search_policy_docs_also_gated(self, orchestrator_km, policy_tokens):
        """search_policy_docs call succeeds when its token is in pre_issued_tokens."""
        client = _mock_client(
            _response(
                [_tool_block("search_policy_docs", {"query": "deductible waiver"}, "tu_002")],
                "tool_use",
            ),
            _response([_text_block("Policy excerpt: deductible may be waived.")], "end_turn"),
        )
        envelope = _run_policy(orchestrator_km, policy_tokens, client)
        assert isinstance(envelope, InquiryEnvelope)
        assert envelope.filter_ok is True


# ---------------------------------------------------------------------------
# Egress filter wiring tests
# ---------------------------------------------------------------------------


def _registry_patches():
    """Context manager that patches ToolRegistry internals so mock_conn doesn't break."""
    return (
        patch("agent_system.tools.registry.append_log", return_value=99),
        patch("agent_system.tools.registry.record_use"),
        patch("agent_system.tools.registry._try_record_use"),
    )


class TestInquiryActorEgressFilter:
    def test_filter_called_when_conn_provided(self, orchestrator_km, status_tokens):
        """filter_output must be called exactly once when conn is provided."""
        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = True
        mock_fr.output = "Filtered response."

        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Your claim is in PROCESSING.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.inquiry_actor.filter_output", return_value=mock_fr) as mock_filter:
            envelope = run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.claim_status,
                pre_issued_tokens=status_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        mock_filter.assert_called_once()
        assert envelope.filter_ok is True
        assert envelope.response_text == "Filtered response."

    def test_filter_ok_false_when_filter_blocks(self, orchestrator_km, status_tokens):
        """When filter_output returns ok=False, envelope.filter_ok must be False."""
        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = False
        mock_fr.output = "I'm not able to share that information. Please contact support."

        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Your SSN is 123-45-6789.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.inquiry_actor.filter_output", return_value=mock_fr):
            envelope = run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.claim_status,
                pre_issued_tokens=status_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        assert envelope.filter_ok is False
        assert "Please contact support" in envelope.response_text

    def test_filter_not_called_when_conn_none(self, orchestrator_km, status_tokens):
        """filter_output must NOT be called when conn is None."""
        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Processing.")], "end_turn"),
        )

        with patch("agent_system.actors.inquiry_actor.filter_output") as mock_filter:
            run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.claim_status,
                pre_issued_tokens=status_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=None,
            )

        mock_filter.assert_not_called()

    def test_filter_receives_confidential_label(self, orchestrator_km, status_tokens):
        """filter_output must be called with source_label=CONFIDENTIAL."""
        from agent_system.ifc.labels import DataLabel

        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = True
        mock_fr.output = "OK."

        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Processing.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.inquiry_actor.filter_output", return_value=mock_fr) as mock_filter:
            run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.claim_status,
                pre_issued_tokens=status_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs["source_label"].level == DataLabel.CONFIDENTIAL

    def test_filter_receives_calling_agent_id(self, orchestrator_km, status_tokens):
        mock_conn = MagicMock()
        mock_fr = MagicMock()
        mock_fr.ok = True
        mock_fr.output = "OK."

        client = _mock_client(
            _response(
                [_tool_block("lookup_claim_status", {"claim_id": _CLAIM_ID})],
                "tool_use",
            ),
            _response([_text_block("Processing.")], "end_turn"),
        )

        p1, p2, p3 = _registry_patches()
        with p1, p2, p3, patch("agent_system.actors.inquiry_actor.filter_output", return_value=mock_fr) as mock_filter:
            run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.claim_status,
                pre_issued_tokens=status_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                session_id=_SESSION,
                conn=mock_conn,
            )

        assert mock_filter.call_args.kwargs["calling_agent_id"] == ACTOR_AGENT_ID


# ---------------------------------------------------------------------------
# Invalid intent
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# complaint intent tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def complaint_tokens(orchestrator_km):
    return {
        "capture_complaint": issue_token(
            orchestrator_km,
            agent_id=ACTOR_AGENT_ID,
            tool="capture_complaint",
            scope={},
        )
    }


def _run_complaint(orchestrator_km, tokens, client, *, user_text: str | None = None):
    return run_inquiry_actor(
        claim_id=_CLAIM_ID,
        intent=ClaimIntent.complaint,
        pre_issued_tokens=tokens,
        orchestrator_public_key=orchestrator_km.public_key_bytes,
        client=client,
        session_id=_SESSION,
        conn=None,
        user_text=user_text,
    )


class TestInquiryActorComplaint:
    def test_happy_path_returns_envelope(self, orchestrator_km, complaint_tokens):
        client = _mock_client(
            _response(
                [_tool_block(
                    "capture_complaint",
                    {"session_id": _SESSION, "category": "service", "description": "Agent was rude."},
                )],
                "tool_use",
            ),
            _response(
                [_text_block("Your complaint has been recorded and escalated.")],
                "end_turn",
            ),
        )
        envelope = _run_complaint(orchestrator_km, complaint_tokens, client)
        assert isinstance(envelope, InquiryEnvelope)

    def test_complaint_captured_true_on_tool_call(self, orchestrator_km, complaint_tokens):
        client = _mock_client(
            _response(
                [_tool_block(
                    "capture_complaint",
                    {"session_id": _SESSION, "category": "coverage", "description": "Wrong coverage applied."},
                )],
                "tool_use",
            ),
            _response([_text_block("Complaint escalated.")], "end_turn"),
        )
        envelope = _run_complaint(orchestrator_km, complaint_tokens, client)
        assert envelope.complaint_captured is True

    def test_complaint_captured_false_when_no_tool_call(self, orchestrator_km, complaint_tokens):
        """LLM skips tool call → complaint_captured stays False."""
        client = _mock_client(
            _response([_text_block("I'll note your complaint.")], "end_turn"),
        )
        envelope = _run_complaint(orchestrator_km, complaint_tokens, client)
        assert envelope.complaint_captured is False

    def test_intent_preserved(self, orchestrator_km, complaint_tokens):
        client = _mock_client(
            _response(
                [_tool_block(
                    "capture_complaint",
                    {"session_id": _SESSION, "category": "process", "description": "Too slow."},
                )],
                "tool_use",
            ),
            _response([_text_block("Complaint recorded.")], "end_turn"),
        )
        envelope = _run_complaint(orchestrator_km, complaint_tokens, client)
        assert envelope.intent == ClaimIntent.complaint

    def test_filter_ok_true_when_conn_none(self, orchestrator_km, complaint_tokens):
        client = _mock_client(
            _response(
                [_tool_block(
                    "capture_complaint",
                    {"session_id": _SESSION, "category": "decision", "description": "Bad decision."},
                )],
                "tool_use",
            ),
            _response([_text_block("Escalated.")], "end_turn"),
        )
        envelope = _run_complaint(orchestrator_km, complaint_tokens, client)
        assert envelope.filter_ok is True

    def test_missing_token_emits_security_event(self, orchestrator_km):
        client = _mock_client(
            _response(
                [_tool_block(
                    "capture_complaint",
                    {"session_id": _SESSION, "category": "other", "description": "General complaint."},
                )],
                "tool_use",
            ),
            _response([_text_block("Noted.")], "end_turn"),
        )
        audit_calls: list[dict] = []

        def _capture_audit(**kwargs):
            audit_calls.append(kwargs)

        run_inquiry_actor(
            claim_id=_CLAIM_ID,
            intent=ClaimIntent.complaint,
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

    def test_user_text_forwarded_to_message(self, orchestrator_km, complaint_tokens):
        """user_text parameter should be wired through without error."""
        client = _mock_client(
            _response(
                [_tool_block(
                    "capture_complaint",
                    {"session_id": _SESSION, "category": "service", "description": "I am unhappy."},
                )],
                "tool_use",
            ),
            _response([_text_block("Your complaint has been escalated.")], "end_turn"),
        )
        envelope = _run_complaint(
            orchestrator_km, complaint_tokens, client, user_text="I am unhappy with the service."
        )
        assert isinstance(envelope, InquiryEnvelope)


# ---------------------------------------------------------------------------
# Invalid intent
# ---------------------------------------------------------------------------


class TestInquiryActorInvalidIntent:
    def test_invalid_intent_raises_value_error(self, orchestrator_km):
        with pytest.raises(ValueError, match="run_inquiry_actor does not handle intent"):
            run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.new_claim,
                pre_issued_tokens={},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=_mock_client(),
                session_id=_SESSION,
                conn=None,
            )

    def test_faq_intent_raises_value_error(self, orchestrator_km):
        with pytest.raises(ValueError):
            run_inquiry_actor(
                claim_id=_CLAIM_ID,
                intent=ClaimIntent.faq,
                pre_issued_tokens={},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=_mock_client(),
                session_id=_SESSION,
                conn=None,
            )
