"""Shared DATABASE_URL loader — reads from env or falls back to .env file."""
from __future__ import annotations

import os
from pathlib import Path


def get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "DATABASE_URL":
                v = v.strip().strip('"').strip("'")
                if v:
                    return v
    raise RuntimeError(
        "DATABASE_URL not configured — set it in the environment or backend/.env"
    )
