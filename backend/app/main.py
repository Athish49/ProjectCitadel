"""SecureClaim AI — FastAPI application entry point (task 1.1.6)."""
from __future__ import annotations

import logging

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from app.showcase.adversarial_sse import router as adversarial_sse_router
from app.showcase.audit_sse import router as audit_sse_router
from app.showcase.playground import router as playground_router
from app.showcase.playground_sse import router as playground_sse_router
from app.telemetry import init_telemetry

log = logging.getLogger(__name__)

app = FastAPI(title="SecureClaim AI", version="0.1.0")
init_telemetry(app)
app.include_router(playground_router)
app.include_router(playground_sse_router)
app.include_router(adversarial_sse_router)
app.include_router(audit_sse_router)


@app.on_event("startup")
async def _log_model_provider() -> None:
    """Log the active LLM provider at startup so it's visible before the first request."""
    try:
        from app.model_provider import detect_provider
        provider, model, _ = detect_provider()
        log.info("LLM provider: %s | model: %s", provider.value.upper(), model)
    except RuntimeError as exc:
        log.warning("LLM provider: NONE CONFIGURED — %s", exc)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "secureclaim-backend"}
