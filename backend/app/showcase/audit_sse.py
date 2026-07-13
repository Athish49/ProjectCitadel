"""Real-time audit log SSE endpoint — polls real DB tables and streams AuditRow events."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db import get_dsn

log = logging.getLogger(__name__)

router = APIRouter(prefix="/showcase/sse")

_POLL_INTERVAL  = 2.0   # seconds between DB polls
_KEEPALIVE_SECS = 15.0  # send SSE keepalive comment if silent this long

# ── Agent/event normalisation ─────────────────────────────────────────────────

_AGENT_MAP: dict[str, str] = {
    "ingress": "ingress",
    "ingress_sanitiser": "ingress",
    "pattern_detection": "pattern_detection",
    "semantic_classifier": "semantic_classifier",
    "parser": "parser_llm",
    "parser_llm": "parser_llm",
    "intake_parser": "parser_llm",
    "orchestrator": "orchestrator",
    "intake_actor": "actor_llm",
    "actor_llm": "actor_llm",
    "identity_verifier": "identity_verifier",
    "claims_processor": "claims_processor",
    "settlement_actor": "settlement_actor",
    "tool_registry": "tool_registry",
    "data_layer": "data_layer",
    "egress_filter": "egress_filter",
    "adversarial_agent": "adversarial_agent",
}

_EVENT_AGENT: dict[str, str] = {
    "injection_detected":           "ingress",
    "sanitise":                     "ingress",
    "injection_pattern_blocked":    "pattern_detection",
    "adversarial_intent_blocked":   "semantic_classifier",
    "schema_violation_blocked":     "parser_llm",
    "egress_violation_blocked":     "egress_filter",
    "pipeline_breach":              "orchestrator",
    "identity_fail_match":          "identity_verifier",
    "identity_lockout":             "identity_verifier",
    "capability_violation":         "tool_registry",
}

_SEC_SEV: dict[str, str] = {"info": "info", "warn": "warn", "critical": "alert"}
_IDENT_SEV: dict[str, str] = {"SUCCESS": "ok", "FAIL_MATCH": "warn", "LOCKOUT": "alert"}


def _agent(agent_id: str | None, fallback: str = "orchestrator") -> str:
    if not agent_id:
        return fallback
    return _AGENT_MAP.get(agent_id, agent_id)


def _short(val: Any) -> str:
    return str(val)[:8] if val is not None else "00000000"


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return datetime.now(timezone.utc).isoformat()
    return dt.astimezone(timezone.utc).isoformat() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).isoformat()


def _sse(row: dict) -> str:
    return f"event: audit_row\ndata: {json.dumps(row)}\n\n"


# ── Row formatters ────────────────────────────────────────────────────────────

def _fmt_audit_log(row: dict) -> dict:
    return {
        "id":       f"al-{row['log_id']}",
        "ts":       _iso(row.get("ts")),
        "traceId":  _short(row.get("trace_id")),
        "agent":    _agent(row.get("agent_id")),
        "action":   row.get("action") or "log_entry",
        "label":    row.get("data_label"),
        "severity": "alert" if row.get("security_event") else "ok",
        "outcome":  "blocked" if row.get("security_event") else "ok",
        "detail":   row.get("details") or {},
    }


def _fmt_security_event(row: dict) -> dict:
    event_type = row.get("event_type") or "security_event"
    return {
        "id":       f"se-{_short(row.get('event_id'))}",
        "ts":       _iso(row.get("ts")),
        "traceId":  _short(row.get("trace_id")),
        "agent":    _EVENT_AGENT.get(event_type, "ingress"),
        "action":   event_type,
        "label":    None,
        "severity": _SEC_SEV.get(row.get("severity", "warn"), "warn"),
        "outcome":  "blocked",
        "detail":   row.get("details") or {},
    }


def _fmt_identity_attempt(row: dict) -> dict:
    outcome = row.get("outcome", "FAIL_MATCH")
    return {
        "id":       f"ia-{_short(row.get('attempt_id'))}",
        "ts":       _iso(row.get("ts")),
        "traceId":  _short(row.get("session_id")),
        "agent":    "identity_verifier",
        "action":   "identity_verify",
        "label":    "PERSONAL",
        "severity": _IDENT_SEV.get(outcome, "warn"),
        "outcome":  outcome.lower(),
        "detail": {
            "policy_number": row.get("attempted_policy_number"),
            "customer_id":   str(row["customer_id"]) if row.get("customer_id") else None,
        },
    }


def _fmt_capability_token(row: dict) -> dict:
    use_result = row.get("use_result")
    action = "capability_check" if row.get("used_at") else "capability_issued"
    if use_result == "OK":
        sev, outcome = "ok", "verified"
    elif use_result:
        sev = "warn"
        outcome = f"denied({use_result.lower().removeprefix('denied_')})"
    else:
        sev, outcome = "ok", "issued"
    return {
        "id":       f"ct-{_short(row.get('token_id'))}",
        "ts":       _iso(row.get("used_at") or row.get("issued_at")),
        "traceId":  _short(row.get("token_id")),
        "agent":    "tool_registry",
        "action":   action,
        "label":    None,
        "severity": sev,
        "outcome":  outcome,
        "detail": {
            "tool":       row.get("tool"),
            "agent_id":   row.get("agent_id"),
            "issued_by":  row.get("issued_by"),
            "use_result": use_result,
        },
    }


# ── Async generator ───────────────────────────────────────────────────────────

async def _generate():
    try:
        dsn = get_dsn()
    except RuntimeError as exc:
        log.error("audit_sse: %s", exc)
        yield ": error: DATABASE_URL not configured\n\n"
        return

    try:
        conn = await psycopg.AsyncConnection.connect(dsn)
    except Exception as exc:
        log.error("audit_sse: DB connect failed: %s", exc)
        yield ": error: db_connect_failed\n\n"
        return

    try:
        await conn.set_autocommit(True)

        async with conn.cursor(row_factory=dict_row) as cur:
            # ── History batch ─────────────────────────────────────────────────
            # Fetch recent rows from all 4 tables, merge, sort newest-first,
            # and emit as a single 'history' event so the client sets state
            # atomically — avoids per-row prepend which loses old rows when
            # total > MAX_ROWS on the frontend.
            history: list[dict] = []

            await cur.execute(
                "SELECT * FROM audit_log ORDER BY log_id DESC LIMIT 200"
            )
            for row in await cur.fetchall():
                history.append(_fmt_audit_log(row))

            await cur.execute(
                "SELECT * FROM security_events ORDER BY ts DESC LIMIT 50"
            )
            for row in await cur.fetchall():
                history.append(_fmt_security_event(row))

            await cur.execute(
                "SELECT * FROM identity_attempts ORDER BY ts DESC LIMIT 30"
            )
            for row in await cur.fetchall():
                history.append(_fmt_identity_attempt(row))

            await cur.execute(
                "SELECT * FROM capability_token_log ORDER BY issued_at DESC LIMIT 30"
            )
            for row in await cur.fetchall():
                history.append(_fmt_capability_token(row))

            # Sort newest-first so the frontend can set rows directly and display
            # them in chronological-descending order without a second sort pass.
            history.sort(key=lambda r: r["ts"], reverse=True)
            yield f"event: history\ndata: {json.dumps(history)}\n\n"

        # Initialise cursors to current state — only NEW rows will stream.
        # Use NOW() as the empty-table fallback; '-infinity' can't round-trip to Python datetime.
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT COALESCE(MAX(log_id), 0) FROM audit_log")
            audit_cursor: int = (await cur.fetchone())["coalesce"]  # type: ignore[index]

            await cur.execute(
                "SELECT COALESCE(MAX(ts), NOW()) FROM security_events"
            )
            sec_cursor: datetime = (await cur.fetchone())["coalesce"]  # type: ignore[index]

            await cur.execute(
                "SELECT COALESCE(MAX(ts), NOW()) FROM identity_attempts"
            )
            ident_cursor: datetime = (await cur.fetchone())["coalesce"]  # type: ignore[index]

            await cur.execute(
                "SELECT COALESCE(MAX(issued_at), NOW()) FROM capability_token_log"
            )
            cap_cursor: datetime = (await cur.fetchone())["coalesce"]  # type: ignore[index]

        loop = asyncio.get_running_loop()
        last_event_at = loop.time()

        while True:
            events: list[str] = []

            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM audit_log WHERE log_id > %s ORDER BY log_id LIMIT 50",
                    (audit_cursor,),
                )
                for row in await cur.fetchall():
                    events.append(_sse(_fmt_audit_log(row)))
                    audit_cursor = row["log_id"]

                await cur.execute(
                    "SELECT * FROM security_events WHERE ts > %s ORDER BY ts LIMIT 50",
                    (sec_cursor,),
                )
                for row in await cur.fetchall():
                    events.append(_sse(_fmt_security_event(row)))
                    sec_cursor = row["ts"]

                await cur.execute(
                    "SELECT * FROM identity_attempts WHERE ts > %s ORDER BY ts LIMIT 50",
                    (ident_cursor,),
                )
                for row in await cur.fetchall():
                    events.append(_sse(_fmt_identity_attempt(row)))
                    ident_cursor = row["ts"]

                await cur.execute(
                    "SELECT * FROM capability_token_log"
                    " WHERE issued_at > %s ORDER BY issued_at LIMIT 50",
                    (cap_cursor,),
                )
                for row in await cur.fetchall():
                    events.append(_sse(_fmt_capability_token(row)))
                    cap_cursor = row["issued_at"]

            # Yield outside the cursor context to avoid psycopg3 async generator issues.
            for event in events:
                yield event

            now = loop.time()
            if events:
                last_event_at = now
            elif now - last_event_at > _KEEPALIVE_SECS:
                yield ": keepalive\n\n"
                last_event_at = now

            await asyncio.sleep(_POLL_INTERVAL)

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("audit_sse: stream error: %s", exc)
    finally:
        await conn.close()


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/audit")
async def audit_stream() -> StreamingResponse:
    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )
