"""Tool implementations for the Inquiry actor (Sprint 4.1, tasks 4.1.8–4.1.9).

lookup_claim_status
  Deterministic stub returning a CONFIDENTIAL-labelled claim status record.
  Derives claim_number, claim_stage, incident_type, incident_date, and
  total_claim_amount from a SHA-256 hash of claim_id.  Mirrors the claims
  table schema (Doc 03 §2.2) so the stub is coherent with seed values.

  NOTE: Production implementation should SELECT from claims WHERE claim_id = %s
  under the customer's RLS row_context.  RLS enforcement deferred to the sprint
  that adds the real DB read path (P7).

capture_complaint
  Deterministic stub recording a customer complaint and returning ESCALATED
  status.  complaint_id derived from SHA-256 of session_id+category+description
  so the same complaint always maps to the same UUID.  category is validated
  against _COMPLAINT_CATEGORIES; unknown values are coerced to "other".

  NOTE: Production implementation should INSERT into complaints table (Doc 03
  §2.13) and trigger ESCALATED stage transition via the orchestrator.

IFC convention: both tools return Labeled[dict] (CONFIDENTIAL).
"""
from __future__ import annotations

import hashlib
import uuid as _uuid_mod
from datetime import date, timedelta

from agent_system.ifc.labels import DataLabel, Label, Labeled

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

# Base date for deterministic incident_date derivation.
_BASE_DATE = date(2024, 1, 1)
_DATE_RANGE_DAYS = 365

_COMPLAINT_CATEGORIES: list[str] = [
    "service",
    "coverage",
    "decision",
    "process",
    "other",
]


def lookup_claim_status(claim_id: str) -> Labeled[dict]:
    """Deterministic stub claim-status lookup (P3 + P9 via ToolRegistry).

    Args:
        claim_id: claim_id string (UUID or any stable identifier).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            claim_id            — echoed back for traceability
            claim_number        — human-readable CLM-XXXXXXXX (from hash)
            claim_stage         — one of 8 pipeline stages (from hash)
            incident_type       — one of 6 incident types (from hash)
            incident_date       — ISO-8601 date string within 2024 (from hash)
            total_claim_amount  — float dollars, 500–50,000 range (from hash)

    NOTE: Production path queries claims under the customer's RLS policy
    (P7 — row_context set before SELECT; see Dev Doc 03 §2.2).
    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    this function writes nothing to the database.
    """
    h = int(hashlib.sha256(claim_id.encode()).hexdigest(), 16)

    claim_number = f"CLM-{h % 100_000_000:08d}"
    claim_stage = _CLAIM_STAGES[h % len(_CLAIM_STAGES)]
    incident_type = _INCIDENT_TYPES[(h >> 8) % len(_INCIDENT_TYPES)]
    incident_date = (_BASE_DATE + timedelta(days=(h >> 16) % _DATE_RANGE_DAYS)).isoformat()
    # Amount: 500 + deterministic offset up to 49,500 (two decimal precision)
    total_claim_amount = round(500.0 + ((h >> 32) % 49_500) + ((h >> 48) % 100) / 100.0, 2)

    return Labeled(
        value={
            "claim_id": claim_id,
            "claim_number": claim_number,
            "claim_stage": claim_stage,
            "incident_type": incident_type,
            "incident_date": incident_date,
            "total_claim_amount": total_claim_amount,
        },
        label=_LABEL_CONFIDENTIAL,
    )


def capture_complaint(
    session_id: str,
    category: str,
    description: str,
) -> Labeled[dict]:
    """Deterministic stub complaint capture (P3 + P9 via ToolRegistry).

    Args:
        session_id:  Session identifier; echoed in the complaint record.
        category:    One of service/coverage/decision/process/other.
                     Unknown values are coerced to "other".
        description: Free-text description of the complaint.

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            complaint_id — UUID derived from SHA-256(session_id:category:description)
            session_id   — echoed back for traceability
            category     — validated/coerced complaint category
            status       — always "ESCALATED" (triggers stage transition)

    NOTE: Production path INSERTs into complaints table (Doc 03 §2.13) and
    triggers the IDENTITY_VERIFIED → ESCALATED transition via the orchestrator.
    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    this function writes nothing to the database.
    """
    if category not in _COMPLAINT_CATEGORIES:
        category = "other"

    raw_hash = hashlib.sha256(
        f"{session_id}:{category}:{description}".encode()
    ).hexdigest()
    complaint_id = str(_uuid_mod.UUID(raw_hash[:32]))

    return Labeled(
        value={
            "complaint_id": complaint_id,
            "session_id": session_id,
            "category": category,
            "status": "ESCALATED",
        },
        label=_LABEL_CONFIDENTIAL,
    )
