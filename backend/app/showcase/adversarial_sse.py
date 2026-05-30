"""SSE endpoint for adversarial agent live feed (Sprint 4.3.4)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.showcase.events import get_breach_stats, subscribe, unsubscribe

router = APIRouter(prefix="/showcase/sse")

_KEEPALIVE_INTERVAL = 15  # seconds


@router.get("/adversarial")
async def adversarial_stream() -> StreamingResponse:
    async def generate():
        q = subscribe()
        try:
            stats = get_breach_stats()
            yield f"event: breach_count\ndata: {json.dumps(stats)}\n\n"

            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_INTERVAL)
                    yield f"event: attempt\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
