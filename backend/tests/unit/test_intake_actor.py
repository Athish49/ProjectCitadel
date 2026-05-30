"""Unit tests for the intake actor LLM with P4 capability-token-gated tools (task 2.1.3).

Run via:
  make test-intake-actor

All tests mock the Anthropic client — no live API calls.
All tests exercise the P4 token gate with real Ed25519 key material.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from agent_system.actors.intake_actor import (
    ACTOR_AGENT_ID,
    ACTOR_MODEL,
    MAX_LOOP_ITERATIONS,
    IntakeEnvelope,
    run_intake_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.parser.schemas import ClaimIntent, IncidentType, IntakeOutput
from agent_system.tools.capability_tokens import CapabilityToken, issue_token

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def all_tokens(orchestrator_km: KeypairManager) -> dict[str, CapabilityToken]:
    """Pre-issue one token per tool, scope={}, for intake_actor."""
    return {
        name: issue_token(
            orchestrator_km,
            agent_id=ACTOR_AGENT_ID,
            tool=name,
            scope={},
        )
        for name in ("mark_intake_complete", "request_more_info", "search_public_faq")
    }


@pytest.fixture()
def intake_output() -> IntakeOutput:
    return IntakeOutput(
        schema_version="intake@2",
        intent=ClaimIntent.new_claim,
        incident_type=IncidentType.collision,
        incident_date=date(2025, 3, 15),
        incident_location="Main St, Springfield",
        damage_description="Front bumper cracked.",
        police_report_filed=True,
        other_parties_involved=False,
        injuries_reported=False,
        intake_complete=True,
        missing_fields=[],
    )


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _tool_block(
    name: str,
    input_: dict,
    block_id: str = "tu_001",
) -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = input_
    b.id = block_id
    return b


def _text_block() -> MagicMock:
    b = MagicMock()
    b.type = "text"
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


def _audit_mock() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# IntakeEnvelope — dataclass contract
# ---------------------------------------------------------------------------


class TestIntakeEnvelope:
    def test_is_frozen(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        with pytest.raises((TypeError, AttributeError)):
            env.outcome = "changed"  # type: ignore[misc]

    def test_missing_fields_is_tuple(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert isinstance(env.missing_fields, tuple)


# ---------------------------------------------------------------------------
# Outcome: mark_intake_complete → ready_for_identity
# ---------------------------------------------------------------------------


class TestOutcomeMarkComplete:
    def test_outcome_ready_for_identity(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "Complete claim."})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "ready_for_identity"

    def test_structured_summary_captured(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "My summary."})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.structured_summary == "My summary."

    def test_missing_fields_empty(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.missing_fields == ()

    def test_session_id_preserved(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            session_id="sess-42",
        )
        assert env.session_id == "sess-42"

    def test_only_one_api_call_made(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Outcome: request_more_info → needs_more_info
# ---------------------------------------------------------------------------


class TestOutcomeRequestMoreInfo:
    def test_outcome_needs_more_info(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("request_more_info", {"field": "incident_date"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "needs_more_info"

    def test_field_captured_in_missing_fields(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("request_more_info", {"field": "incident_date"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert "incident_date" in env.missing_fields

    def test_structured_summary_is_none(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("request_more_info", {"field": "incident_location"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.structured_summary is None

    def test_multiple_fields_in_single_response(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [
                    _tool_block("request_more_info", {"field": "incident_date"}, "tu_001"),
                    _tool_block("request_more_info", {"field": "incident_location"}, "tu_002"),
                ],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert "incident_date" in env.missing_fields
        assert "incident_location" in env.missing_fields


# ---------------------------------------------------------------------------
# Outcome: no terminal tool called → reject_as_out_of_scope
# ---------------------------------------------------------------------------


class TestOutcomeNoTerminalTool:
    def test_end_turn_without_tool_use(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response([_text_block()], stop_reason="end_turn")
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "reject_as_out_of_scope"

    def test_structured_summary_none_when_rejected(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response([_text_block()], stop_reason="end_turn")
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.structured_summary is None

    def test_missing_fields_empty_when_rejected(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response([_text_block()], stop_reason="end_turn")
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.missing_fields == ()


# ---------------------------------------------------------------------------
# Multi-round loop: search_public_faq → mark_intake_complete
# ---------------------------------------------------------------------------


class TestMultiRoundLoop:
    def test_two_round_outcome_ready(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": "deductible"}, "tu_001")],
                "tool_use",
            ),
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "done"}, "tu_002")],
                "tool_use",
            ),
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "ready_for_identity"

    def test_two_round_makes_two_api_calls(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("search_public_faq", {"query": "deductible"}, "tu_001")],
                "tool_use",
            ),
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "done"}, "tu_002")],
                "tool_use",
            ),
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert client.messages.create.call_count == 2

    def test_text_blocks_skipped(self, orchestrator_km, all_tokens, intake_output):
        """Text blocks mixed into content are ignored; only tool_use blocks are processed."""
        client = _mock_client(
            _response(
                [
                    _text_block(),
                    _tool_block("mark_intake_complete", {"structured_summary": "ok"}, "tu_001"),
                ],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "ready_for_identity"


# ---------------------------------------------------------------------------
# Loop exhaustion
# ---------------------------------------------------------------------------


class TestLoopExhausted:
    def test_exhausted_outcome_reject(self, orchestrator_km, all_tokens, intake_output):
        faq_response = _response(
            [_tool_block("search_public_faq", {"query": "coverage"})], "tool_use"
        )
        client = _mock_client(*([faq_response] * MAX_LOOP_ITERATIONS))
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "reject_as_out_of_scope"

    def test_exhausted_audit_loop_exhausted_true(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        faq_response = _response(
            [_tool_block("search_public_faq", {"query": "coverage"})], "tool_use"
        )
        client = _mock_client(*([faq_response] * MAX_LOOP_ITERATIONS))
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        intake_decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert len(intake_decision_calls) == 1
        assert intake_decision_calls[0].kwargs["details"]["loop_exhausted"] is True

    def test_exhausted_uses_max_iterations_calls(self, orchestrator_km, all_tokens, intake_output):
        faq_response = _response(
            [_tool_block("search_public_faq", {"query": "coverage"})], "tool_use"
        )
        client = _mock_client(*([faq_response] * MAX_LOOP_ITERATIONS))
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert client.messages.create.call_count == MAX_LOOP_ITERATIONS


# ---------------------------------------------------------------------------
# P4 capability token gate
# ---------------------------------------------------------------------------


class TestCapabilityTokenGate:
    def test_missing_token_denied_audited(self, orchestrator_km, intake_output):
        """Tool not in pre_issued_tokens → tool_call_denied security event."""
        audit = _audit_mock()
        # Supply only search_public_faq token; LLM tries mark_intake_complete
        partial_tokens = {
            "search_public_faq": issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool="search_public_faq",
                scope={},
            )
        }
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            ),
            _response([_text_block()], "end_turn"),
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=partial_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        denied_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "tool_call_denied"
        ]
        assert len(denied_calls) >= 1
        assert denied_calls[0].kwargs["security_event"] is True

    def test_missing_token_deny_reason_no_token(self, orchestrator_km, intake_output):
        audit = _audit_mock()
        partial_tokens: dict = {}
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            ),
            _response([_text_block()], "end_turn"),
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=partial_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        denied_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "tool_call_denied"
        ]
        details = denied_calls[0].kwargs["details"]
        assert details.get("deny_reason") == "no_token_issued"

    def test_forged_token_denied(self, orchestrator_km, intake_output):
        """Token signed by a different key → DENIED_SIGNATURE, security_event=True."""
        audit = _audit_mock()
        attacker_km = KeypairManager.generate("orchestrator")
        forged_tokens = {
            "mark_intake_complete": issue_token(
                attacker_km,  # wrong key
                agent_id=ACTOR_AGENT_ID,
                tool="mark_intake_complete",
                scope={},
            )
        }
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            ),
            _response([_text_block()], "end_turn"),
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=forged_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,  # legit key
            client=client,
            audit_fn=audit,
        )
        denied_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "tool_call_denied"
        ]
        assert len(denied_calls) >= 1
        assert denied_calls[0].kwargs["security_event"] is True

    def test_scope_mismatch_denied(self, orchestrator_km, intake_output):
        """Token scope={"field": "incident_date"}, call with field="incident_location" → denied."""
        audit = _audit_mock()
        scoped_tokens = {
            "request_more_info": issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool="request_more_info",
                scope={"field": "incident_date"},
            )
        }
        client = _mock_client(
            _response(
                [_tool_block("request_more_info", {"field": "incident_location"})],
                "tool_use",
            ),
            _response([_text_block()], "end_turn"),
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=scoped_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        denied_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "tool_call_denied"
        ]
        assert len(denied_calls) >= 1
        assert denied_calls[0].kwargs["security_event"] is True

    def test_scope_match_allowed(self, orchestrator_km, intake_output):
        """Token scope={"field": "incident_date"}, call with field="incident_date" → allowed."""
        scoped_tokens = {
            "request_more_info": issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool="request_more_info",
                scope={"field": "incident_date"},
            )
        }
        client = _mock_client(
            _response(
                [_tool_block("request_more_info", {"field": "incident_date"})],
                "tool_use",
            )
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=scoped_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "needs_more_info"
        assert "incident_date" in env.missing_fields

    def test_denied_tool_does_not_update_outcome(self, orchestrator_km, intake_output):
        """A denied tool call must not set terminal_tool; outcome falls through to reject."""
        partial_tokens: dict = {}
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            ),
            _response([_text_block()], "end_turn"),
        )
        env = run_intake_actor(
            intake_output,
            pre_issued_tokens=partial_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        assert env.outcome == "reject_as_out_of_scope"


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_intake_decision_audited(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        actions = [call.kwargs["action"] for call in audit.call_args_list]
        assert "intake_decision" in actions

    def test_intake_decision_data_label_internal(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert decision_calls[0].kwargs["data_label"] == "INTERNAL"

    def test_intake_decision_not_security_event(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert decision_calls[0].kwargs["security_event"] is False

    def test_intake_decision_details_has_outcome(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert "outcome" in decision_calls[0].kwargs["details"]

    def test_intake_decision_details_has_loop_exhausted(
        self, orchestrator_km, all_tokens, intake_output
    ):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert "loop_exhausted" in decision_calls[0].kwargs["details"]

    def test_intake_decision_loop_exhausted_false_on_success(
        self, orchestrator_km, all_tokens, intake_output
    ):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert decision_calls[0].kwargs["details"]["loop_exhausted"] is False

    def test_intake_decision_agent_id(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert decision_calls[0].kwargs["agent_id"] == ACTOR_AGENT_ID

    def test_intake_decision_target_is_session_id(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
            session_id="sess-99",
        )
        decision_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "intake_decision"
        ]
        assert decision_calls[0].kwargs["target"] == "sess-99"

    def test_tool_call_ok_audited(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        ok_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "tool_call_ok"
        ]
        assert len(ok_calls) >= 1

    def test_tool_call_ok_data_label_confidential(self, orchestrator_km, all_tokens, intake_output):
        audit = _audit_mock()
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
            audit_fn=audit,
        )
        ok_calls = [
            call for call in audit.call_args_list
            if call.kwargs.get("action") == "tool_call_ok"
        ]
        assert ok_calls[0].kwargs["data_label"] == "CONFIDENTIAL"

    def test_no_audit_fn_does_not_raise(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        # audit_fn=None → noop, no error
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )


# ---------------------------------------------------------------------------
# API call shape
# ---------------------------------------------------------------------------


class TestApiCallShape:
    def test_uses_correct_model(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert kwargs["model"] == ACTOR_MODEL

    def test_temperature_is_zero(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert kwargs["temperature"] == 0

    def test_tools_list_non_empty(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert len(kwargs["tools"]) == 3

    def test_intake_json_in_user_message(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        messages = kwargs["messages"]
        user_messages = [m for m in messages if m["role"] == "user"]
        content = " ".join(
            m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])
            for m in user_messages
        )
        assert "collision" in content

    def test_system_prompt_present(self, orchestrator_km, all_tokens, intake_output):
        client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": "ok"})],
                "tool_use",
            )
        )
        run_intake_actor(
            intake_output,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert "system" in kwargs
        assert len(kwargs["system"]) > 0


# ---------------------------------------------------------------------------
# API error propagation
# ---------------------------------------------------------------------------


class TestApiErrorPropagation:
    def test_api_error_propagates(self, orchestrator_km, all_tokens, intake_output):
        import anthropic as _anthropic

        client = MagicMock()
        client.messages.create.side_effect = _anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(_anthropic.APIConnectionError):
            run_intake_actor(
                intake_output,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
            )

    def test_api_error_no_audit(self, orchestrator_km, all_tokens, intake_output):
        import anthropic as _anthropic

        audit = _audit_mock()
        client = MagicMock()
        client.messages.create.side_effect = _anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(_anthropic.APIConnectionError):
            run_intake_actor(
                intake_output,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                audit_fn=audit,
            )
        audit.assert_not_called()
