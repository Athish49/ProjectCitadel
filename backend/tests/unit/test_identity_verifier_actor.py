"""Unit tests for the identity verifier actor (P1/P3/P4 — task 2.1.4).

Run via:
  make test-identity-verifier-actor

All tests mock the Anthropic client — no live API calls.
All P4 tests use real Ed25519 key material.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_system.actors.identity_verifier_actor import (
    ACTOR_AGENT_ID,
    ACTOR_MODEL,
    IdentityEnvelope,
    run_identity_verifier_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import CapabilityToken, issue_token

pytestmark = pytest.mark.unit

_TOOL_NAME = "request_identity_check"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def token(orchestrator_km: KeypairManager) -> CapabilityToken:
    return issue_token(
        orchestrator_km,
        agent_id=ACTOR_AGENT_ID,
        tool=_TOOL_NAME,
        scope={},
    )


@pytest.fixture()
def all_tokens(token: CapabilityToken) -> dict[str, CapabilityToken]:
    return {_TOOL_NAME: token}


def _success_check_fn(policy_number: str, dob_hint: str, ssn_last4: str):
    return {"verified": True, "outcome": "SUCCESS", "attempts_remaining": 3}


def _fail_check_fn(policy_number: str, dob_hint: str, ssn_last4: str):
    return {"verified": False, "outcome": "FAIL_MATCH", "attempts_remaining": 2}


def _lockout_check_fn(policy_number: str, dob_hint: str, ssn_last4: str):
    return {"verified": False, "outcome": "LOCKOUT", "attempts_remaining": 0}


def _not_found_check_fn(policy_number: str, dob_hint: str, ssn_last4: str):
    return {"verified": False, "outcome": "NOT_FOUND", "attempts_remaining": 2}


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _tool_block(name: str, input_: dict, block_id: str = "tu_001") -> MagicMock:
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


_CREDS = {"policy_number": "POL-001", "dob_hint": "1985-06-15", "ssn_last4": "1234"}


# ---------------------------------------------------------------------------
# IdentityEnvelope — dataclass contract
# ---------------------------------------------------------------------------


class TestIdentityEnvelope:
    def test_is_frozen(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        with pytest.raises((TypeError, AttributeError)):
            env.outcome = "changed"  # type: ignore[misc]

    def test_session_id_preserved(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            session_id="sess-77",
        )
        assert env.session_id == "sess-77"


# ---------------------------------------------------------------------------
# Outcome: SUCCESS → identity_verified
# ---------------------------------------------------------------------------


class TestOutcomeVerified:
    def test_outcome_identity_verified(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert env.outcome == "identity_verified"

    def test_attempts_remaining_on_success(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert env.attempts_remaining == 3

    def test_single_api_call_on_success(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Outcome: FAIL_MATCH → identity_failed
# ---------------------------------------------------------------------------


class TestOutcomeFailed:
    def test_outcome_identity_failed_on_fail_match(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_fail_check_fn,
            client=client,
        )
        assert env.outcome == "identity_failed"

    def test_attempts_remaining_on_fail(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_fail_check_fn,
            client=client,
        )
        assert env.attempts_remaining == 2

    def test_not_found_maps_to_identity_failed(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_not_found_check_fn,
            client=client,
        )
        assert env.outcome == "identity_failed"


# ---------------------------------------------------------------------------
# Outcome: LOCKOUT → identity_locked_out
# ---------------------------------------------------------------------------


class TestOutcomeLockedOut:
    def test_outcome_identity_locked_out(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_lockout_check_fn,
            client=client,
        )
        assert env.outcome == "identity_locked_out"

    def test_attempts_remaining_zero_on_lockout(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_lockout_check_fn,
            client=client,
        )
        assert env.attempts_remaining == 0


# ---------------------------------------------------------------------------
# Outcome: no tool call → identity_failed
# ---------------------------------------------------------------------------


class TestOutcomeNoToolCall:
    def test_end_turn_without_tool(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_text_block()], stop_reason="end_turn")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert env.outcome == "identity_failed"

    def test_no_tool_call_attempts_remaining_zero(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_text_block()], stop_reason="end_turn")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert env.attempts_remaining == 0


# ---------------------------------------------------------------------------
# Tool returns only verified + attempts_remaining to LLM (not vault data)
# ---------------------------------------------------------------------------


class TestPiiNeverInContext:
    def test_check_fn_called_with_correct_credentials(self, orchestrator_km, all_tokens):
        calls = []

        def spy_fn(policy_number, dob_hint, ssn_last4):
            calls.append((policy_number, dob_hint, ssn_last4))
            return {"verified": True, "outcome": "SUCCESS", "attempts_remaining": 3}

        creds = {"policy_number": "POL-007", "dob_hint": "1990-01-01", "ssn_last4": "9999"}
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, creds)], "tool_use")
        )
        run_identity_verifier_actor(
            **creds,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=spy_fn,
            client=client,
        )
        assert calls == [("POL-007", "1990-01-01", "9999")]

    def test_tool_result_content_has_only_verified_and_attempts(
        self, orchestrator_km, all_tokens
    ):
        """The content fed back to the LLM must contain ONLY verified + attempts_remaining."""
        import json as _json

        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        # The second messages.create call receives the tool result in messages
        second_call_kwargs = client.messages.create.call_args_list[0].kwargs
        messages = second_call_kwargs["messages"]
        # Last user message contains the tool result
        tool_result_msg = messages[-1]
        content = tool_result_msg["content"]
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_result":
                    parsed = _json.loads(item["content"])
                    keys = set(parsed.keys())
                    assert keys == {"verified", "attempts_remaining"}


# ---------------------------------------------------------------------------
# P4 capability token gate
# ---------------------------------------------------------------------------


class TestCapabilityTokenGate:
    def test_missing_token_audited_security_event(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens={},  # no token
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_missing_token_deny_reason(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert denied[0].kwargs["details"]["deny_reason"] == "no_token_issued"

    def test_missing_token_data_label_personal(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert denied[0].kwargs["data_label"] == "PERSONAL"

    def test_missing_token_outcome_identity_failed(self, orchestrator_km):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert env.outcome == "identity_failed"

    def test_forged_token_denied(self, orchestrator_km):
        audit = _audit_mock()
        attacker_km = KeypairManager.generate("orchestrator")
        forged = {
            _TOOL_NAME: issue_token(
                attacker_km, agent_id=ACTOR_AGENT_ID, tool=_TOOL_NAME, scope={}
            )
        }
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=forged,
            orchestrator_public_key=orchestrator_km.public_key_bytes,  # real key
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_scope_mismatch_denied(self, orchestrator_km):
        audit = _audit_mock()
        scoped = {
            _TOOL_NAME: issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool=_TOOL_NAME,
                scope={"policy_number": "POL-EXPECTED"},
            )
        }
        creds = {**_CREDS, "policy_number": "POL-OTHER"}
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, creds)], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        run_identity_verifier_actor(
            **creds,
            pre_issued_tokens=scoped,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_scope_match_allowed(self, orchestrator_km):
        scoped = {
            _TOOL_NAME: issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool=_TOOL_NAME,
                scope={"policy_number": "POL-001"},
            )
        }
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        env = run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=scoped,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        assert env.outcome == "identity_verified"


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_identity_decision_audited(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        actions = [c.kwargs["action"] for c in audit.call_args_list]
        assert "identity_decision" in actions

    def test_identity_decision_data_label_internal(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        decision = [c for c in audit.call_args_list if c.kwargs.get("action") == "identity_decision"]
        assert decision[0].kwargs["data_label"] == "INTERNAL"

    def test_identity_decision_not_security_event(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        decision = [c for c in audit.call_args_list if c.kwargs.get("action") == "identity_decision"]
        assert decision[0].kwargs["security_event"] is False

    def test_identity_decision_details_has_outcome(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        decision = [c for c in audit.call_args_list if c.kwargs.get("action") == "identity_decision"]
        assert "outcome" in decision[0].kwargs["details"]

    def test_identity_decision_details_has_attempts_remaining(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        decision = [c for c in audit.call_args_list if c.kwargs.get("action") == "identity_decision"]
        assert "attempts_remaining" in decision[0].kwargs["details"]

    def test_identity_decision_agent_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        decision = [c for c in audit.call_args_list if c.kwargs.get("action") == "identity_decision"]
        assert decision[0].kwargs["agent_id"] == ACTOR_AGENT_ID

    def test_identity_decision_target_is_session_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
            session_id="sess-id-test",
        )
        decision = [c for c in audit.call_args_list if c.kwargs.get("action") == "identity_decision"]
        assert decision[0].kwargs["target"] == "sess-id-test"

    def test_tool_call_ok_data_label_personal(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
            audit_fn=audit,
        )
        ok_calls = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_ok"]
        assert ok_calls[0].kwargs["data_label"] == "PERSONAL"

    def test_no_audit_fn_does_not_raise(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )


# ---------------------------------------------------------------------------
# API call shape
# ---------------------------------------------------------------------------


class TestApiCallShape:
    def test_uses_correct_model(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert kwargs["model"] == ACTOR_MODEL

    def test_temperature_is_zero(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert kwargs["temperature"] == 0

    def test_tools_list_has_one_tool(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert len(kwargs["tools"]) == 1
        assert kwargs["tools"][0]["name"] == _TOOL_NAME

    def test_credentials_in_user_message(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        messages = kwargs["messages"]
        user_msgs = [m for m in messages if m["role"] == "user"]
        content = " ".join(
            m["content"] if isinstance(m["content"], str) else str(m["content"])
            for m in user_msgs
        )
        assert "POL-001" in content

    def test_system_prompt_present(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        run_identity_verifier_actor(
            **_CREDS,
            pre_issued_tokens=all_tokens,
            orchestrator_public_key=orchestrator_km.public_key_bytes,
            identity_check_fn=_success_check_fn,
            client=client,
        )
        _, kwargs = client.messages.create.call_args
        assert "system" in kwargs
        assert len(kwargs["system"]) > 0


# ---------------------------------------------------------------------------
# Unwired identity_check_fn raises RuntimeError
# ---------------------------------------------------------------------------


class TestUnwiredCheckFn:
    def test_default_fn_raises_runtime_error(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response([_tool_block(_TOOL_NAME, _CREDS)], "tool_use")
        )
        with pytest.raises(RuntimeError, match="not wired"):
            run_identity_verifier_actor(
                **_CREDS,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                # identity_check_fn intentionally omitted
                client=client,
            )


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
            run_identity_verifier_actor(
                **_CREDS,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                identity_check_fn=_success_check_fn,
                client=client,
            )

    def test_api_error_no_audit(self, orchestrator_km, all_tokens):
        import anthropic as _anthropic

        audit = _audit_mock()
        client = MagicMock()
        client.messages.create.side_effect = _anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(_anthropic.APIConnectionError):
            run_identity_verifier_actor(
                **_CREDS,
                pre_issued_tokens=all_tokens,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                identity_check_fn=_success_check_fn,
                client=client,
                audit_fn=audit,
            )
        audit.assert_not_called()
