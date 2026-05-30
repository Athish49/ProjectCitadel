"""SecureClaim AI — FastAPI application entry point (task 1.1.6)."""
from __future__ import annotations

from fastapi import FastAPI

from app.showcase.adversarial_sse import router as adversarial_sse_router
from app.showcase.playground import router as playground_router
from app.telemetry import init_telemetry

app = FastAPI(title="SecureClaim AI", version="0.1.0")
init_telemetry(app)
app.include_router(playground_router)
app.include_router(adversarial_sse_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "secureclaim-backend"}
