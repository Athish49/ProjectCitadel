"""Shared DATABASE_URL accessor — delegates to the central config."""
from __future__ import annotations

from app.config import cfg


def get_dsn() -> str:
    if not cfg.database_url:
        raise RuntimeError(
            "DATABASE_URL not configured — set it in the environment or backend/.env"
        )
    return cfg.database_url
