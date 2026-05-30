"""Showcase playground endpoint (TAD §7.2) — Sprint 4.3.2 / 4.3.4."""
from __future__ import annotations

import logging
import os
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from agent_system.sanitisation.text import sanitise
from app.showcase.events import AdversarialEvent, publish

log = logging.getLogger(__name__)

router = APIRouter(prefix="/showcase/playground")


class SubmitRequest(BaseModel):
    message: str
    session_id: str | None = None
    attack_id: int | None = None


class SubmitResponse(BaseModel):
    trace_id: str
    session_id: str
    sanitizer_detections: list[str]
    chars_stripped: int
    verdict: str  # "clean" | "flagged"


async def _open_github_issue(trace_id: str, session_id: str, attack_id: int) -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPO", "")
    if not token or not repo:
        log.warning("GITHUB_TOKEN or GITHUB_REPO not set — skipping issue creation")
        return
    title = f"[Adversarial] Breach: attack_id={attack_id} trace={trace_id[:8]}"
    body = (
        f"The adversarial agent evaded ingress sanitization.\n\n"
        f"- **attack_id**: `{attack_id}`\n"
        f"- **trace_id**: `{trace_id}`\n"
        f"- **session_id**: `{session_id}`\n"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.github.com/repos/{repo}/issues",
                json={"title": title, "body": body, "labels": ["adversarial", "security"]},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            resp.raise_for_status()
            log.info("github_issue_opened url=%s", resp.json().get("html_url"))
    except Exception as exc:
        log.warning("github_issue_open_failed trace_id=%s error=%s", trace_id, exc)


@router.post("/submit", response_model=SubmitResponse)
async def submit(req: SubmitRequest, background_tasks: BackgroundTasks) -> SubmitResponse:
    session_id = req.session_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    result = sanitise(req.message)
    verdict = "flagged" if result.detections else "clean"

    if req.attack_id is not None:
        sse_verdict = "EVADED_INGRESS" if verdict == "clean" else "BLOCKED_INGRESS"
        publish(AdversarialEvent(
            trace_id=trace_id,
            session_id=session_id,
            attack_id=req.attack_id,
            verdict=sse_verdict,
            sanitizer_detections=result.detections,
            chars_stripped=result.chars_stripped,
        ))
        if verdict == "clean":
            background_tasks.add_task(_open_github_issue, trace_id, session_id, req.attack_id)

    return SubmitResponse(
        trace_id=trace_id,
        session_id=session_id,
        sanitizer_detections=result.detections,
        chars_stripped=result.chars_stripped,
        verdict=verdict,
    )
