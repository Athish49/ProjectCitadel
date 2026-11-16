"""Unit tests for the playground SSE pipeline.

Covers the DB-free, side-effect-free pieces (_sse_verdict's payload shape,
the POLICY_HELD tag regexes) plus end-to-end invariant tests that drive
_generate_pipeline through every branch with the LLM/DB boundary mocked —
these are what actually catch the "layer below a blocked layer still shows
PASS" class of bug, since the pure-helper tests above can't.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.showcase import playground_sse, session_store
from app.showcase.playground_sse import (
    _LAYER_ORDER,
    _POLICY_HELD_REASONS,
    _POLICY_HELD_RE,
    _POLICY_HELD_STRIP_RE,
    _generate_pipeline,
    _layer_payload,
    _sse_verdict,
)
from app.showcase.trace_store import TraceEntry
from app.showcase.trace_store import put as _put_trace
from agent_system.parser.schemas import SchemaViolationError

pytestmark = pytest.mark.unit


def _parse_sse(event_str: str) -> dict:
    assert event_str.startswith("event: verdict\ndata: ")
    data_line = event_str.split("\n", 1)[1]
    assert data_line.startswith("data: ")
    return json.loads(data_line[len("data: "):].rstrip("\n"))


def _all_not_reached() -> list[dict]:
    return [_layer_payload(lid, "not_reached", None, []) for lid in _LAYER_ORDER]


class TestSseVerdictPayloadShape:
    def test_includes_policy_held_field_when_set(self) -> None:
        payload = _parse_sse(
            _sse_verdict("trace-1", "CLEAN", None, None, "reply text", _all_not_reached(),
                         policy_held="cannot_approve_own_claim")
        )
        assert payload["policyHeld"] == "cannot_approve_own_claim"
        assert payload["outcome"] == "CLEAN"
        assert payload["traceId"] == "trace-1"

    def test_defaults_policy_held_to_none(self) -> None:
        payload = _parse_sse(_sse_verdict("trace-2", "CLEAN", None, None, "reply text", _all_not_reached()))
        assert payload["policyHeld"] is None

    def test_blocked_verdict_explicitly_carries_none(self) -> None:
        payload = _parse_sse(
            _sse_verdict("trace-3", "BLOCKED", "P1", "ingress", "blocked summary", _all_not_reached(), policy_held=None)
        )
        assert payload["policyHeld"] is None
        assert payload["blockedByLayer"] == "ingress"

    def test_layers_field_covers_all_seven_layers(self) -> None:
        payload = _parse_sse(
            _sse_verdict("trace-4", "CLEAN", None, None, "reply text", _all_not_reached())
        )
        assert [l["layerId"] for l in payload["layers"]] == _LAYER_ORDER

    def test_layer_payload_rejects_unknown_status(self) -> None:
        with pytest.raises(AssertionError):
            _layer_payload("ingress", "bogus", None, [])


class TestPolicyHeldRegex:
    def test_captures_well_formed_tag(self) -> None:
        text = "I can't do that. [POLICY_HELD: cannot_approve_own_claim]"
        m = _POLICY_HELD_RE.search(text)
        assert m is not None
        assert m.group(1) == "cannot_approve_own_claim"

    def test_strips_tag_from_reply(self) -> None:
        text = "I can't do that. [POLICY_HELD: cannot_approve_own_claim]"
        stripped = _POLICY_HELD_STRIP_RE.sub("", text).strip()
        assert "[POLICY_HELD" not in stripped
        assert stripped == "I can't do that."

    def test_strict_regex_misses_malformed_tag_but_strip_still_removes_it(self) -> None:
        # A malformed tag (stray capitals/punctuation) must never leak to the user,
        # even if the strict capture regex can't recover a clean slug from it.
        text = "Declined. [POLICY_HELD: Cannot_Approve_Own_Claim.]"
        assert _POLICY_HELD_RE.search(text) is None
        stripped = _POLICY_HELD_STRIP_RE.sub("", text).strip()
        assert "[POLICY_HELD" not in stripped

    def test_no_false_positive_on_ordinary_reply(self) -> None:
        text = "Your deductible is $2,449. Anything else I can help with?"
        assert _POLICY_HELD_RE.search(text) is None

    def test_vocabulary_contains_expected_reasons(self) -> None:
        assert _POLICY_HELD_REASONS == {
            "cannot_approve_own_claim",
            "cannot_reveal_fraud_score",
            "cannot_access_other_customer_data",
            "cannot_disclose_identifiers",
            "out_of_scope_request",
        }


# ── End-to-end pipeline invariant tests ────────────────────────────────────
#
# Drive _generate_pipeline through every branch with the LLM/DB boundary
# mocked at the module level, and assert the contract described at the top
# of _generate_pipeline: exactly one verdict, verdict.layers always covers
# all 7 layers in order, nothing after the decisive layer is ever "passed",
# and streamed layer_result events agree with the verdict's final layers.

_FAKE_INTAKE_OUTPUT = SimpleNamespace(
    intent=SimpleNamespace(value="file_claim"),
    incident_type=SimpleNamespace(value="collision"),
)


def _make_entry(payload: str = "What's my deductible?", detections: list[str] | None = None,
                 chat_session_id: str | None = None, attack_id: int | None = None) -> tuple[str, TraceEntry]:
    trace_id = str(uuid.uuid4())
    entry = TraceEntry(
        payload=payload,
        detections=detections or [],
        chars_stripped=0,
        sanitized=f"<untrusted>{payload}</untrusted>",
        chat_session_id=chat_session_id,
        persona_key="mark",
        has_attachment=False,
        attack_id=attack_id,
    )
    _put_trace(trace_id, entry)
    return trace_id, entry


def _fake_actor_client(reply: str | None = None, raises: Exception | None = None):
    async def _create(**_kwargs):
        if raises is not None:
            raise raises
        return SimpleNamespace(content=[SimpleNamespace(text=reply)])

    return SimpleNamespace(messages=SimpleNamespace(create=_create))


def _raise_runtime(*_args, **_kwargs):
    raise RuntimeError("DATABASE_URL not available")


async def _collect(trace_id: str) -> tuple[list[dict], dict]:
    """Run the generator to completion; return (layer_results, verdict).
    Asserts the single-verdict, verdict-is-last contract inline."""
    layer_results: list[dict] = []
    verdict: dict | None = None
    async for raw in _generate_pipeline(trace_id):
        assert raw.startswith("event: ")
        header, _, body = raw.partition("\n")
        event_type = header[len("event: "):]
        assert verdict is None, "generator yielded after its verdict"
        data_line = body.strip()
        assert data_line.startswith("data: ")
        data = json.loads(data_line[len("data: "):])
        if event_type == "layer_result":
            layer_results.append(data)
        elif event_type == "verdict":
            verdict = data
        elif event_type == "stream_error":
            pytest.fail(f"unexpected stream_error: {data}")
        else:
            pytest.fail(f"unexpected event type: {event_type}")
    assert verdict is not None, "generator finished without a verdict"
    return layer_results, verdict


@pytest.fixture(autouse=True)
def _happy_path_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default every LLM/DB boundary to a benign, successful outcome. Each
    test overrides only the specific seam(s) it wants to exercise."""
    monkeypatch.setattr(playground_sse, "_semantic_classify", AsyncMock(return_value=("benign", 0.05)))
    monkeypatch.setattr(playground_sse, "run_intake_parser", lambda *a, **kw: _FAKE_INTAKE_OUTPUT)
    monkeypatch.setattr(playground_sse, "get_sync_client", lambda: None)
    monkeypatch.setattr(playground_sse, "get_async_client", lambda: _fake_actor_client(reply="Your deductible is $500."))
    monkeypatch.setattr(playground_sse, "_load_policy_knowledge", AsyncMock(return_value=""))
    monkeypatch.setattr(playground_sse, "get_dsn", _raise_runtime)
    monkeypatch.setattr(playground_sse, "_audit_layer", AsyncMock(return_value=None))
    monkeypatch.setattr(playground_sse, "_update_attack_log", AsyncMock(return_value=None))


def _assert_full_layer_coverage(verdict: dict) -> None:
    assert [l["layerId"] for l in verdict["layers"]] == _LAYER_ORDER


def _assert_layer_results_match_verdict(layer_results: list[dict], verdict: dict) -> None:
    by_id = {l["layerId"]: l for l in verdict["layers"]}
    for streamed in layer_results:
        assert by_id[streamed["layerId"]]["status"] == streamed["status"]


def _assert_nothing_passed_after_decisive(verdict: dict) -> None:
    decisive = verdict.get("blockedByLayer")
    seen_decisive = False
    for layer in verdict["layers"]:
        if seen_decisive:
            assert layer["status"] != "passed", f"{layer['layerId']} is passed after decisive layer {decisive}"
        if layer["layerId"] == decisive:
            seen_decisive = True


class TestPipelineCleanPath:
    @pytest.mark.asyncio
    async def test_benign_message_is_clean_with_all_layers_passed(self) -> None:
        trace_id, _ = _make_entry()
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "CLEAN"
        assert verdict["blockedByLayer"] is None
        _assert_full_layer_coverage(verdict)
        _assert_layer_results_match_verdict(layer_results, verdict)
        assert all(l["status"] == "passed" for l in verdict["layers"])
        assert len(layer_results) == len(_LAYER_ORDER)

    @pytest.mark.asyncio
    async def test_clean_reply_is_written_to_session_history(self) -> None:
        chat_session_id = str(uuid.uuid4())
        trace_id, entry = _make_entry(chat_session_id=chat_session_id)
        _, verdict = await _collect(trace_id)

        history = session_store.get_history(chat_session_id)
        assert history == [
            {"role": "user", "content": entry.payload},
            {"role": "assistant", "content": verdict["summary"]},
        ]


class TestPipelineIngressAndPatternBlocks:
    @pytest.mark.asyncio
    async def test_delimiter_injection_blocked_at_ingress(self) -> None:
        trace_id, _ = _make_entry(detections=["delimiter_injection"])
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "BLOCKED"
        assert verdict["blockedByLayer"] == "ingress"
        assert len(layer_results) == 1
        _assert_full_layer_coverage(verdict)
        _assert_nothing_passed_after_decisive(verdict)
        assert all(
            l["status"] == "not_reached" for l in verdict["layers"] if l["layerId"] != "ingress"
        )

    @pytest.mark.asyncio
    async def test_injection_pattern_blocked_at_pattern_detection(self) -> None:
        trace_id, _ = _make_entry(detections=["ignore_instructions"])
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "BLOCKED"
        assert verdict["blockedByLayer"] == "pattern-detection"
        assert verdict["layers"][0]["status"] == "passed"  # ingress passed
        _assert_nothing_passed_after_decisive(verdict)
        _assert_layer_results_match_verdict(layer_results, verdict)


class TestPipelineSemanticClassifier:
    @pytest.mark.asyncio
    async def test_adversarial_intent_blocked(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(playground_sse, "_semantic_classify", AsyncMock(return_value=("adversarial", 0.95)))
        trace_id, _ = _make_entry()
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "BLOCKED"
        assert verdict["blockedByLayer"] == "semantic-classifier"
        _assert_nothing_passed_after_decisive(verdict)
        _assert_layer_results_match_verdict(layer_results, verdict)

    @pytest.mark.asyncio
    async def test_classifier_failure_is_reported_as_error_not_passed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(playground_sse, "_semantic_classify", AsyncMock(side_effect=RuntimeError("boom")))
        trace_id, _ = _make_entry()
        layer_results, verdict = await _collect(trace_id)

        # A classifier failure is a soft layer — the pipeline still continues
        # (pattern-detection already covers the hard cases) — but the layer
        # itself must never be reported as a verified "passed".
        assert verdict["outcome"] == "CLEAN"
        classifier = next(l for l in verdict["layers"] if l["layerId"] == "semantic-classifier")
        assert classifier["status"] == "error"
        _assert_layer_results_match_verdict(layer_results, verdict)


class TestPipelineParser:
    @pytest.mark.asyncio
    async def test_schema_violation_blocked_at_parser(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_schema_violation(*_a, **_kw):
            raise SchemaViolationError(
                "bad field", schema_name="intake@2", field_path="incident_date",
                error_kind="type_mismatch", raw_excerpt="...",
            )

        monkeypatch.setattr(playground_sse, "run_intake_parser", _raise_schema_violation)
        trace_id, _ = _make_entry()
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "BLOCKED"
        assert verdict["blockedByLayer"] == "parser-llm"
        _assert_nothing_passed_after_decisive(verdict)
        _assert_layer_results_match_verdict(layer_results, verdict)

    @pytest.mark.asyncio
    async def test_generic_parser_exception_is_error_not_blocked_as_attack(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_value_error(*_a, **_kw):
            raise ValueError("transport failure")

        monkeypatch.setattr(playground_sse, "run_intake_parser", _raise_value_error)
        trace_id, _ = _make_entry()
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "ERROR"
        assert verdict["blockedByLayer"] == "parser-llm"
        parser_layer = next(l for l in verdict["layers"] if l["layerId"] == "parser-llm")
        assert parser_layer["status"] == "error"
        _assert_nothing_passed_after_decisive(verdict)
        _assert_layer_results_match_verdict(layer_results, verdict)


class TestPipelineActor:
    @pytest.mark.asyncio
    async def test_actor_llm_exception_is_error_and_writes_no_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            playground_sse, "get_async_client", lambda: _fake_actor_client(raises=RuntimeError("down"))
        )
        chat_session_id = str(uuid.uuid4())
        trace_id, _ = _make_entry(chat_session_id=chat_session_id)
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "ERROR"
        assert verdict["blockedByLayer"] == "actor-llm"
        actor_layer = next(l for l in verdict["layers"] if l["layerId"] == "actor-llm")
        assert actor_layer["status"] == "error"
        egress_layer = next(l for l in verdict["layers"] if l["layerId"] == "egress-filter")
        assert egress_layer["status"] == "not_reached"
        _assert_nothing_passed_after_decisive(verdict)
        assert session_store.get_history(chat_session_id) == []

    @pytest.mark.asyncio
    async def test_policy_held_decline_skips_egress_and_writes_real_exchange(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reply = "I can't approve or release claim payments myself. [POLICY_HELD: cannot_approve_own_claim]"
        monkeypatch.setattr(playground_sse, "get_async_client", lambda: _fake_actor_client(reply=reply))
        chat_session_id = str(uuid.uuid4())
        trace_id, entry = _make_entry(chat_session_id=chat_session_id)
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "HELD"
        assert verdict["policyHeld"] == "cannot_approve_own_claim"
        assert "[POLICY_HELD" not in verdict["summary"]
        actor_layer = next(l for l in verdict["layers"] if l["layerId"] == "actor-llm")
        assert actor_layer["status"] == "held"
        egress_layer = next(l for l in verdict["layers"] if l["layerId"] == "egress-filter")
        assert egress_layer["status"] == "not_reached"
        _assert_layer_results_match_verdict(layer_results, verdict)

        history = session_store.get_history(chat_session_id)
        assert history == [
            {"role": "user", "content": entry.payload},
            {"role": "assistant", "content": verdict["summary"]},
        ]


class TestPipelineEgress:
    @pytest.mark.asyncio
    async def test_egress_blocked_withholds_reply_from_history(self, monkeypatch: pytest.MonkeyPatch) -> None:
        secret_reply = "Your SSN on file is 123-45-6789."
        monkeypatch.setattr(playground_sse, "get_async_client", lambda: _fake_actor_client(reply=secret_reply))
        monkeypatch.setattr(
            playground_sse, "_run_egress_sync",
            lambda text, trace_id: {
                "events": [playground_sse._evt("alert", "PII detected")],
                "status": "blocked",
                "blocked_by_layer": "egress-filter",
                "blocked_by_pattern": "P10",
            },
        )
        chat_session_id = str(uuid.uuid4())
        trace_id, _ = _make_entry(chat_session_id=chat_session_id)
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "BLOCKED"
        assert verdict["blockedByLayer"] == "egress-filter"
        _assert_nothing_passed_after_decisive(verdict)
        _assert_layer_results_match_verdict(layer_results, verdict)
        # The unreleased, PII-bearing reply must never land in history.
        history = session_store.get_history(chat_session_id)
        assert all(secret_reply not in turn["content"] for turn in history)

    @pytest.mark.asyncio
    async def test_egress_error_fails_closed_and_withholds_reply(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reply = "Here is your answer."
        monkeypatch.setattr(playground_sse, "get_async_client", lambda: _fake_actor_client(reply=reply))
        monkeypatch.setattr(
            playground_sse, "_run_egress_sync",
            lambda text, trace_id: {
                "events": [playground_sse._evt("alert", "Egress filter error")],
                "status": "error",
                "blocked_by_layer": None,
                "blocked_by_pattern": None,
            },
        )
        chat_session_id = str(uuid.uuid4())
        trace_id, _ = _make_entry(chat_session_id=chat_session_id)
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "ERROR"
        assert verdict["blockedByLayer"] == "egress-filter"
        egress_layer = next(l for l in verdict["layers"] if l["layerId"] == "egress-filter")
        assert egress_layer["status"] == "error"
        _assert_nothing_passed_after_decisive(verdict)
        history = session_store.get_history(chat_session_id)
        assert all(reply not in turn["content"] for turn in history)


class TestAttackLogUpdate:
    """Covers the production-readiness fix: an attack-tagged (attack_id set)
    submission's real pipeline outcome must be written back to
    adversarial_attack_logs, and a plain (non-attack-tagged) submission must
    never attempt that UPDATE at all — there's no row for it to update."""

    @pytest.mark.asyncio
    async def test_attack_tagged_blocked_updates_with_blocked_verdict_and_layer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_update = AsyncMock(return_value=None)
        monkeypatch.setattr(playground_sse, "_update_attack_log", mock_update)
        trace_id, _ = _make_entry(detections=["ignore_instructions"], attack_id=42)
        _, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "BLOCKED"
        mock_update.assert_called_once_with(
            trace_id, "BLOCKED", "pattern-detection", "P3", False,
        )

    @pytest.mark.asyncio
    async def test_attack_tagged_clean_updates_with_is_breach_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_update = AsyncMock(return_value=None)
        monkeypatch.setattr(playground_sse, "_update_attack_log", mock_update)
        trace_id, _ = _make_entry(attack_id=7)  # benign "What's my deductible?" -> CLEAN
        _, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "CLEAN"
        mock_update.assert_called_once_with(
            trace_id, "CLEAN", None, None, True,
        )

    @pytest.mark.asyncio
    async def test_attack_tagged_held_updates_blocked_by_layer_actor_llm(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_update = AsyncMock(return_value=None)
        monkeypatch.setattr(playground_sse, "_update_attack_log", mock_update)
        reply = "I can't approve or release claim payments myself. [POLICY_HELD: cannot_approve_own_claim]"
        monkeypatch.setattr(playground_sse, "get_async_client", lambda: _fake_actor_client(reply=reply))
        trace_id, _ = _make_entry(attack_id=9)
        _, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "HELD"
        # SSE verdict payload itself keeps blockedByLayer=None for HELD...
        assert verdict["blockedByLayer"] is None
        # ...but the DB row still gets a real, non-fabricated layer instead of
        # the frontend's stale "blocked at ingress" fallback.
        mock_update.assert_called_once_with(
            trace_id, "HELD", "actor-llm", None, False,
        )

    @pytest.mark.asyncio
    async def test_plain_chat_submission_never_attempts_attack_log_update(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_update = AsyncMock(return_value=None)
        monkeypatch.setattr(playground_sse, "_update_attack_log", mock_update)
        trace_id, _ = _make_entry(attack_id=None)  # plain chat — no adversarial_attack_logs row
        _, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "CLEAN"
        mock_update.assert_not_called()


class TestPipelineUnhandledError:
    @pytest.mark.asyncio
    async def test_unhandled_exception_mid_actor_layer_yields_single_error_verdict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise(*_a, **_kw):
            raise RuntimeError("capability token signing failed")

        monkeypatch.setattr(playground_sse, "issue_token", _raise)
        trace_id, _ = _make_entry()
        layer_results, verdict = await _collect(trace_id)

        assert verdict["outcome"] == "ERROR"
        assert verdict["blockedByLayer"] == "actor-llm"
        actor_layer = next(l for l in verdict["layers"] if l["layerId"] == "actor-llm")
        assert actor_layer["status"] == "error"
        _assert_full_layer_coverage(verdict)
        _assert_nothing_passed_after_decisive(verdict)
        egress_layer = next(l for l in verdict["layers"] if l["layerId"] == "egress-filter")
        assert egress_layer["status"] == "not_reached"
