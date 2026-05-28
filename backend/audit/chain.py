"""Audit log hash-chain implementation (task 1.1.4).

Each row's row_hash = sha256(prev_hash_hex + canonical_json_of_all_other_fields).
The first row uses GENESIS_HASH as its prev_hash.
append_log() serializes writers via pg_advisory_xact_lock so the chain
stays consistent under concurrent inserts.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

GENESIS_HASH = "0" * 64


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def canonical_fields(row: dict) -> str:
    data = {k: _serialize(v) for k, v in row.items() if k != "row_hash"}
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def compute_row_hash(prev_hash: str, row_fields: dict) -> str:
    payload = (prev_hash + canonical_fields(row_fields)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def append_log(
    conn: psycopg.Connection,
    *,
    agent_id: str,
    action: str,
    target: str,
    data_label: str,
    trace_id: uuid.UUID | None = None,
    details: dict | None = None,
    security_event: bool = False,
) -> int:
    """Append one row to audit_log and return its log_id.

    conn must be opened with autocommit=False; caller commits.
    conn's DB role must have SELECT on audit_log (use admin/service DSN,
    not an agent role — agents inherit INSERT-only via role_audit_writer).
    """
    with conn.cursor() as cur:
        # Serialise all writers for the duration of this transaction.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('audit_log_append'))")

        # Get the most recent row_hash (or GENESIS_HASH for the very first row).
        cur.execute(
            "SELECT row_hash FROM audit_log ORDER BY log_id DESC LIMIT 1"
        )
        prev_row = cur.fetchone()
        prev_hash: str = prev_row[0] if prev_row else GENESIS_HASH

        # Reserve the log_id before computing the hash so log_id is part of
        # the signed payload — prevents anyone from renumbering rows.
        cur.execute("SELECT nextval('audit_log_log_id_seq')")
        log_id: int = cur.fetchone()[0]

        row_fields: dict = {
            "log_id": log_id,
            "trace_id": trace_id,
            "prev_hash": prev_hash,
            "agent_id": agent_id,
            "action": action,
            "target": target,
            "details": details,
            "data_label": data_label,
            "security_event": security_event,
        }
        row_hash = compute_row_hash(prev_hash, row_fields)

        cur.execute(
            """
            INSERT INTO audit_log (
                log_id, trace_id, prev_hash, row_hash,
                agent_id, action, target, details, data_label, security_event
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s::jsonb, %s, %s
            )
            """,
            (
                log_id,
                trace_id,
                prev_hash,
                row_hash,
                agent_id,
                action,
                target,
                json.dumps(details) if details is not None else None,
                data_label,
                security_event,
            ),
        )

    return log_id


def verify_chain(conn: psycopg.Connection) -> list[int]:
    """Return log_ids of any rows whose hash or prev_hash link is broken."""
    broken: list[int] = []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM audit_log ORDER BY log_id"
        )
        rows = cur.fetchall()

    expected_prev = GENESIS_HASH
    for row in rows:
        row_dict = dict(row)
        # Rebuild the fields dict used during insert (exclude row_hash, include ts).
        fields_for_hash: dict = {
            k: v for k, v in row_dict.items()
            if k not in ("row_hash", "ts")
        }
        # ts is NOT part of the hash payload (DEFAULT now() runs inside PG after
        # nextval; we never include it in compute_row_hash).
        # prev_hash stored in the row must match what we tracked.
        stored_prev = row_dict["prev_hash"]
        if stored_prev != expected_prev:
            broken.append(row_dict["log_id"])
            # Keep going — report all broken rows.
            expected_prev = row_dict["row_hash"]
            continue

        expected_hash = compute_row_hash(stored_prev, fields_for_hash)
        if row_dict["row_hash"] != expected_hash:
            broken.append(row_dict["log_id"])

        expected_prev = row_dict["row_hash"]

    return broken
