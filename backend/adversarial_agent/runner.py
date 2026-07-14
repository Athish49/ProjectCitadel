"""Adversarial agent entry point — Sprint 4.3.2 / 4.3.3.

Lifecycle:
  1. Prove network isolation (target API reachable; postgres unreachable).
  2. Create SpendLedger (hard $50/month circuit breaker — P11).
  3. Create Anthropic client and AttackStrategy.
  4. Run attack loop until max_attempts exhausted, spend cap tripped, or SIGTERM.

Network isolation probes:
  - adversarial-api /health  → must succeed
  - secureclaim-postgres:5432 → must fail (agent lives on adversarial_net only)
"""
from __future__ import annotations

import logging
import signal
import socket
import sys
import time
import uuid

import anthropic
import httpx

from config import (
    AGENT_ID,
    ANTHROPIC_API_KEY,
    DATABASE_URL,
    INPUT_COST_PER_1K,
    OUTPUT_COST_PER_1K,
    LOG_LEVEL,
    LOOP_INTERVAL_SECONDS,
    MAX_ATTEMPTS,
    MODEL,
    MONTHLY_SPEND_CAP_USD,
    SPEND_LEDGER_PATH,
    SSE_TIMEOUT_SECONDS,
    TARGET_API_URL,
)
from spend import SpendLedger
from strategy import AttackStrategy

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger(AGENT_ID)

_running = True


def _handle_stop(sig: int, _frame: object) -> None:
    global _running
    log.info("shutdown signal received (sig=%d) — stopping", sig)
    _running = False


def _probe_target() -> bool:
    """Verify the adversarial API target is reachable."""
    try:
        resp = httpx.get(f"{TARGET_API_URL}/health", timeout=5.0)
        resp.raise_for_status()
        log.info("isolation_probe target=adversarial-api result=reachable body=%s", resp.json())
        return True
    except Exception as exc:
        log.warning("isolation_probe target=adversarial-api result=unreachable error=%s", exc)
        return False


def _probe_db_isolation() -> None:
    """Assert the agent cannot directly reach the main Postgres instance.

    A successful TCP connection here is a network misconfiguration — the agent
    should be on adversarial_net only and cannot see secureclaim-postgres.
    """
    try:
        with socket.create_connection(("secureclaim-postgres", 5432), timeout=3):
            log.error(
                "isolation_probe target=secureclaim-postgres result=REACHABLE "
                "— network isolation is broken; agent can reach the main DB directly"
            )
    except OSError:
        log.info(
            "isolation_probe target=secureclaim-postgres result=unreachable "
            "— network isolation confirmed"
        )


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    log.info(
        "adversarial agent initialized — agent_id=%s model=%s target=%s max_attempts=%d",
        AGENT_ID,
        MODEL,
        TARGET_API_URL,
        MAX_ATTEMPTS,
    )

    if not _probe_target():
        log.error("adversarial-api unreachable at startup — exiting")
        sys.exit(1)

    _probe_db_isolation()

    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY not set — exiting")
        sys.exit(1)

    ledger = SpendLedger(
        cap_usd=MONTHLY_SPEND_CAP_USD,
        input_cost_per_1k=INPUT_COST_PER_1K,
        output_cost_per_1k=OUTPUT_COST_PER_1K,
        ledger_path=SPEND_LEDGER_PATH,
    )
    if ledger.tripped:
        log.error(
            "SPEND_CAP_ALREADY_TRIPPED period total_usd=%.4f cap_usd=%.2f — exiting",
            ledger.total_usd,
            MONTHLY_SPEND_CAP_USD,
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    strategy = AttackStrategy(
        client=client,
        max_attempts=MAX_ATTEMPTS,
        ledger=ledger,
        sse_timeout=SSE_TIMEOUT_SECONDS,
        database_url=DATABASE_URL,
    )
    session_id = str(uuid.uuid4())

    log.info(
        "attack_session_start session_id=%s max_attempts=%d cap_usd=%.2f",
        session_id,
        MAX_ATTEMPTS,
        MONTHLY_SPEND_CAP_USD,
    )

    while _running and not strategy.exhausted:
        strategy.run_one(api_url=TARGET_API_URL, session_id=session_id)
        if not strategy.exhausted:
            time.sleep(LOOP_INTERVAL_SECONDS)

    log.info(
        "attack_session_end session_id=%s exhausted=%s",
        session_id,
        strategy.exhausted,
    )


if __name__ == "__main__":
    main()
