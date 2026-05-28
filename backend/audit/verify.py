"""CLI job: verify the audit_log hash chain.

Usage:
    uv run python -m audit.verify

Exits 0 if the chain is intact, 1 if any rows are broken.
Emits a security_event row for each outcome (chain_verified / chain_broken).
"""
from __future__ import annotations

import os
import sys
import uuid

import psycopg

from .chain import verify_chain

ADMIN_DSN = os.environ.get(
    "AUDIT_VERIFY_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)


def _emit_security_event(
    conn: psycopg.Connection,
    event_type: str,
    severity: str,
    details: dict,
) -> None:
    with conn.cursor() as cur:
        import json
        cur.execute(
            """
            INSERT INTO security_events (event_id, event_type, severity, details)
            VALUES (%s, %s, %s, %s::jsonb)
            """,
            (str(uuid.uuid4()), event_type, severity, json.dumps(details)),
        )


def main() -> int:
    with psycopg.connect(ADMIN_DSN, autocommit=False) as conn:
        broken = verify_chain(conn)

        if not broken:
            _emit_security_event(
                conn,
                event_type="chain_verified",
                severity="info",
                details={"message": "Audit log hash chain is intact"},
            )
            conn.commit()
            print("audit_log chain OK")
            return 0

        _emit_security_event(
            conn,
            event_type="chain_broken",
            severity="critical",
            details={
                "broken_log_ids": broken,
                "message": f"Hash-chain break detected in {len(broken)} row(s)",
            },
        )
        conn.commit()
        print(
            f"CHAIN BROKEN: {len(broken)} row(s) failed verification: {broken}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
