"""Adversarial agent configuration — all values from environment variables."""
from __future__ import annotations

import os

TARGET_API_URL: str = os.environ.get("TARGET_API_URL", "http://adversarial-api:8080")
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
AGENT_ID: str = "adversarial_agent"
MODEL: str = "claude-haiku-4-5-20251001"
LOOP_INTERVAL_SECONDS: float = float(os.environ.get("LOOP_INTERVAL_SECONDS", "300"))
MAX_ATTEMPTS: int = int(os.environ.get("MAX_ATTEMPTS", "20"))

# Spend cap (P11 — Sprint 4.3.3).
# Token prices are estimates for claude-haiku-4-5-20251001; verify against
# https://www.anthropic.com/pricing if exact accounting is required.
MONTHLY_SPEND_CAP_USD: float = float(os.environ.get("MONTHLY_SPEND_CAP_USD", "50.0"))
HAIKU_INPUT_COST_PER_1K: float = float(os.environ.get("HAIKU_INPUT_COST_PER_1K", "0.001"))
HAIKU_OUTPUT_COST_PER_1K: float = float(os.environ.get("HAIKU_OUTPUT_COST_PER_1K", "0.005"))
SPEND_LEDGER_PATH: str = os.environ.get("SPEND_LEDGER_PATH", "/var/spend/ledger.json")
