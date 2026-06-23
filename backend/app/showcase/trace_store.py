"""Short-lived in-memory store for showcase playground pipeline traces.

Entries are written by the POST /submit endpoint and read by the SSE pipeline
endpoint.  Uses get (not pop) semantics so that EventSource reconnects find the
same entry; TTL handles cleanup.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

_TTL = 120.0  # seconds before an entry is considered expired


@dataclass
class TraceEntry:
    payload: str
    detections: list[str]
    chars_stripped: int
    sanitized: str  # <untrusted>-wrapped text produced by sanitise()
    created_at: float = field(default_factory=time.monotonic)


_store: dict[str, TraceEntry] = {}


def put(trace_id: str, entry: TraceEntry) -> None:
    """Store a trace entry.  Prunes expired entries as a side-effect."""
    now = time.monotonic()
    expired = [k for k, v in _store.items() if now - v.created_at > _TTL]
    for k in expired:
        del _store[k]
    _store[trace_id] = entry


def get(trace_id: str) -> TraceEntry | None:
    """Return the entry for trace_id if it exists and has not expired."""
    entry = _store.get(trace_id)
    if entry is None:
        return None
    if time.monotonic() - entry.created_at > _TTL:
        del _store[trace_id]
        return None
    return entry
