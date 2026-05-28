"""
Migration runner for SecureClaim AI.

Applies numbered SQL files from db/migrations/ in lexicographic order.
Each migration runs in its own transaction; if it fails the transaction is
rolled back and the version is NOT recorded — safe to retry after fixing.

Usage:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/secureclaim \
        uv run python -m db.migrate
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_ENSURE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(100) PRIMARY KEY,
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
)
"""


def run_migrations(dsn: str) -> int:
    """Apply pending migrations. Returns the count of migrations applied."""
    applied = 0

    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(_ENSURE_TABLE)
        conn.commit()

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        if not migration_files:
            print("db/migrate: no migration files found in", MIGRATIONS_DIR)
            return 0

        for path in migration_files:
            version = path.stem

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s", (version,)
                )
                already_applied = cur.fetchone() is not None

            if already_applied:
                print(f"  [skip]  {version}")
                continue

            print(f"  [apply] {version}", end="", flush=True)
            sql = path.read_text()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
                    )
                conn.commit()
                applied += 1
                print(" — ok")
            except Exception as exc:
                conn.rollback()
                print(f" — FAILED: {exc}")
                raise

    return applied


def main() -> None:
    dsn = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/secureclaim",
    )
    print(f"db/migrate: connecting to {dsn.split('@')[-1]}")  # omit credentials from log
    count = run_migrations(dsn)
    print(f"db/migrate: done ({count} migration(s) applied)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"db/migrate: fatal — {exc}", file=sys.stderr)
        sys.exit(1)
