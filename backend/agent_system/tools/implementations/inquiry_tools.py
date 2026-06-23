"""Tool implementations for the Inquiry actor (Sprint 4.1, tasks 4.1.8–4.1.9).

lookup_claim_status  — SELECT from claims table (CONFIDENTIAL, P3 + P9)
capture_complaint    — INSERT into complaints table (CONFIDENTIAL, P3 + P9)

Both tools require a DB connection injected by ToolRegistry via ContextVar
(agent_system.tools.tool_context.get_tool_conn).

capture_complaint additionally requires customer_id to perform the DB INSERT
(complaints.customer_id is NOT NULL).  When customer_id is None the function
still returns an ESCALATED envelope but omits the DB write; the canonical call
path always provides customer_id.
"""
from __future__ import annotations

import uuid as _uuid_mod

from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.tools.tool_context import get_tool_conn

_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)

_CLAIM_STAGES: list[str] = [
    "INTAKE",
    "IDENTITY_PENDING",
    "IDENTITY_VERIFIED",
    "PROCESSING",
    "DECIDED",
    "SETTLED",
    "CLOSED",
    "ESCALATED",
]

_INCIDENT_TYPES: list[str] = [
    "collision",
    "theft",
    "weather",
    "vandalism",
    "fire",
    "animal_strike",
]

_COMPLAINT_CATEGORIES: list[str] = [
    "service",
    "coverage",
    "decision",
    "process",
    "other",
]


def _to_uuid(value: str) -> _uuid_mod.UUID:
    """Parse *value* as UUID; derive a stable UUID5 if not a valid UUID string."""
    try:
        return _uuid_mod.UUID(value)
    except ValueError:
        return _uuid_mod.uuid5(_uuid_mod.NAMESPACE_DNS, value)


# ---------------------------------------------------------------------------
# Tool: lookup_claim_status
# ---------------------------------------------------------------------------


def lookup_claim_status(claim_id: str) -> Labeled[dict]:
    """Return current status fields for *claim_id* from the claims table.

    Args:
        claim_id: claim_id (UUID string) subject to the caller's RLS context.

    Returns:
        Labeled[dict] (CONFIDENTIAL) with claim_id, claim_number, claim_stage,
        incident_type, incident_date (ISO-8601 string), total_claim_amount (float).

    Raises:
        ValueError: when no row exists for claim_id under the current RLS context.
    """
    conn = get_tool_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT claim_number, claim_stage, incident_type,
                   incident_date, total_claim_amount
            FROM claims
            WHERE claim_id = %s
            """,
            (claim_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise ValueError(f"No claim found for claim_id={claim_id!r}")

    claim_number, claim_stage, incident_type, incident_date, total_claim_amount = row

    return Labeled(
        value={
            "claim_id":           claim_id,
            "claim_number":       claim_number,
            "claim_stage":        claim_stage,
            "incident_type":      incident_type,
            "incident_date":      (
                incident_date.isoformat()
                if hasattr(incident_date, "isoformat")
                else str(incident_date)
            ),
            "total_claim_amount": float(total_claim_amount),
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Tool: capture_complaint
# ---------------------------------------------------------------------------


def capture_complaint(
    session_id: str,
    category: str,
    description: str,
    customer_id: str | None = None,
) -> Labeled[dict]:
    """Record a customer complaint and return ESCALATED status.

    Args:
        session_id:   Session identifier (string or UUID string).
        category:     One of service/coverage/decision/process/other.
                      Unknown values are coerced to "other".
        description:  Free-text description of the complaint.
        customer_id:  Customer UUID string.  Required for the DB INSERT;
                      when None the function returns an ESCALATED envelope
                      without writing to the complaints table.

    Returns:
        Labeled[dict] (CONFIDENTIAL) with complaint_id, session_id, category, status.
    """
    if category not in _COMPLAINT_CATEGORIES:
        category = "other"

    # Derive a stable complaint_id from the call inputs so that the same
    # complaint always produces the same UUID.
    complaint_id = str(
        _uuid_mod.uuid5(
            _uuid_mod.NAMESPACE_DNS,
            f"{session_id}:{category}:{description}",
        )
    )

    if customer_id is not None:
        conn = get_tool_conn()
        session_uuid = _to_uuid(session_id)
        customer_uuid = _uuid_mod.UUID(customer_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO complaints
                    (complaint_id, session_id, customer_id,
                     category, description, status)
                VALUES (%s, %s, %s, %s, %s, 'ESCALATED')
                ON CONFLICT (complaint_id) DO NOTHING
                """,
                (complaint_id, session_uuid, customer_uuid, category, description),
            )

    return Labeled(
        value={
            "complaint_id": complaint_id,
            "session_id":   session_id,
            "category":     category,
            "status":       "ESCALATED",
        },
        label=_LABEL_CONFIDENTIAL,
    )
