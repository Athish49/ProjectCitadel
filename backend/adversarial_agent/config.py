"""Adversarial agent configuration — all values from environment variables."""
from __future__ import annotations

import os

TARGET_API_URL: str = os.environ.get("TARGET_API_URL", "http://adversarial-api:8080")
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
AGENT_ID: str = "adversarial_agent"
MODEL: str = "claude-sonnet-4-6"
LOOP_INTERVAL_SECONDS: float = float(os.environ.get("LOOP_INTERVAL_SECONDS", "2"))
MAX_ATTEMPTS: int = int(os.environ.get("MAX_ATTEMPTS", "60"))
SSE_TIMEOUT_SECONDS: float = float(os.environ.get("SSE_TIMEOUT_SECONDS", "120.0"))

# Spend cap (P11 — Sprint 4.3.3).
# Token prices for claude-sonnet-4-6; verify against
# https://www.anthropic.com/pricing if exact accounting is required.
MONTHLY_SPEND_CAP_USD: float = float(os.environ.get("MONTHLY_SPEND_CAP_USD", "50.0"))
INPUT_COST_PER_1K: float = float(os.environ.get("INPUT_COST_PER_1K", "0.003"))
OUTPUT_COST_PER_1K: float = float(os.environ.get("OUTPUT_COST_PER_1K", "0.015"))
SPEND_LEDGER_PATH: str = os.environ.get("SPEND_LEDGER_PATH", "/var/spend/ledger.json")
