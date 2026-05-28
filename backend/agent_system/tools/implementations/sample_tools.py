"""Sample tool implementations for the P4 capability-token showcase.

These are pure deterministic functions — no DB I/O.  They are registered with
a ToolRegistry at startup and invoked only after a valid capability token has
been verified server-side.
"""
from __future__ import annotations

from typing import Any


def approve_claim(claim_id: str, amount: int) -> dict[str, Any]:
    """Approve a claim for the given amount.  Returns a structured decision."""
    return {
        "claim_id": claim_id,
        "amount": amount,
        "status": "approved",
    }


def score_fraud(claim_id: str) -> dict[str, Any]:
    """Return a deterministic stub fraud score for showcase/testing."""
    return {
        "claim_id": claim_id,
        "fraud_score": 0.04,
        "decision": "CLEAR",
    }
