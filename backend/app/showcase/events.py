"""In-process adversarial event bus (Sprint 4.3.4).

Single-worker constraint: this module is designed for a single uvicorn worker.
Multi-worker deployments would need a Redis pub/sub backend instead.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

_subscribers: list[asyncio.Queue[dict[str, Any]]] = []
_breach_count: int = 0
_last_breach_at: str | None = None


@dataclass
class AdversarialEvent:
    trace_id: str
    session_id: str
    attack_id: int
    verdict: str
    sanitizer_detections: list[str] = field(default_factory=list)
    chars_stripped: int = 0


def subscribe() -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue[dict[str, Any]]) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


def get_breach_stats() -> dict[str, Any]:
    return {"breach_count": _breach_count, "last_breach_at": _last_breach_at}


def publish(event: AdversarialEvent) -> None:
    global _breach_count, _last_breach_at

    is_breach = event.verdict == "EVADED_INGRESS"
    if is_breach:
        _breach_count += 1
        _last_breach_at = datetime.now(timezone.utc).isoformat()

    payload: dict[str, Any] = {
        "trace_id": event.trace_id,
        "session_id": event.session_id,
        "attack_id": event.attack_id,
        "verdict": event.verdict,
        "sanitizer_detections": event.sanitizer_detections,
        "chars_stripped": event.chars_stripped,
        "is_breach": is_breach,
        "breach_count": _breach_count,
        "last_breach_at": _last_breach_at,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    dead: list[asyncio.Queue[dict[str, Any]]] = []
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            log.warning("adversarial_sse: subscriber queue full, dropping event")
            dead.append(q)

    for q in dead:
        unsubscribe(q)
