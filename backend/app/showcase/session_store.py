"""In-memory conversation history store with TTL eviction for playground sessions."""
from __future__ import annotations

import time

TTL: float = 1800.0  # 30-minute session TTL in seconds

_STORE: dict[str, list[dict]] = {}
_TIMESTAMPS: dict[str, float] = {}


def append(session_id: str, role: str, content: str) -> None:
    evict_expired()
    if session_id not in _STORE:
        _STORE[session_id] = []
    _STORE[session_id].append({"role": role, "content": content})
    _TIMESTAMPS[session_id] = time.monotonic()


def get_history(session_id: str) -> list[dict]:
    if session_id not in _STORE:
        return []
    if time.monotonic() - _TIMESTAMPS[session_id] > TTL:
        del _STORE[session_id]
        del _TIMESTAMPS[session_id]
        return []
    return list(_STORE[session_id])


def evict_expired() -> None:
    now = time.monotonic()
    expired = [sid for sid, ts in _TIMESTAMPS.items() if now - ts > TTL]
    for sid in expired:
        _STORE.pop(sid, None)
        _TIMESTAMPS.pop(sid, None)
