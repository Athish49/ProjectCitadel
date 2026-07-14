"""SSE endpoint for adversarial agent live feed — polls adversarial_attack_logs table.

Architecture note: the adversarial-api and the website backend are separate containers
that share one Postgres instance. All state therefore flows through the DB; the previous
in-memory pub/sub was only reachable within the adversarial-api process and never
forwarded to the website's SSE subscribers in production.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db import get_dsn

log = logging.getLogger(__name__)

router = APIRouter(prefix="/showcase/sse")

_POLL_INTERVAL   = 2.0   # seconds between DB polls for new rows
_KEEPALIVE_SECS  = 15.0  # emit SSE keepalive comment if silent this long
_STATUS_INTERVAL = 30.0  # seconds between periodic agent_status refreshes
_AGENT_LIVE_SECS = 90    # last row younger than this → agent is LIVE
_HISTORY_LIMIT   = 20    # rows to emit on connect


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return datetime.now(timezone.utc).isoformat()
    return (
        dt.astimezone(timezone.utc).isoformat()
        if dt.tzinfo
        else dt.replace(tzinfo=timezone.utc).isoformat()
    )


def _fmt_row(row: dict) -> dict:
    return {
        "trace_id":             str(row["trace_id"]),
        "session_id":           str(row["session_id"]),
        "attack_id":            row["attack_id"],
        "verdict":              row["verdict"],
        "sanitizer_detections": row["sanitizer_detections"] or [],
        "chars_stripped":       row["chars_stripped"],
        "is_breach":            row["is_breach"],
        "pipeline_verdict":     row.get("pipeline_verdict"),
        "blocked_by_layer":     row.get("blocked_by_layer"),
        "timestamp":            _iso(row["ts"]),
    }


def _agent_status(last_ts: datetime | None) -> dict:
    if last_ts is None:
        return {"status": "OFFLINE", "last_seen_at": None}
    aware = last_ts.astimezone(timezone.utc) if last_ts.tzinfo else last_ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - aware).total_seconds()
    return {
        "status":      "LIVE" if age <= _AGENT_LIVE_SECS else "OFFLINE",
        "last_seen_at": _iso(last_ts),
    }


async def _generate():
    try:
        dsn = get_dsn()
    except RuntimeError as exc:
        log.error("adversarial_sse: %s", exc)
        yield ": error: DATABASE_URL not configured\n\n"
        return

    try:
        conn = await psycopg.AsyncConnection.connect(dsn)
    except Exception as exc:
        log.error("adversarial_sse: DB connect failed: %s", exc)
        yield ": error: db_connect_failed\n\n"
        return

    try:
        await conn.set_autocommit(True)

        async with conn.cursor(row_factory=dict_row) as cur:
            # ── History batch (newest → oldest, frontend reverses to display) ──
            await cur.execute(
                "SELECT * FROM adversarial_attack_logs ORDER BY id DESC LIMIT %s",
                (_HISTORY_LIMIT,),
            )
            history_rows = await cur.fetchall()
            # Send newest-first; frontend prepends entries so this order is natural
            history = [_fmt_row(r) for r in history_rows]
            yield f"event: history\ndata: {json.dumps(history)}\n\n"

            # ── All-time breach stats from DB ────────────────────────────────
            await cur.execute(
                "SELECT"
                "  COUNT(*) AS total,"
                "  COALESCE(SUM(CASE WHEN pipeline_verdict = 'BREACH' THEN 1 ELSE 0 END), 0) AS breaches,"
                "  MAX(CASE WHEN pipeline_verdict = 'BREACH' THEN ts END) AS last_breach_at "
                "FROM adversarial_attack_logs"
            )
            s = await cur.fetchone()
            breach_stats_payload = {
                "total_attempts":  int(s["total"]),
                "breach_count":    int(s["breaches"]),
                "last_breach_at":  _iso(s["last_breach_at"]) if s["last_breach_at"] else None,
            }
            yield f"event: breach_stats\ndata: {json.dumps(breach_stats_payload)}\n\n"

            # ── Agent status ─────────────────────────────────────────────────
            await cur.execute(
                "SELECT MAX(ts) AS last_ts FROM adversarial_attack_logs"
            )
            last_ts_row = await cur.fetchone()
            last_ts: datetime | None = last_ts_row["last_ts"] if last_ts_row else None
            yield f"event: agent_status\ndata: {json.dumps(_agent_status(last_ts))}\n\n"

            # ── Polling cursor: max id already sent (0 if table empty) ───────
            cursor_id: int = history_rows[0]["id"] if history_rows else 0

        loop = asyncio.get_running_loop()
        last_event_at  = loop.time()
        last_status_at = loop.time()

        while True:
            events: list[str] = []

            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM adversarial_attack_logs"
                    " WHERE id > %s ORDER BY id LIMIT 50",
                    (cursor_id,),
                )
                for row in await cur.fetchall():
                    events.append(f"event: attempt\ndata: {json.dumps(_fmt_row(row))}\n\n")
                    cursor_id = row["id"]

            for event in events:
                yield event

            now = loop.time()
            if events:
                last_event_at = now

            if now - last_status_at >= _STATUS_INTERVAL:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(
                        "SELECT MAX(ts) AS last_ts FROM adversarial_attack_logs"
                    )
                    row = await cur.fetchone()
                    ts = row["last_ts"] if row else None
                yield f"event: agent_status\ndata: {json.dumps(_agent_status(ts))}\n\n"
                last_status_at = now
            elif now - last_event_at > _KEEPALIVE_SECS:
                yield ": keepalive\n\n"
                last_event_at = now

            await asyncio.sleep(_POLL_INTERVAL)

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("adversarial_sse: stream error: %s", exc)
    finally:
        await conn.close()


@router.get("/adversarial")
async def adversarial_stream() -> StreamingResponse:
    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )
