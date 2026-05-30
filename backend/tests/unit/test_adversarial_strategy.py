"""Unit tests for the adversarial attack strategy module (Sprint 4.3.2).

All tests mock the Anthropic client and httpx calls; no network or API key required.
"""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

pytest.importorskip("httpx")
pytest.importorskip("anthropic")

pytestmark = pytest.mark.unit

_ADV_PATH_INSERTED = False


def _insert_adv_path():
    import os
    global _ADV_PATH_INSERTED
    adv_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "adversarial_agent")
    )
    if adv_path not in sys.path:
        sys.path.insert(0, adv_path)
        _ADV_PATH_INSERTED = True


def _import_strategy():
    _insert_adv_path()
    for mod in ("strategy", "spend"):
        if mod in sys.modules:
            del sys.modules[mod]
    import strategy
    return strategy


def _mock_ledger() -> MagicMock:
    ledger = MagicMock()
    type(ledger).tripped = PropertyMock(return_value=False)
    ledger.record.return_value = 0.001
    return ledger


class TestAttackCategories:
    def test_exactly_15_categories(self):
        s = _import_strategy()
        assert len(s.ATTACK_CATEGORIES) == 15

    def test_all_attack_ids_unique(self):
        s = _import_strategy()
        ids = [c.attack_id for c in s.ATTACK_CATEGORIES]
        assert len(ids) == len(set(ids))

    def test_all_hints_non_empty(self):
        s = _import_strategy()
        for cat in s.ATTACK_CATEGORIES:
            assert cat.hint.strip(), f"Empty hint for {cat.name}"

    def test_category_1_is_direct_prompt_injection(self):
        s = _import_strategy()
        cat = next(c for c in s.ATTACK_CATEGORIES if c.attack_id == 1)
        assert "Prompt Injection" in cat.name


class TestGeneratePayload:
    def _make_client(self, text: str = "crafted payload") -> MagicMock:
        client = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text=text)]
        msg.usage.input_tokens = 100
        msg.usage.output_tokens = 50
        client.messages.create.return_value = msg
        return client

    def test_calls_haiku_model(self):
        s = _import_strategy()
        client = self._make_client()
        cat = s.ATTACK_CATEGORIES[0]
        s._generate_payload(cat, client, [], _mock_ledger())
        call_kwargs = client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_returns_payload_text(self):
        s = _import_strategy()
        client = self._make_client("my attack payload")
        cat = s.ATTACK_CATEGORIES[0]
        result = s._generate_payload(cat, client, [], _mock_ledger())
        assert result == "my attack payload"

    def test_prior_detections_included_in_prompt(self):
        s = _import_strategy()
        client = self._make_client()
        cat = s.ATTACK_CATEGORIES[0]
        s._generate_payload(cat, client, ["ignore_instructions", "dan_mode"], _mock_ledger())
        prompt_text = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "ignore_instructions" in prompt_text
        assert "dan_mode" in prompt_text

    def test_no_prior_detections_omits_evasion_note(self):
        s = _import_strategy()
        client = self._make_client()
        cat = s.ATTACK_CATEGORIES[0]
        s._generate_payload(cat, client, [], _mock_ledger())
        prompt_text = client.messages.create.call_args[1]["messages"][0]["content"]
        assert "prior payload" not in prompt_text


class TestSendAttack:
    def _mock_resp(self, detections: list[str], chars_stripped: int = 0) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "trace_id": "trace-abc",
            "session_id": "session-xyz",
            "sanitizer_detections": detections,
            "chars_stripped": chars_stripped,
            "verdict": "flagged" if detections else "clean",
        }
        resp.raise_for_status = MagicMock()
        return resp

    def test_blocked_verdict_when_detections_present(self):
        s = _import_strategy()
        cat = s.ATTACK_CATEGORIES[0]
        with patch("httpx.post", return_value=self._mock_resp(["ignore_instructions"])):
            outcome = s._send_attack("http://api", cat, "payload", 1, "sess", None)
        assert outcome.verdict == "BLOCKED_INGRESS"
        assert "ignore_instructions" in outcome.sanitizer_detections

    def test_evaded_verdict_when_no_detections(self):
        s = _import_strategy()
        cat = s.ATTACK_CATEGORIES[0]
        with patch("httpx.post", return_value=self._mock_resp([])):
            outcome = s._send_attack("http://api", cat, "payload", 1, "sess", None)
        assert outcome.verdict == "EVADED_INGRESS"

    def test_api_error_verdict_on_exception(self):
        import httpx
        s = _import_strategy()
        cat = s.ATTACK_CATEGORIES[0]
        with patch("httpx.post", side_effect=httpx.ConnectError("down")):
            outcome = s._send_attack("http://api", cat, "payload", 1, "sess", None)
        assert outcome.verdict == "API_ERROR"

    def test_mutated_from_preserved(self):
        s = _import_strategy()
        cat = s.ATTACK_CATEGORIES[0]
        with patch("httpx.post", return_value=self._mock_resp([])):
            outcome = s._send_attack("http://api", cat, "payload", 1, "sess", "original payload")
        assert outcome.mutated_from == "original payload"

    def test_trace_id_from_response(self):
        s = _import_strategy()
        cat = s.ATTACK_CATEGORIES[0]
        with patch("httpx.post", return_value=self._mock_resp([])):
            outcome = s._send_attack("http://api", cat, "payload", 1, "sess", None)
        assert outcome.trace_id == "trace-abc"


class TestAttackStrategy:
    def _make_strategy(self, max_attempts: int = 5) -> tuple:
        s = _import_strategy()
        client = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text="generated payload")]
        msg.usage.input_tokens = 100
        msg.usage.output_tokens = 50
        client.messages.create.return_value = msg
        ledger = _mock_ledger()
        strategy = s.AttackStrategy(client=client, max_attempts=max_attempts, ledger=ledger)
        return s, strategy, client

    def test_not_exhausted_at_start(self):
        _, strategy, _ = self._make_strategy()
        assert not strategy.exhausted

    def test_exhausted_after_max_attempts(self):
        s, strategy, _ = self._make_strategy(max_attempts=2)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "trace_id": "t", "session_id": "s",
            "sanitizer_detections": [], "chars_stripped": 0, "verdict": "clean",
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            strategy.run_one("http://api", "sess")
            strategy.run_one("http://api", "sess")
        assert strategy.exhausted

    def test_rotates_through_categories(self):
        s, strategy, client = self._make_strategy(max_attempts=30)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "trace_id": "t", "session_id": "s",
            "sanitizer_detections": [], "chars_stripped": 0, "verdict": "clean",
        }
        mock_resp.raise_for_status = MagicMock()
        seen_ids = set()
        with patch("httpx.post", return_value=mock_resp):
            for _ in range(len(s.ATTACK_CATEGORIES)):
                outcome = strategy.run_one("http://api", "sess")
                seen_ids.add(outcome.attack_id)
        assert len(seen_ids) == len(s.ATTACK_CATEGORIES)

    def test_mutation_uses_prior_detections(self):
        s, strategy, client = self._make_strategy(max_attempts=20)
        mock_blocked = MagicMock()
        mock_blocked.json.return_value = {
            "trace_id": "t1", "session_id": "s",
            "sanitizer_detections": ["dan_mode"], "chars_stripped": 5, "verdict": "flagged",
        }
        mock_blocked.raise_for_status = MagicMock()

        mock_clean = MagicMock()
        mock_clean.json.return_value = {
            "trace_id": "t2", "session_id": "s",
            "sanitizer_detections": [], "chars_stripped": 0, "verdict": "clean",
        }
        mock_clean.raise_for_status = MagicMock()

        # First full rotation (15 categories): first category blocked once
        responses = [mock_blocked] + [mock_clean] * 14
        # Second rotation: first category should now mutate
        responses += [mock_clean] * 15

        with patch("httpx.post", side_effect=responses):
            # Run first full rotation
            for _ in range(15):
                strategy.run_one("http://api", "sess")

            # Reset to same first category (rotation_idx = 15, next = index 0 again)
            second_outcome = strategy.run_one("http://api", "sess")

        # The second attempt on category index 0 should have mutated_from set
        assert second_outcome.mutated_from is not None
        # And the prompt passed to Claude should have referenced the blocked pattern
        all_calls = client.messages.create.call_args_list
        second_call_prompt = all_calls[-1][1]["messages"][0]["content"]
        assert "dan_mode" in second_call_prompt

    def test_outcome_has_timestamp(self):
        s, strategy, _ = self._make_strategy()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "trace_id": "t", "session_id": "s",
            "sanitizer_detections": [], "chars_stripped": 0, "verdict": "clean",
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            outcome = strategy.run_one("http://api", "sess")
        assert outcome.timestamp  # non-empty ISO string
