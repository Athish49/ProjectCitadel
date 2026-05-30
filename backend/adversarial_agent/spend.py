"""Per-call cost accounting with monthly circuit breaker (P11 — Sprint 4.3.3).

The SpendLedger persists to a JSON file on a named Docker volume so the cap is
genuinely monthly and survives container restarts. It resets automatically when
the UTC calendar month rolls over.

Pricing constants (HAIKU_INPUT_COST_PER_1K, HAIKU_OUTPUT_COST_PER_1K) are
estimates for claude-haiku-4-5-20251001 based on published Anthropic pricing.
Verify against https://www.anthropic.com/pricing before relying on exact figures.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("adversarial_agent")

_PERIOD_FORMAT = "%Y-%m"


class SpendLedger:
    """Monthly spend accumulator with a hard-cap circuit breaker.

    Not thread-safe; designed for the single-process adversarial agent.
    """

    def __init__(
        self,
        cap_usd: float,
        input_cost_per_1k: float,
        output_cost_per_1k: float,
        ledger_path: str,
    ) -> None:
        self._cap = cap_usd
        self._input_rate = input_cost_per_1k / 1000.0   # $/token
        self._output_rate = output_cost_per_1k / 1000.0
        self._path = Path(ledger_path)
        self._period, self._total_usd = self._load()

        log.info(
            "spend_ledger initialized period=%s total_usd=%.6f cap_usd=%.2f path=%s",
            self._period,
            self._total_usd,
            self._cap,
            self._path,
        )

    # -- persistence ----------------------------------------------------------

    @staticmethod
    def _current_period() -> str:
        return datetime.now(timezone.utc).strftime(_PERIOD_FORMAT)

    def _load(self) -> tuple[str, float]:
        period = self._current_period()
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                if data.get("period") == period:
                    return period, float(data.get("total_usd", 0.0))
            except Exception as exc:
                log.warning("spend_ledger load failed (%s) — starting fresh", exc)
        return period, 0.0

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"period": self._period, "total_usd": self._total_usd}))
        except Exception as exc:
            log.warning("spend_ledger save failed: %s", exc)

    # -- public API -----------------------------------------------------------

    @property
    def tripped(self) -> bool:
        """True when the current-period spend equals or exceeds the cap.

        Handles month rollover automatically on every access.
        """
        current = self._current_period()
        if current != self._period:
            log.info(
                "spend_ledger period rollover %s → %s — resetting total",
                self._period,
                current,
            )
            self._period = current
            self._total_usd = 0.0
            self._save()
        return self._total_usd >= self._cap

    @property
    def total_usd(self) -> float:
        return self._total_usd

    def record(self, input_tokens: int, output_tokens: int) -> float:
        """Accumulate cost for one API call, persist, and return cost delta in USD."""
        delta = input_tokens * self._input_rate + output_tokens * self._output_rate
        self._total_usd += delta
        self._save()
        log.info(
            "spend_ledger period=%s delta_usd=%.6f total_usd=%.6f cap_usd=%.2f",
            self._period,
            delta,
            self._total_usd,
            self._cap,
        )
        if self._total_usd >= self._cap:
            log.error(
                "SPEND_CAP_TRIPPED period=%s total_usd=%.4f cap_usd=%.2f "
                "— circuit breaker engaged; no further LLM calls will be made this month",
                self._period,
                self._total_usd,
                self._cap,
            )
        return delta
