"""SecureClaim AI — FastAPI application entry point (task 1.1.6)."""
from __future__ import annotations

from fastapi import FastAPI

from app.telemetry import init_telemetry

app = FastAPI(title="SecureClaim AI", version="0.1.0")
init_telemetry(app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "secureclaim-backend"}
