"""Unit tests for SpendLedger and its integration with AttackStrategy (Sprint 4.3.3)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

def _insert_adv_path():
    import os
    adv_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "adversarial_agent")
    )
    if adv_path not in sys.path:
        sys.path.insert(0, adv_path)


def _import_spend():
    _insert_adv_path()
    if "spend" in sys.modules:
        del sys.modules["spend"]
    import spend
    return spend


def _import_strategy():
    _insert_adv_path()
    for mod in ("strategy", "spend"):
        if mod in sys.modules:
            del sys.modules[mod]
    import strategy
    return strategy


# ---------------------------------------------------------------------------
# SpendLedger unit tests
# ---------------------------------------------------------------------------


class TestSpendLedger:
    def _make_ledger(self, tmp_path: Path, cap: float = 50.0) -> object:
        spend = _import_spend()
        return spend.SpendLedger(
            cap_usd=cap,
            input_cost_per_1k=1.0,   # $1/1K input tokens → $0.001/token
            output_cost_per_1k=5.0,  # $5/1K output tokens → $0.005/token
            ledger_path=str(tmp_path / "ledger.json"),
        )

    def test_starts_at_zero(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path)
        assert ledger.total_usd == 0.0

    def test_not_tripped_at_start(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path)
        assert not ledger.tripped

    def test_record_returns_correct_delta(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path)
        # 1000 input tokens × $0.001 + 200 output tokens × $0.005 = $1.00 + $1.00 = $2.00
        delta = ledger.record(input_tokens=1000, output_tokens=200)
        assert abs(delta - 2.0) < 1e-9

    def test_accumulates_across_calls(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path)
        ledger.record(1000, 0)   # $1.00
        ledger.record(0, 1000)   # $5.00
        assert abs(ledger.total_usd - 6.0) < 1e-9

    def test_not_tripped_below_cap(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path, cap=50.0)
        ledger.record(input_tokens=1000, output_tokens=0)  # $1.00
        assert not ledger.tripped

    def test_tripped_at_cap(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path, cap=1.0)
        ledger.record(input_tokens=1000, output_tokens=0)  # $1.00 — exactly at cap
        assert ledger.tripped

    def test_tripped_above_cap(self, tmp_path: Path):
        ledger = self._make_ledger(tmp_path, cap=0.5)
        ledger.record(input_tokens=1000, output_tokens=0)  # $1.00 > $0.50
        assert ledger.tripped

    def test_persists_to_file(self, tmp_path: Path):
        spend = _import_spend()
        path = tmp_path / "ledger.json"
        ledger = spend.SpendLedger(
            cap_usd=50.0, input_cost_per_1k=1.0, output_cost_per_1k=5.0,
            ledger_path=str(path),
        )
        ledger.record(1000, 0)  # $1.00
        assert path.exists()
        data = json.loads(path.read_text())
        assert abs(data["total_usd"] - 1.0) < 1e-9

    def test_loads_existing_period_from_file(self, tmp_path: Path):
        spend = _import_spend()
        path = tmp_path / "ledger.json"
        from datetime import datetime, timezone
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        path.write_text(json.dumps({"period": period, "total_usd": 30.0}))

        ledger = spend.SpendLedger(
            cap_usd=50.0, input_cost_per_1k=1.0, output_cost_per_1k=5.0,
            ledger_path=str(path),
        )
        assert abs(ledger.total_usd - 30.0) < 1e-9

    def test_ignores_stale_period_in_file(self, tmp_path: Path):
        spend = _import_spend()
        path = tmp_path / "ledger.json"
        path.write_text(json.dumps({"period": "2000-01", "total_usd": 999.0}))

        ledger = spend.SpendLedger(
            cap_usd=50.0, input_cost_per_1k=1.0, output_cost_per_1k=5.0,
            ledger_path=str(path),
        )
        assert ledger.total_usd == 0.0
        assert not ledger.tripped

    def test_month_rollover_resets_total(self, tmp_path: Path):
        spend = _import_spend()
        ledger = spend.SpendLedger(
            cap_usd=0.5, input_cost_per_1k=1.0, output_cost_per_1k=5.0,
            ledger_path=str(tmp_path / "ledger.json"),
        )
        ledger.record(1000, 0)  # $1.00 — crosses cap
        assert ledger.tripped

        # Simulate month rollover by patching _current_period on the instance's class
        with patch.object(type(ledger), "_current_period", staticmethod(lambda: "2099-12")):
            assert not ledger.tripped       # rollover detected → reset
            assert ledger.total_usd == 0.0  # reset confirmed

    def test_tripped_log_error_emitted(self, tmp_path: Path, caplog):
        import logging
        ledger = self._make_ledger(tmp_path, cap=0.001)
        with caplog.at_level(logging.ERROR, logger="adversarial_agent"):
            ledger.record(input_tokens=10, output_tokens=0)
        assert any("SPEND_CAP_TRIPPED" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# AttackStrategy integration: circuit breaker via ledger.tripped
# ---------------------------------------------------------------------------


class TestSpendCapInStrategy:
    def _mock_ledger(self, tripped: bool = False) -> MagicMock:
        ledger = MagicMock()
        type(ledger).tripped = PropertyMock(return_value=tripped)
        ledger.record.return_value = 0.001
        return ledger

    def _make_strategy(self, tripped: bool = False, max_attempts: int = 20):
        s = _import_strategy()
        client = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text="payload")]
        msg.usage.input_tokens = 100
        msg.usage.output_tokens = 50
        client.messages.create.return_value = msg
        ledger = self._mock_ledger(tripped=tripped)
        strategy = s.AttackStrategy(client=client, max_attempts=max_attempts, ledger=ledger)
        return s, strategy, client, ledger

    def test_exhausted_when_ledger_tripped(self):
        _, strategy, _, _ = self._make_strategy(tripped=True)
        assert strategy.exhausted

    def test_not_exhausted_when_ledger_not_tripped_and_attempts_remain(self):
        _, strategy, _, _ = self._make_strategy(tripped=False, max_attempts=5)
        assert not strategy.exhausted

    def test_ledger_record_called_after_generate(self):
        import httpx
        s, strategy, client, ledger = self._make_strategy(tripped=False)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "trace_id": "t", "session_id": "s",
            "sanitizer_detections": [], "chars_stripped": 0, "verdict": "clean",
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            strategy.run_one("http://api", "sess")
        ledger.record.assert_called_once_with(100, 50)

    def test_exhausted_after_cap_crossed_mid_run(self):
        """Simulates cap being crossed exactly after the first call."""
        s = _import_strategy()
        client = MagicMock()
        msg = MagicMock()
        msg.content = [MagicMock(text="p")]
        msg.usage.input_tokens = 10
        msg.usage.output_tokens = 5
        client.messages.create.return_value = msg

        ledger = MagicMock()
        record_calls = [0]

        def _record(*_args, **_kwargs):
            record_calls[0] += 1
            return 0.001

        ledger.record.side_effect = _record
        # tripped is False before first record call, True after
        type(ledger).tripped = PropertyMock(side_effect=lambda: record_calls[0] >= 1)

        strategy = s.AttackStrategy(client=client, max_attempts=20, ledger=ledger)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "trace_id": "t", "session_id": "s",
            "sanitizer_detections": [], "chars_stripped": 0, "verdict": "clean",
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("httpx.post", return_value=mock_resp):
            strategy.run_one("http://api", "sess")  # record called → tripped becomes True
        assert strategy.exhausted
