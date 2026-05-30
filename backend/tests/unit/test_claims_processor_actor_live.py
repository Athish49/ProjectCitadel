"""Unit tests for run_claims_processor_actor (Sprint 4.1.6).

All tests mock the Anthropic client — no live API calls.
All P4 tests use real Ed25519 key material.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from agent_system.actors.claims_processor_actor import (
    ACTOR_AGENT_ID,
    ACTOR_MODEL,
    MAX_LOOP_ITERATIONS,
    ProcessorEnvelope,
    run_claims_processor_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import CapabilityToken, issue_token
from agent_system.tools.implementations.claims_tools import (
    classify_damage,
    lookup_coverage,
    score_fraud,
)

pytestmark = pytest.mark.unit

_CID = "clm-test-001"
_EREF = "ev-test-001"

# Precompute expected envelope fields from deterministic stub functions.
_EXPECTED_DAMAGE = classify_damage(_EREF).value["damage_label"]
_expected_cov = lookup_coverage(_CID).value
_EXPECTED_COV_CALC = (
    f"{_expected_cov['policy_type'].lower()}_"
    f"{'applicable' if _expected_cov['coverage_applicable'] else 'not_applicable'}"
)
_EXPECTED_FRAUD = score_fraud(_CID).value["decision"]


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
        for t in (
            "classify_damage", "lookup_coverage", "score_fraud",
            "search_policy_docs", "search_fraud_rules",
        )
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


def _all_tool_blocks() -> list:
    return [
        _tool_block("classify_damage", {"evidence_ref": _EREF}, "tu_cd"),
        _tool_block("lookup_coverage", {"claim_id": _CID}, "tu_lc"),
        _tool_block("score_fraud", {"claim_id": _CID}, "tu_sf"),
        _tool_block("search_policy_docs", {"query": "vehicle damage coverage policy"}, "tu_spd"),
    ]


def _run_actor(
    orchestrator_km,
    tokens,
    client,
    *,
    session_id: str = "sess-test",
    audit_fn=None,
) -> ProcessorEnvelope:
    return run_claims_processor_actor(
        claim_id=_CID,
        evidence_ref=_EREF,
        pre_issued_tokens=tokens,
        orchestrator_public_key=orchestrator_km.public_key_bytes,
        client=client,
        session_id=session_id,
        audit_fn=audit_fn,
    )


# ---------------------------------------------------------------------------
# ProcessorEnvelope — dataclass contract
# ---------------------------------------------------------------------------


class TestProcessorEnvelope:
    def test_is_frozen(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        with pytest.raises((TypeError, AttributeError)):
            env.damage_assessment = "changed"  # type: ignore[misc]

    def test_session_id_preserved(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client, session_id="sess-77")
        assert env.session_id == "sess-77"

    def test_claim_id_preserved(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.claim_id == _CID


# ---------------------------------------------------------------------------
# Happy path — all 4 tools called in one turn
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_damage_assessment_from_tool(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.damage_assessment == _EXPECTED_DAMAGE

    def test_coverage_calculation_from_tool(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.coverage_calculation == _EXPECTED_COV_CALC

    def test_fraud_signal_from_tool(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.fraud_signal == _EXPECTED_FRAUD

    def test_fraud_signal_is_valid_value(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.fraud_signal in {"CLEAR", "FLAG", "DENY"}

    def test_two_api_calls_for_one_tool_turn(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        assert client.messages.create.call_count == 2

    def test_coverage_calculation_has_applicable_suffix(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.coverage_calculation.endswith("_applicable") or env.coverage_calculation.endswith(
            "_not_applicable"
        )


# ---------------------------------------------------------------------------
# P10 — SECRET filter: score_fraud sends only {decision} to LLM
# ---------------------------------------------------------------------------


class TestP10SecretFilter:
    def _get_tool_results(self, client):
        # Second API call messages: [user_msg, assistant_msg, user_tool_results]
        second_call_msgs = client.messages.create.call_args_list[1].kwargs["messages"]
        return second_call_msgs[-1]["content"]

    def test_score_fraud_tool_result_has_only_decision(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results(client)
        sf_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sf")
        parsed = json.loads(sf_result["content"])
        assert set(parsed.keys()) == {"decision"}

    def test_risk_score_not_in_llm_context(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results(client)
        sf_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sf")
        parsed = json.loads(sf_result["content"])
        assert "risk_score" not in parsed

    def test_risk_factors_not_in_llm_context(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results(client)
        sf_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sf")
        parsed = json.loads(sf_result["content"])
        assert "risk_factors" not in parsed

    def test_decision_value_is_valid(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results(client)
        sf_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sf")
        parsed = json.loads(sf_result["content"])
        assert parsed["decision"] in {"CLEAR", "FLAG", "DENY"}

    def test_classify_damage_result_has_full_content(self, orchestrator_km, all_tokens):
        """Non-SECRET tools send full inner dict to LLM (not stripped)."""
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results(client)
        cd_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_cd")
        parsed = json.loads(cd_result["content"])
        assert "damage_label" in parsed
        assert "confidence" in parsed

    def test_lookup_coverage_result_has_policy_type(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results(client)
        lc_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_lc")
        parsed = json.loads(lc_result["content"])
        assert "policy_type" in parsed


# ---------------------------------------------------------------------------
# Fallback / fail-closed defaults
# ---------------------------------------------------------------------------


class TestFallbackDefaults:
    def test_no_tool_calls_damage_unknown(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.damage_assessment == "unknown"

    def test_no_tool_calls_coverage_unknown(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.coverage_calculation == "unknown"

    def test_no_tool_calls_fraud_signal_flag(self, orchestrator_km, all_tokens):
        """Fail-closed: missing score_fraud → FLAG → ESCALATED downstream."""
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.fraud_signal == "FLAG"

    def test_missing_score_fraud_defaults_to_flag(self, orchestrator_km, all_tokens):
        """classify_damage + lookup_coverage called; score_fraud absent → FLAG."""
        client = _mock_client(
            _response([
                _tool_block("classify_damage", {"evidence_ref": _EREF}, "tu_cd"),
                _tool_block("lookup_coverage", {"claim_id": _CID}, "tu_lc"),
            ], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.fraud_signal == "FLAG"
        assert env.damage_assessment == _EXPECTED_DAMAGE
        assert env.coverage_calculation == _EXPECTED_COV_CALC

    def test_end_turn_immediately_returns_envelope(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert isinstance(env, ProcessorEnvelope)

    def test_one_api_call_on_immediate_end_turn(self, orchestrator_km, all_tokens):
        client = _mock_client(_response([_text_block()], "end_turn"))
        _run_actor(orchestrator_km, all_tokens, client)
        assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Multi-turn loop — tools spread across iterations
# ---------------------------------------------------------------------------


class TestMultiTurnLoop:
    def test_tools_across_two_turns(self, orchestrator_km, all_tokens):
        """classify_damage in turn 1; lookup_coverage + score_fraud in turn 2."""
        client = _mock_client(
            _response([
                _tool_block("classify_damage", {"evidence_ref": _EREF}, "tu_cd"),
            ], "tool_use"),
            _response([
                _tool_block("lookup_coverage", {"claim_id": _CID}, "tu_lc"),
                _tool_block("score_fraud", {"claim_id": _CID}, "tu_sf"),
            ], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert env.damage_assessment == _EXPECTED_DAMAGE
        assert env.fraud_signal == _EXPECTED_FRAUD
        assert client.messages.create.call_count == 3

    def test_max_iterations_terminates_loop(self, orchestrator_km, all_tokens):
        """Loop must not exceed MAX_LOOP_ITERATIONS even if LLM never ends."""
        repeated = _response(
            [_tool_block("classify_damage", {"evidence_ref": _EREF})], "tool_use"
        )
        client = _mock_client(*([repeated] * (MAX_LOOP_ITERATIONS + 5)))
        env = _run_actor(orchestrator_km, all_tokens, client)
        assert client.messages.create.call_count == MAX_LOOP_ITERATIONS
        assert isinstance(env, ProcessorEnvelope)


# ---------------------------------------------------------------------------
# P4 capability token gate
# ---------------------------------------------------------------------------


class TestCapabilityTokenGate:
    def test_missing_token_audited_as_security_event(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": _EREF})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, {}, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_missing_token_deny_reason(self, orchestrator_km):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": _EREF})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, {}, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert denied[0].kwargs["details"]["deny_reason"] == "no_token_issued"

    def test_missing_token_still_returns_envelope(self, orchestrator_km):
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": _EREF})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, {}, client)
        assert isinstance(env, ProcessorEnvelope)

    def test_missing_token_damage_unknown(self, orchestrator_km):
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": _EREF})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, {}, client)
        assert env.damage_assessment == "unknown"

    def test_forged_token_denied(self, orchestrator_km):
        audit = _audit_mock()
        attacker_km = KeypairManager.generate("orchestrator")
        forged = {
            "classify_damage": issue_token(
                attacker_km, agent_id=ACTOR_AGENT_ID, tool="classify_damage", scope={}
            )
        }
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": _EREF})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, forged, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_scope_mismatch_denied(self, orchestrator_km):
        audit = _audit_mock()
        scoped = {
            "classify_damage": issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool="classify_damage",
                scope={"evidence_ref": "ev-EXPECTED"},
            )
        }
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": "ev-WRONG"})], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, scoped, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True

    def test_scope_match_allows_call(self, orchestrator_km):
        scoped = {
            "classify_damage": issue_token(
                orchestrator_km,
                agent_id=ACTOR_AGENT_ID,
                tool="classify_damage",
                scope={"evidence_ref": _EREF},
            ),
            "lookup_coverage": issue_token(
                orchestrator_km, agent_id=ACTOR_AGENT_ID, tool="lookup_coverage", scope={}
            ),
            "score_fraud": issue_token(
                orchestrator_km, agent_id=ACTOR_AGENT_ID, tool="score_fraud", scope={}
            ),
            "search_policy_docs": issue_token(
                orchestrator_km, agent_id=ACTOR_AGENT_ID, tool="search_policy_docs", scope={}
            ),
        }
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        env = _run_actor(orchestrator_km, scoped, client)
        assert env.damage_assessment == _EXPECTED_DAMAGE


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    def test_processor_assessment_audited(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        actions = [c.kwargs["action"] for c in audit.call_args_list]
        assert "processor_assessment" in actions

    def test_processor_assessment_stub_is_false(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert pa[0].kwargs["details"]["stub"] is False

    def test_processor_assessment_agent_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert pa[0].kwargs["agent_id"] == ACTOR_AGENT_ID

    def test_processor_assessment_target_is_session_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, session_id="sess-audit-42", audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert pa[0].kwargs["target"] == "sess-audit-42"

    def test_processor_assessment_data_label_confidential(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert pa[0].kwargs["data_label"] == "CONFIDENTIAL"

    def test_processor_assessment_not_security_event(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert pa[0].kwargs["security_event"] is False

    def test_processor_assessment_details_has_claim_id(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert pa[0].kwargs["details"]["claim_id"] == _CID

    def test_processor_assessment_details_has_fraud_signal(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert "fraud_signal" in pa[0].kwargs["details"]

    def test_tool_call_ok_audited_on_successful_dispatch(self, orchestrator_km, all_tokens):
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("classify_damage", {"evidence_ref": _EREF}, "tu_cd")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        ok_calls = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_ok"]
        assert len(ok_calls) >= 1

    def test_no_audit_fn_does_not_raise(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)


# ---------------------------------------------------------------------------
# API call shape
# ---------------------------------------------------------------------------


class TestApiCallShape:
    def test_uses_correct_model(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert kwargs["model"] == ACTOR_MODEL

    def test_temperature_is_zero(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert kwargs["temperature"] == 0

    def test_tools_list_has_five_tools(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert len(kwargs["tools"]) == 5

    def test_tool_names_correct(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        tool_names = {t["name"] for t in kwargs["tools"]}
        assert tool_names == {
            "classify_damage", "lookup_coverage", "score_fraud",
            "search_policy_docs", "search_fraud_rules",
        }

    def test_system_prompt_present(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        assert "system" in kwargs
        assert len(kwargs["system"]) > 0

    def test_claim_id_in_user_message(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
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

    def test_evidence_ref_in_user_message(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        kwargs = client.messages.create.call_args_list[0].kwargs
        user_content = " ".join(
            m["content"] if isinstance(m["content"], str) else str(m["content"])
            for m in kwargs["messages"]
            if m["role"] == "user"
        )
        assert _EREF in user_content


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

    def test_api_error_no_assessment_audit(self, orchestrator_km, all_tokens):
        import anthropic as _anthropic

        audit = _audit_mock()
        client = MagicMock()
        client.messages.create.side_effect = _anthropic.APIConnectionError(
            request=MagicMock()
        )
        with pytest.raises(_anthropic.APIConnectionError):
            _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        pa = [c for c in audit.call_args_list if c.kwargs.get("action") == "processor_assessment"]
        assert len(pa) == 0


# ---------------------------------------------------------------------------
# P3 — search_fraud_rules SECRET text stripping
# ---------------------------------------------------------------------------


class TestSearchFraudRulesSecretFilter:
    """P3 guard: search_fraud_rules returns SECRET-labeled chunks.

    The actor must strip the `text` field from each chunk before the result
    is forwarded to the LLM, exposing only rule references (doc_id, source,
    score, data_label). This mirrors the score_fraud pattern.
    """

    def _get_tool_results_for_call(self, client, call_index: int = 1):
        """Return the tool_results list from the (call_index+1)th API call."""
        msgs = client.messages.create.call_args_list[call_index].kwargs["messages"]
        return msgs[-1]["content"]

    def test_search_fraud_rules_in_tools_list(self, orchestrator_km, all_tokens):
        client = _mock_client(
            _response(_all_tool_blocks(), "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_names = {
            t["name"]
            for t in client.messages.create.call_args_list[0].kwargs["tools"]
        }
        assert "search_fraud_rules" in tool_names

    def test_search_fraud_rules_token_accepted(self, orchestrator_km, all_tokens):
        """Token issued to claims_processor for search_fraud_rules must not be denied."""
        audit = _audit_mock()
        client = _mock_client(
            _response([_tool_block("search_fraud_rules", {"query": "staged accident"}, "tu_sfr")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) == 0

    def test_chunk_text_stripped_from_llm_context(self, orchestrator_km, all_tokens):
        """SECRET chunk text must not appear in the tool result sent to the LLM."""
        client = _mock_client(
            _response([_tool_block("search_fraud_rules", {"query": "staged accident"}, "tu_sfr")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results_for_call(client, 1)
        sfr_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sfr")
        parsed = json.loads(sfr_result["content"])
        for chunk in parsed.get("chunks", []):
            assert "text" not in chunk, "SECRET fraud rule text must not reach the LLM"

    def test_chunk_references_preserved(self, orchestrator_km, all_tokens):
        """doc_id, source, score, data_label must survive stripping."""
        client = _mock_client(
            _response([_tool_block("search_fraud_rules", {"query": "staged accident"}, "tu_sfr")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results_for_call(client, 1)
        sfr_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sfr")
        parsed = json.loads(sfr_result["content"])
        chunks = parsed.get("chunks", [])
        assert len(chunks) > 0
        for chunk in chunks:
            assert "doc_id" in chunk
            assert "source" in chunk
            assert "score" in chunk

    def test_query_field_preserved(self, orchestrator_km, all_tokens):
        """Top-level query field must be present so LLM can correlate the search."""
        client = _mock_client(
            _response([_tool_block("search_fraud_rules", {"query": "glass staging"}, "tu_sfr")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, all_tokens, client)
        tool_results = self._get_tool_results_for_call(client, 1)
        sfr_result = next(r for r in tool_results if r.get("tool_use_id") == "tu_sfr")
        parsed = json.loads(sfr_result["content"])
        assert "query" in parsed

    def test_search_fraud_rules_missing_token_denied(self, orchestrator_km):
        """No token for search_fraud_rules → security event, same as other tools."""
        audit = _audit_mock()
        # Provide tokens for everything except search_fraud_rules.
        tokens = {
            t: issue_token(orchestrator_km, agent_id=ACTOR_AGENT_ID, tool=t, scope={})
            for t in ("classify_damage", "lookup_coverage", "score_fraud", "search_policy_docs")
        }
        client = _mock_client(
            _response([_tool_block("search_fraud_rules", {"query": "staged accident"}, "tu_sfr")], "tool_use"),
            _response([_text_block()], "end_turn"),
        )
        _run_actor(orchestrator_km, tokens, client, audit_fn=audit)
        denied = [c for c in audit.call_args_list if c.kwargs.get("action") == "tool_call_denied"]
        assert len(denied) >= 1
        assert denied[0].kwargs["security_event"] is True
