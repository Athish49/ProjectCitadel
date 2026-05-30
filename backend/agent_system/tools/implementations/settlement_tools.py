"""Tool implementations for the Settlement Actor (Sprint 4.2).

Task 4.2.3 — draft_summary
  Customer-facing settlement summary generator.  Fills one of two templates
  (SETTLED / ESCALATED) from structured inputs; returns a CONFIDENTIAL-labelled
  Labeled[dict].  The settlement actor passes `summary` through filter_output
  (P10) before embedding it in SettlementEnvelope — no PII enters the customer
  channel via this path.

Task 4.2.1 — calculate_settlement
  Deterministic stub settlement calculator returning a CONFIDENTIAL-labelled result.
  Derives raw_claim_amount, deductible, offered_amount, and auto_approve_limit from
  a SHA-256 hash of claim_id using the same bit-range convention as lookup_coverage
  (h >> 16 for deductible, h >> 24 for auto_approve_limit) so the two tools always
  agree on the per-claim deductible and limit.  Raw claim amount uses h >> 32.

  NOTE: Production implementation should query the claims + damage_assessments tables
  and apply policy-specific calculation rules.  Deferred to the sprint that adds the
  real DB read path.

Task 4.2.2 — request_payout
  DB-gated payout executor enforcing 5 server-side guards in sequence:
    1. claims.claim_stage = 'DECIDED'           (P2: state-machine integrity)
    2. fraud_scores.decision = 'CLEAR'           (P2: fraud gate)
    3. offered_amount <= auto_approve_limit       (P2: amount ceiling)
    4. pii_vault.bank_account_enc NOT NULL        (payee exists)
    5. settlements.payout_status != 'PROCESSED'  (idempotency)
  Bank details are resolved server-side from pii_vault; they never enter LLM context.
  Raises PayoutGuardError on any guard failure; ToolRegistry logs tool_call_handler_error.

  NOTE: Guard 1 relies on DB-persisted claim_stage.  The orchestrator currently only
  updates in-memory state; task 4.2.4 must add UPDATE claims SET claim_stage = ...
  to the orchestrator transition path so this guard can be satisfied end-to-end.
"""
from __future__ import annotations

import hashlib
import uuid as _uuid_mod

import psycopg

from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.tools.implementations.claims_tools import (
    AUTO_APPROVE_LIMITS,
    DEDUCTIBLES,
)

# ---------------------------------------------------------------------------
# Claim amount catalogue — gross claim amounts before deductible.
# Range spans minor repairs through total-loss payouts.
# ---------------------------------------------------------------------------

_CLAIM_AMOUNTS: list[float] = [
    1_200.0,
    2_500.0,
    4_800.0,
    6_500.0,
    8_000.0,
    12_000.0,
    16_500.0,
    22_000.0,
    28_000.0,
    35_000.0,
]

_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)


# ---------------------------------------------------------------------------
# Tool: calculate_settlement — task 4.2.1
# ---------------------------------------------------------------------------


def calculate_settlement(claim_id: str) -> Labeled[dict]:
    """Deterministic stub settlement calculator (P3 + P9 via ToolRegistry).

    Args:
        claim_id: claim_id string (UUID or any stable identifier).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            claim_id            — echoed back for traceability
            raw_claim_amount    — gross claim amount before deductible (float)
            deductible_applied  — deductible amount (float; same derivation as lookup_coverage)
            offered_amount      — net payable: max(0, raw - deductible) (float)
            auto_approve_limit  — per-claim auto-approval ceiling (float; same as lookup_coverage)

    The settlement actor uses offered_amount vs. auto_approve_limit to determine
    whether to call request_payout (SETTLED path) or surface ESCALATED to the
    orchestrator.  Both values are derived from the same hash as lookup_coverage
    so the state machine guards in transitions.py can be satisfied deterministically.

    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    this function writes nothing to the database.
    """
    h = int(hashlib.sha256(claim_id.encode()).hexdigest(), 16)
    deductible = float(DEDUCTIBLES[(h >> 16) % len(DEDUCTIBLES)])
    auto_approve_limit = float(AUTO_APPROVE_LIMITS[(h >> 24) % len(AUTO_APPROVE_LIMITS)])
    raw_claim_amount = _CLAIM_AMOUNTS[(h >> 32) % len(_CLAIM_AMOUNTS)]
    offered_amount = max(0.0, raw_claim_amount - deductible)

    return Labeled(
        value={
            "claim_id":           claim_id,
            "raw_claim_amount":   raw_claim_amount,
            "deductible_applied": deductible,
            "offered_amount":     offered_amount,
            "auto_approve_limit": auto_approve_limit,
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Guard error — task 4.2.2
# ---------------------------------------------------------------------------


class PayoutGuardError(Exception):
    """Raised when a server-side request_payout guard fails.

    ToolRegistry catches this as handler_error and logs tool_call_handler_error.
    Calling actor inspects result.handler_error.reason and .guard for audit.
    """

    def __init__(self, reason: str, guard: str) -> None:
        super().__init__(f"payout denied ({guard}): {reason}")
        self.reason = reason
        self.guard = guard  # "stage" | "fraud" | "amount" | "payee" | "idempotency"


# ---------------------------------------------------------------------------
# Tool: request_payout — task 4.2.2
# ---------------------------------------------------------------------------


def request_payout(claim_id: str, *, conn: psycopg.Connection) -> Labeled[dict]:
    """DB-gated payout executor (P2 + P4). Guards run in strict sequence.

    Args:
        claim_id: claim_id string matching the claims table primary key.
        conn:     psycopg connection (keyword-only; bound via functools.partial
                  before registry.register so it stays out of ToolRegistry params).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            claim_id          — echoed back for traceability
            payout_status     — always "PROCESSED" on success
            payout_reference  — server-generated UUID (settlement receipt)
            offered_amount    — amount disbursed (float)

    Raises:
        PayoutGuardError: if any of the 5 guards fails. guard attribute names
            the failing guard: "stage", "fraud", "amount", "payee", "idempotency".

    NOTE: Guard 1 requires claim_stage = 'DECIDED' in the DB.  Until task 4.2.4
    wires the orchestrator transition to UPDATE claims SET claim_stage = 'DECIDED',
    this guard will only pass in integration tests that seed the DB directly.
    """
    with conn.cursor() as cur:
        # Guard 1: claim must be in DECIDED stage
        cur.execute("SELECT claim_stage FROM claims WHERE claim_id = %s", (claim_id,))
        row = cur.fetchone()
        if row is None:
            raise PayoutGuardError(f"claim {claim_id!r} not found", "stage")
        if row[0] != "DECIDED":
            raise PayoutGuardError(f"claim_stage={row[0]!r}, expected 'DECIDED'", "stage")

        # Guard 2: fraud decision must be CLEAR
        cur.execute("SELECT decision FROM fraud_scores WHERE claim_id = %s", (claim_id,))
        fs_row = cur.fetchone()
        if fs_row is None:
            raise PayoutGuardError("no fraud score on record", "fraud")
        if fs_row[0] != "CLEAR":
            raise PayoutGuardError(f"fraud_decision={fs_row[0]!r}, expected 'CLEAR'", "fraud")

        # Guard 3: offered_amount must not exceed auto_approve_limit
        s = calculate_settlement(claim_id).value
        offered_amount = s["offered_amount"]
        auto_approve_limit = s["auto_approve_limit"]
        if offered_amount > auto_approve_limit:
            raise PayoutGuardError(
                f"offered_amount={offered_amount} > auto_approve_limit={auto_approve_limit}",
                "amount",
            )
        deductible_applied = s["deductible_applied"]

        # Guard 4: payee bank details must be on file (resolved server-side, never exposed to LLM)
        cur.execute(
            "SELECT v.bank_account_enc FROM claims c "
            "JOIN pii_vault v ON v.customer_id = c.customer_id "
            "WHERE c.claim_id = %s",
            (claim_id,),
        )
        payee_row = cur.fetchone()
        if payee_row is None or payee_row[0] is None:
            raise PayoutGuardError("no bank account on file for session-bound payee", "payee")

        # Guard 5: idempotency — reject if already PROCESSED
        cur.execute("SELECT payout_status FROM settlements WHERE claim_id = %s", (claim_id,))
        existing = cur.fetchone()
        if existing is not None and existing[0] == "PROCESSED":
            raise PayoutGuardError("already paid", "idempotency")

        # All guards passed — record the payout
        payout_reference = str(_uuid_mod.uuid4())
        cur.execute(
            """INSERT INTO settlements
                 (claim_id, offered_amount, deductible_applied,
                  approval_status, payout_status, payout_reference)
               VALUES (%s, %s, %s, 'AUTO_APPROVED', 'PROCESSED', %s)
               ON CONFLICT (claim_id) DO UPDATE SET
                 offered_amount    = EXCLUDED.offered_amount,
                 deductible_applied = EXCLUDED.deductible_applied,
                 approval_status   = 'AUTO_APPROVED',
                 payout_status     = 'PROCESSED',
                 payout_reference  = EXCLUDED.payout_reference
            """,
            (claim_id, offered_amount, deductible_applied, payout_reference),
        )

    return Labeled(
        value={
            "claim_id":          claim_id,
            "payout_status":     "PROCESSED",
            "payout_reference":  payout_reference,
            "offered_amount":    offered_amount,
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Summary templates — task 4.2.3
# ---------------------------------------------------------------------------

_SUMMARY_TEMPLATES: dict[str, str] = {
    "SETTLED": (
        "Your claim {claim_id} has been approved and a payment of ${offered_amount:,.2f} "
        "has been scheduled (reference: {payout_reference}). "
        "Funds will be deposited within 5–7 business days."
    ),
    "ESCALATED": (
        "Your claim {claim_id} has been referred to our specialist team for manual review. "
        "A claims specialist will contact you within 2 business days."
    ),
}


# ---------------------------------------------------------------------------
# Tool: draft_summary — task 4.2.3
# ---------------------------------------------------------------------------


def draft_summary(
    claim_id: str,
    outcome: str,
    offered_amount: float,
    payout_reference: str,
) -> Labeled[dict]:
    """Customer-facing settlement summary (P10 via egress filter in settlement actor).

    Args:
        claim_id:          claim_id string for traceability.
        outcome:           "SETTLED" or "ESCALATED" (controls template selection).
        offered_amount:    approved payout amount (float; 0.0 for ESCALATED path).
        payout_reference:  server-generated UUID from request_payout ("" for ESCALATED).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            claim_id         — echoed back
            outcome          — echoed back
            offered_amount   — echoed back
            payout_reference — echoed back
            summary          — formatted customer-facing text

    The settlement actor passes summary through filter_output (P10) before
    embedding it in SettlementEnvelope.  This function writes nothing to the DB.
    """
    template = _SUMMARY_TEMPLATES.get(outcome, _SUMMARY_TEMPLATES["ESCALATED"])
    summary = template.format(
        claim_id=claim_id,
        offered_amount=offered_amount,
        payout_reference=payout_reference or "N/A",
    )
    return Labeled(
        value={
            "claim_id":          claim_id,
            "outcome":           outcome,
            "offered_amount":    offered_amount,
            "payout_reference":  payout_reference,
            "summary":           summary,
        },
        label=_LABEL_CONFIDENTIAL,
    )
