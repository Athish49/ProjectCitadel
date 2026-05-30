"""Unit tests for the adversarial agent sandbox (Sprint 4.3.1).

These tests verify config, the isolation probes, and runner entry points
without requiring Docker or a live API.
"""
from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("httpx")

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestAdversarialConfig:
    def _load_config(self, env_overrides: dict[str, str]):
        """Load config module fresh with env overrides applied."""
        with patch.dict("os.environ", env_overrides, clear=False):
            if "config" in sys.modules:
                del sys.modules["config"]
            # Prepend adversarial_agent/ to path for the isolated module
            import os

            adv_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "adversarial_agent"
            )
            sys.path.insert(0, os.path.abspath(adv_path))
            try:
                import config as cfg

                importlib.reload(cfg)
                return cfg
            finally:
                sys.path.pop(0)

    def test_defaults(self):
        cfg = self._load_config({})
        assert cfg.TARGET_API_URL == "http://adversarial-api:8080"
        assert cfg.AGENT_ID == "adversarial_agent"
        assert cfg.MODEL == "claude-haiku-4-5-20251001"
        assert cfg.LOG_LEVEL == "INFO"
        assert cfg.LOOP_INTERVAL_SECONDS == 300.0

    def test_env_override_target_url(self):
        cfg = self._load_config({"TARGET_API_URL": "http://localhost:9999"})
        assert cfg.TARGET_API_URL == "http://localhost:9999"

    def test_model_is_haiku(self):
        cfg = self._load_config({})
        assert cfg.MODEL == "claude-haiku-4-5-20251001"

    def test_loop_interval_float(self):
        cfg = self._load_config({"LOOP_INTERVAL_SECONDS": "15"})
        assert cfg.LOOP_INTERVAL_SECONDS == 15.0


# ---------------------------------------------------------------------------
# Runner isolation probes
# ---------------------------------------------------------------------------


def _import_runner():
    """Import runner from adversarial_agent/ directory."""
    import importlib.util
    import os

    adv_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "adversarial_agent")
    )
    if adv_path not in sys.path:
        sys.path.insert(0, adv_path)
    if "runner" in sys.modules:
        del sys.modules["runner"]
    import runner

    return runner


class TestIsolationProbes:
    def test_probe_target_success(self):
        runner = _import_runner()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = runner._probe_target()

        assert result is True

    def test_probe_target_failure_returns_false(self):
        import httpx

        runner = _import_runner()
        with patch("httpx.get", side_effect=httpx.ConnectError("unreachable")):
            result = runner._probe_target()

        assert result is False

    def test_probe_db_isolation_logs_error_on_success(self, caplog):
        """If postgres IS reachable the probe must log an error (misconfiguration)."""
        import logging

        runner = _import_runner()
        mock_sock = MagicMock()
        mock_sock.__enter__ = MagicMock(return_value=mock_sock)
        mock_sock.__exit__ = MagicMock(return_value=False)

        with patch("socket.create_connection", return_value=mock_sock):
            with caplog.at_level(logging.ERROR, logger="adversarial_agent"):
                runner._probe_db_isolation()

        assert any("REACHABLE" in r.message for r in caplog.records)

    def test_probe_db_isolation_logs_info_on_oserror(self, caplog):
        """OSError means postgres unreachable — isolation confirmed."""
        import logging

        runner = _import_runner()
        with patch("socket.create_connection", side_effect=OSError("refused")):
            with caplog.at_level(logging.INFO, logger="adversarial_agent"):
                runner._probe_db_isolation()

        assert any("isolation confirmed" in r.message for r in caplog.records)

    def test_main_exits_when_target_unreachable(self):
        import httpx

        runner = _import_runner()
        with patch("httpx.get", side_effect=httpx.ConnectError("down")):
            with pytest.raises(SystemExit) as exc_info:
                runner.main()
        assert exc_info.value.code == 1

    def test_main_runs_loop_iteration_then_stops(self):
        """main() runs one iteration of the attack loop then stops when _running is cleared."""
        runner = _import_runner()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.raise_for_status = MagicMock()

        call_count = 0

        def fake_sleep(n):
            nonlocal call_count
            call_count += 1
            runner._running = False  # stop after first sleep

        mock_strategy = MagicMock()
        mock_strategy.exhausted = False
        mock_strategy.run_one.return_value = MagicMock()

        mock_ledger = MagicMock()
        mock_ledger.tripped = False

        with (
            patch("httpx.get", return_value=mock_resp),
            patch("socket.create_connection", side_effect=OSError()),
            patch("time.sleep", side_effect=fake_sleep),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("runner.ANTHROPIC_API_KEY", "test-key"),
            patch("runner.anthropic.Anthropic", return_value=MagicMock()),
            patch("runner.SpendLedger", return_value=mock_ledger),
            patch("runner.AttackStrategy", return_value=mock_strategy),
        ):
            runner._running = True
            runner.main()

        assert call_count == 1
