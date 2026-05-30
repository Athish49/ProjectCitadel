"""Unit tests for run_settlement_actor (Sprint 4.2.3).

All tests mock the Anthropic client — no live API calls.
All P4 tests use real Ed25519 key material.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from agent_system.actors.settlement_actor import (
    ACTOR_AGENT_ID,
    ACTOR_MODEL,
    MAX_LOOP_ITERATIONS,
    SettlementEnvelope,
    run_settlement_actor,
)
from agent_system.egress.filter import REFUSAL_MESSAGE
from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import CapabilityToken, issue_token
from agent_system.tools.implementations.settlement_tools import (
    calculate_settlement,
    draft_summary,
)

pytestmark = pytest.mark.unit

_CID = "clm-test-001"

_EXPECTED_SETTLEMENT = calculate_settlement(_CID).value
_EXPECTED_ESCALATED_SUMMARY = draft_summary(
    _CID, "ESCALATED", _EXPECTED_SETTLEMENT["offered_amount"], ""
).value["summary"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def all_tokens(orchestrator_km: KeypairManager) -> dict[str, CapabilityToken]:
    return {
        t: issue_token(orchestrator_km, agent_id=ACTOR_AGENT_ID, tool=t, scope={})
        for t in ("calculate_settlement", "request_payout", "draft_summary")
    }


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _tool_block(name: str, input_: dict, block_id: str | None = None) -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = input_
    b.id = block_id or f"tu_{name}"
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


def _make_actor_conn(n_token_log_fetchones: int) -> MagicMock:
    """Mock conn for full-path actor tests.

    Each tool call through ToolRegistry does one fetchone on capability_token_log.
    """
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.side_effect = [(None,)] * n_token_log_fetchones
    conn.cursor.return_value = cur
    return conn


def _all_settlement_blocks() -> list:
    return [
        _tool_block("calculate_settlement", {"claim_id": _CID}, "tu_cs"),
        _tool_block("draft_summary", {
            "claim_id":         _CID,
            "outcome":          "ESCALATED",
            "offered_amount":   _EXPECTED_SETTLEMENT["offered_amount"],
            "payout_reference": "",
        }, "tu_ds"),
    ]


def _run_actor(
    orchestrator_km,
    tokens,
    client,
    *,
    session_id: str = "sess-test",
    audit_fn=None,
    conn=None,
) -> SettlementEnvelope:
    return run_settlement_actor(
        claim_id=_CID,
        pre_issued_tokens=tokens,
        orchestrator_public_key=orchestrator_km.public_key_bytes,
        client=client,
        session_id=session_id,
        audit_fn=audit_fn,
        conn=conn,
    )


# ---------------------------------------------------------------------------
# SettlementEnvelope — dataclass contract
# ---------------------------------------------------------------------------


class TestSettlementEnvelope:
    def test_is_frozen(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        with pytest.raises((TypeError, AttributeError)):
            env.summary = "changed"  # type: ignore[misc]

    def test_session_id_preserved(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client, session_id="sess-42")
        assert env.session_id == "sess-42"

    def test_claim_id_preserved(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.claim_id == _CID


# ---------------------------------------------------------------------------
# Happy path — calculate_settlement + draft_summary (legacy conn=None)
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_settlement_amount_from_calculate_settlement(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.settlement_amount == _EXPECTED_SETTLEMENT["offered_amount"]

    def test_summary_from_draft_summary(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.summary == _EXPECTED_ESCALATED_SUMMARY

    def test_payout_status_escalated_when_no_request_payout(self, orchestrator_km, all_tokens):
        """Legacy path: request_payout unavailable → always escalated."""
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.payout_status == "escalated"

    def test_two_api_calls_for_one_tool_turn(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        assert client.messages.create.call_count == 2

    def test_calculate_settlement_result_sent_to_llm(self, orchestrator_km, all_tokens):
        """Tool result for calculate_settlement must include offered_amount."""
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        second_call_msgs = client.messages.create.call_args_list[1].kwargs["messages"]
        tool_results = second_call_msgs[-1]["content"]
        cs_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_cs")
        parsed = json.loads(cs_result["content"])
        assert "offered_amount" in parsed

    def test_draft_summary_result_sent_to_llm(self, orchestrator_km, all_tokens):
        """Tool result for draft_summary must include summary field."""
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        second_call_msgs = client.messages.create.call_args_list[1].kwargs["messages"]
        tool_results = second_call_msgs[-1]["content"]
        ds_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_ds")
        parsed = json.loads(ds_result["content"])
        assert "summary" in parsed


# ---------------------------------------------------------------------------
# Fallback / fail-closed defaults
# ---------------------------------------------------------------------------


class TestFallbackDefaults:
    def test_no_tool_calls_payout_status_escalated(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.payout_status == "escalated"

    def test_no_tool_calls_offered_amount_zero(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.settlement_amount == 0.0

    def test_no_tool_calls_fallback_summary(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert isinstance(env.summary, str)
        assert len(env.summary) > 0

    def test_end_turn_immediately_returns_envelope(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert isinstance(env, SettlementEnvelope)

    def test_only_calculate_settlement_called_escalated(self, orchestrator_km, all_tokens):
        """calculate_settlement called but no draft_summary → fallback summary."""
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID}, "tu_cs")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.settlement_amount == _EXPECTED_SETTLEMENT["offered_amount"]
        assert env.payout_status == "escalated"


# ---------------------------------------------------------------------------
# Multi-turn loop — tools spread across iterations
# ---------------------------------------------------------------------------


class TestMultiTurnLoop:
    def test_tools_across_two_turns(self, orchestrator_km, all_tokens):
        """calculate_settlement in turn 1; draft_summary in turn 2."""
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID}, "tu_cs")], "tool_use"),
            _response([_tool_block("draft_summary", {
                "claim_id":         _CID,
                "outcome":          "ESCALATED",
                "offered_amount":   _EXPECTED_SETTLEMENT["offered_amount"],
                "payout_reference": "",
            }, "tu_ds")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.settlement_amount == _EXPECTED_SETTLEMENT["offered_amount"]
        assert env.summary == _EXPECTED_ESCALATED_SUMMARY
        assert client.messages.create.call_count == 3

    def test_max_iterations_terminates_loop(self, orchestrator_km, all_tokens):
        """Loop must not exceed MAX_LOOP_ITERATIONS even if LLM never ends."""
        repeated = _response(
            [_tool_block("calculate_settlement", {"claim_id": _CID})], "tool_use"
        )
        client = _mock_client(*([repeated] * (MAX_LOOP_ITERATIONS + 5)))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert client.messages.create.call_count == MAX_LOOP_ITERATIONS
        assert isinstance(env, SettlementEnvelope)


# ---------------------------------------------------------------------------
# P4 capability token gate
# ---------------------------------------------------------------------------


class TestCapabilityTokenGate:
    def test_missing_token_audited_as_security_event(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, {}, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_missing_token_deny_reason(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, {}, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert denied[0].kwargs["details"]["deny_reason"] == "no_token_issued"

    def test_missing_token_still_returns_envelope(self, orchestrator_km):
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, {}, client)
        assert isinstance(env, SettlementEnvelope)

    def test_missing_token_settlement_amount_zero(self, orchestrator_km):
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, {}, client)
        assert env.settlement_amount == 0.0

    def test_forged_token_denied(self, orchestrator_km):
        audit = _audit_mock()
        attacker_km = KeypairManager.generate("orchestrator")
        forged = {
            "calculate_settlement": issue_token(
                attacker_km, agent_id=ACTOR_AGENT_ID, tool="calculate_settlement", scope={}
            )
        }
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, forged, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_request_payout_not_available_on_legacy_path(self, orchestrator_km, all_tokens):
        """request_payout call on conn=None path → error result, settlement_amount=0.0."""
        client = _mock_client(
            _response([_tool_block("request_payout", {"claim_id": _CID}, "tu_rp")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        # No payout result captured → settlement_amount falls back to 0.0
        assert env.settlement_amount == 0.0
        assert env.payout_status == "escalated"


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_settlement_issued_audited(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        actions = [c.kwargs["action"] for c in audit.call_args_list]
        assert "settlement_issued" in actions

    def test_settlement_issued_stub_is_false(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert issued[0].kwargs["details"]["stub"] is False

    def test_settlement_issued_agent_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert issued[0].kwargs["agent_id"] == ACTOR_AGENT_ID

    def test_settlement_issued_target_is_session_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, session_id="sess-audit-99", audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert issued[0].kwargs["target"] == "sess-audit-99"

    def test_settlement_issued_data_label_confidential(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert issued[0].kwargs["data_label"] == "CONFIDENTIAL"

    def test_settlement_issued_not_security_event(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert issued[0].kwargs["security_event"] is False

    def test_settlement_issued_details_has_claim_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert issued[0].kwargs["details"]["claim_id"] == _CID

    def test_tool_call_ok_audited_on_successful_dispatch(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("calculate_settlement", {"claim_id": _CID}, "tu_cs")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        ok_calls = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_ok"]
        assert len(ok_calls) >= 1

    def test_no_audit_fn_does_not_raise(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)


# ---------------------------------------------------------------------------
# API call shape
# ---------------------------------------------------------------------------


class TestApiCallShape:
    def test_uses_correct_model(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert kwargs["model"] == ACTOR_MODEL

    def test_temperature_is_zero(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert kwargs["temperature"] == 0

    def test_tools_list_has_three_tools(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert len(kwargs["tools"]) == 3

    def test_tool_names_correct(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        tool_names = {t["name"] for t in kwargs["tools"]}
        assert tool_names == {"calculate_settlement", "request_payout", "draft_summary"}

    def test_system_prompt_present(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert "system" in kwargs
        assert len(kwargs["system"]) > 0

    def test_claim_id_in_user_message(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        user_content = " ".join(
            m["content"] if isinstance(m["content"], str) else str(m["content"])
            for m in kwargs["messages"]
            if m["role"] == "user"
        )
        assert _CID in user_content


# ---------------------------------------------------------------------------
# API error propagation
# ---------------------------------------------------------------------------


class TestApiErrorPropagation:
    def test_api_error_propagates(self, orchestrator_km, all_tokens):
        import anthropic as _anthropic

        client = MagicMock()
        client.messages.create.side_effect = _anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(_anthropic.APIConnectionError):
            _run_actor(orchestrator_km, all_tokens, client)

    def test_api_error_no_settlement_audit(self, orchestrator_km, all_tokens):
        import anthropic as _anthropic

        audit = _audit_mock()
        client = MagicMock()
        client.messages.create.side_effect = _anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(_anthropic.APIConnectionError):
            _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        issued = [c for c in audit.call_args_list if c.kwargs.get("action") == "settlement_issued"]
        assert len(issued) == 0


# ---------------------------------------------------------------------------
# P10 — Egress filter (full path with mock conn)
# ---------------------------------------------------------------------------


class TestEgressFilter:
    """P10 load-bearing tests: draft_summary output passes through filter_output
    before it reaches SettlementEnvelope.summary.
    """

    def _run_with_mock_conn_and_filter(
        self,
        orchestrator_km,
        all_tokens,
        filter_return_value,
        n_tool_calls: int = 2,
    ) -> SettlementEnvelope:
        """Run actor (full path) with patched filter_output and mock DB conn."""
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        mock_conn = _make_actor_conn(n_tool_calls)
        with (
            patch("agent_system.tools.registry.append_log", return_value=1),
            patch("agent_system.tools.registry.record_use"),
            patch("agent_system.tools.registry._try_record_use"),
            patch("agent_system.actors.settlement_actor.filter_output") as mock_filter,
        ):
            mock_filter.return_value = filter_return_value
            env = run_settlement_actor(
                claim_id=_CID,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                conn=mock_conn,
            )
        return env

    def test_pii_in_summary_sets_refusal_message(self, orchestrator_km, all_tokens):
        """Egress filter blocking PII → envelope.summary = REFUSAL_MESSAGE."""
        from agent_system.egress.filter import FilterResult

        env = self._run_with_mock_conn_and_filter(
            orchestrator_km,
            all_tokens,
            FilterResult(ok=False, output=REFUSAL_MESSAGE, violations=["pii:ssn"]),
        )
        assert env.summary == REFUSAL_MESSAGE

    def test_pii_block_escalates_payout_status(self, orchestrator_km, all_tokens):
        """Egress filter block → payout_status forced to 'escalated'."""
        from agent_system.egress.filter import FilterResult

        env = self._run_with_mock_conn_and_filter(
            orchestrator_km,
            all_tokens,
            FilterResult(ok=False, output=REFUSAL_MESSAGE, violations=["pii:ssn"]),
        )
        assert env.payout_status == "escalated"

    def test_filter_ok_preserves_summary(self, orchestrator_km, all_tokens):
        """Egress filter passing → envelope.summary is the drafted text."""
        from agent_system.egress.filter import FilterResult

        env = self._run_with_mock_conn_and_filter(
            orchestrator_km,
            all_tokens,
            FilterResult(ok=True, output=_EXPECTED_ESCALATED_SUMMARY),
        )
        assert env.summary == _EXPECTED_ESCALATED_SUMMARY

    def test_filter_called_with_actor_agent_id(self, orchestrator_km, all_tokens):
        """filter_output must be called with ACTOR_AGENT_ID as calling_agent_id."""
        from agent_system.egress.filter import FilterResult

        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        mock_conn = _make_actor_conn(2)
        with (
            patch("agent_system.tools.registry.append_log", return_value=1),
            patch("agent_system.tools.registry.record_use"),
            patch("agent_system.tools.registry._try_record_use"),
            patch("agent_system.actors.settlement_actor.filter_output") as mock_filter,
        ):
            mock_filter.return_value = FilterResult(ok=True, output=_EXPECTED_ESCALATED_SUMMARY)
            run_settlement_actor(
                claim_id=_CID,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                client=client,
                conn=mock_conn,
            )
        mock_filter.assert_called_once()
        assert mock_filter.call_args.kwargs["calling_agent_id"] == ACTOR_AGENT_ID

    def test_filter_not_called_on_legacy_path(self, orchestrator_km, all_tokens):
        """conn=None → filter_output is never called (no egress filtering on legacy path)."""
        client = _mock_client(
            _response(_all_settlement_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        with patch("agent_system.actors.settlement_actor.filter_output") as mock_filter:
            _run_actor(orchestrator_km, all_tokens, client)  # conn=None
        mock_filter.assert_not_called()
