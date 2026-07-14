"""Showcase playground endpoint (TAD §7.2) — Sprint 4.3.2 / 4.3.4."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from pydantic import BaseModel

from agent_system.sanitisation.text import sanitise
from app.config import cfg
from app.db import get_dsn
from app.showcase.trace_store import TraceEntry
from app.showcase.trace_store import put as _store_trace
from audit.chain import append_log

log = logging.getLogger(__name__)

router = APIRouter(prefix="/showcase/playground")

PERSONA_CUSTOMER_IDS: dict[str, str] = {
    "mark":      "035a902e-c9b8-480b-81b4-d245a7b188c7",
    "christina": "08263522-0c19-41ca-aa59-8bcb5654a5e5",
    "ryan":      "3374fb96-344d-4d60-802f-ef269c27c916",
    "laura":     "2bc746d7-2484-46e2-80a0-6387b780d969",
    "morgan":    "2b69c31b-323a-4e55-be79-e9fefc5b2838",
}


async def verify_playground_token(
    x_playground_token: str | None = Header(None),
) -> None:
    if x_playground_token != cfg.playground_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


class SubmitRequest(BaseModel):
    message: str
    session_id: str | None = None
    attack_id: int | None = None
    attack_category: str | None = None
    attack_category_group: str | None = None


class SubmitResponse(BaseModel):
    trace_id: str
    session_id: str
    sanitizer_detections: list[str]
    chars_stripped: int
    verdict: str  # "clean" | "flagged"


async def _write_attack_log(
    trace_id: str,
    session_id: str,
    attack_id: int,
    verdict: str,
    detections: list[str],
    chars_stripped: int,
    is_breach: bool,
    payload: str | None = None,
    attack_category: str | None = None,
    attack_category_group: str | None = None,
) -> None:
    """Persist adversarial attack outcome to adversarial_attack_logs."""
    def _sync() -> None:
        try:
            dsn = get_dsn()
        except RuntimeError:
            log.warning("attack_log_write: DATABASE_URL not available — skipping")
            return
        try:
            sid: uuid.UUID
            try:
                sid = uuid.UUID(session_id)
            except (ValueError, AttributeError):
                sid = uuid.uuid4()
            with psycopg.connect(dsn, autocommit=False) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO adversarial_attack_logs
                            (trace_id, session_id, attack_id, verdict,
                             sanitizer_detections, chars_stripped, is_breach,
                             payload, attack_category, attack_category_group)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                        """,
                        (
                            uuid.UUID(trace_id),
                            sid,
                            attack_id,
                            verdict,
                            json.dumps(detections),
                            chars_stripped,
                            is_breach,
                            payload,
                            attack_category,
                            attack_category_group,
                        ),
                    )
                conn.commit()
        except Exception as exc:
            log.warning("attack_log_write_failed trace=%s error=%s", trace_id[:8], exc)

    await asyncio.to_thread(_sync)


async def _write_audit(
    trace_id: str,
    session_id: str,
    message: str,
    detections: list[str],
    chars_stripped: int,
    verdict: str,
) -> None:
    """Write sanitiser outcome to audit_log (and security_events if flagged)."""
    def _sync() -> None:
        try:
            dsn = get_dsn()
        except RuntimeError:
            log.warning("audit_write: DATABASE_URL not available — skipping")
            return
        try:
            with psycopg.connect(dsn, autocommit=False) as conn:
                append_log(
                    conn,
                    agent_id="ingress",
                    action="sanitise",
                    target=f"session:{session_id[:8]}",
                    data_label="UNTRUSTED",
                    trace_id=uuid.UUID(trace_id),
                    details={
                        "chars": len(message),
                        "chars_stripped": chars_stripped,
                        "detections": detections,
                        "verdict": verdict,
                    },
                    security_event=(verdict == "flagged"),
                )
                if verdict == "flagged" and detections:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO security_events
                                (trace_id, event_type, severity, details)
                            VALUES (%s, %s, %s, %s::jsonb)
                            """,
                            (
                                uuid.UUID(trace_id),
                                "injection_detected",
                                "warn",
                                json.dumps({
                                    "detections": detections,
                                    "chars_stripped": chars_stripped,
                                }),
                            ),
                        )
                conn.commit()
        except Exception as exc:
            log.warning("audit_write_failed trace=%s error=%s", trace_id[:8], exc)

    await asyncio.to_thread(_sync)


@router.post("/submit", response_model=SubmitResponse)
async def submit(req: SubmitRequest, background_tasks: BackgroundTasks, _: None = Depends(verify_playground_token)) -> SubmitResponse:
    session_id = req.session_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    result = sanitise(req.message)
    verdict = "flagged" if result.detections else "clean"

    _store_trace(trace_id, TraceEntry(
        payload=req.message,
        detections=result.detections,
        chars_stripped=result.chars_stripped,
        sanitized=result.labeled.value,
    ))

    if req.attack_id is not None:
        sse_verdict = "EVADED_INGRESS" if verdict == "clean" else "BLOCKED_INGRESS"
        background_tasks.add_task(
            _write_attack_log,
            trace_id, session_id, req.attack_id,
            sse_verdict, result.detections, result.chars_stripped,
            False,   # is_breach: unknown at ingress time; pipeline_verdict updated later by agent
            req.message, req.attack_category, req.attack_category_group,
        )
        # GitHub issue removed: breach determination now requires full 7-layer pipeline verdict

    # Write real audit entries — runs after the response is sent.
    background_tasks.add_task(
        _write_audit,
        trace_id, session_id, req.message,
        result.detections, result.chars_stripped, verdict,
    )

    return SubmitResponse(
        trace_id=trace_id,
        session_id=session_id,
        sanitizer_detections=result.detections,
        chars_stripped=result.chars_stripped,
        verdict=verdict,
    )


@router.get("/profile/{persona_key}")
async def profile(persona_key: str, _: None = Depends(verify_playground_token)) -> dict:
    customer_id = PERSONA_CUSTOMER_IDS.get(persona_key)
    if not customer_id:
        raise HTTPException(status_code=404, detail="Unknown persona")

    def _fetch() -> dict:
        try:
            dsn = get_dsn()
        except RuntimeError:
            raise HTTPException(status_code=503, detail="Database unavailable")
        with psycopg.connect(dsn, autocommit=False) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        c.first_name, c.last_name, c.city, c.state,
                        p.policy_number, p.policy_type, p.policy_csl, p.policy_deductible,
                        p.coverage_type, p.policy_expiry_date, p.policy_status,
                        v.auto_make, v.auto_model, v.auto_year,
                        cl.claim_number, cl.incident_type, cl.claim_stage, cl.total_claim_amount
                    FROM customers c
                    JOIN policies p ON p.customer_id = c.customer_id
                    JOIN vehicles v ON v.customer_id = c.customer_id
                    LEFT JOIN claims cl ON cl.customer_id = c.customer_id
                    WHERE c.customer_id = %s
                    LIMIT 1
                    """,
                    (customer_id,),
                )
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Profile not found")
        return dict(row)

    return await asyncio.to_thread(_fetch)
