"""Real-agents end-to-end integration test (task 4.2.4).

Verifies 5 SETTLED paths and 2 ESCALATED paths against real seed data:

  SETTLED (×5)         score_fraud=CLEAR, offered ≤ limit
                        claim_stage='DECIDED' written to DB by request_transition
                        → request_payout guards all pass → payout_status='approved'

  AMOUNT_ESCALATED (×1) score_fraud=CLEAR, offered > limit
                        settlement actor skips request_payout → payout_status='escalated'

  FRAUD_ESCALATED (×1)  score_fraud hash returns FLAG
                        orchestrator transitions DECIDED → ESCALATED directly
                        no settlement actor call

Claim IDs are derived deterministically from uuid5 so calculate_settlement and
score_fraud hash outcomes are stable across runs.

LLM clients are mocked; all other I/O uses the real implementation:
  - Ed25519 key material and CapabilityToken verification (P4)
  - ToolRegistry replay protection (capability_token_log writes)
  - DB guards inside request_payout (5-guard sequence)
  - P10 egress filter on settlement summary

Prerequisites: make up && make migrate
Run via: make test-real-agents-e2e
"""
from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock

import psycopg
import pytest

from agent_system.actors.claims_processor_actor import (
    ACTOR_AGENT_ID as CLAIMS_PROCESSOR_AGENT_ID,
    run_claims_processor_actor,
)
from agent_system.actors.settlement_actor import (
    ACTOR_AGENT_ID as SETTLEMENT_AGENT_ID,
    run_settlement_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.orchestrator.state import Orchestrator
from agent_system.orchestrator.transitions import ClaimStage, TransitionGuardContext
from agent_system.tools.capability_tokens import CapabilityToken, issue_token, persist_issuance
from agent_system.tools.implementations.settlement_tools import calculate_settlement

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)

# Fixed namespace for deterministic claim IDs (stable across runs).
_TEST_NS = uuid.UUID("12345678-1234-5678-1234-567812345678")


def _cid(i: int) -> str:
    return str(uuid.uuid5(_TEST_NS, f"e2e-{i:03d}"))


# Claim indices with known deterministic outcomes (verified via calculate_settlement + score_fraud hashes).
# SETTLED:         score_fraud returns CLEAR  AND  offered_amount <= auto_approve_limit
# AMOUNT_ESCALATED: score_fraud returns CLEAR AND  offered_amount >  auto_approve_limit
# FRAUD_ESCALATED:  score_fraud returns FLAG  (i=0; offered=19500 > limit=5000 too)
_SETTLED_INDICES = [2, 6, 13, 15, 16]
_AMOUNT_ESC_IDX = 9
_FRAUD_ESC_IDX = 0


# ---------------------------------------------------------------------------
# DB infrastructure
# ---------------------------------------------------------------------------


def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def setup_module(_: object) -> None:
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
        conn.commit()


def teardown_module(_: object) -> None:
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
        conn.commit()


# ---------------------------------------------------------------------------
# DB seeding helpers
# ---------------------------------------------------------------------------


def _seed_claim(
    cur: psycopg.Cursor,
    claim_id: str,
    *,
    fraud_decision: str = "CLEAR",
    has_bank_account: bool = True,
) -> tuple[str, str]:
    """Insert customer, policy, pii_vault, claim, and fraud_scores rows.

    Returns (customer_id, policy_id) for use in teardown.

    NOTE: Uses the postgres superuser connection which bypasses column-level
    grants and RLS.  The role_settlement_actor pii_vault grant restriction is
    exercised in test_agent_roles.py, not here.
    """
    customer_id = str(uuid.uuid4())
    policy_id = str(uuid.uuid4())
    short = claim_id[:8]

    cur.execute(
        "INSERT INTO customers"
        " (customer_id, policy_number, first_name, last_name, email, date_of_birth)"
        " VALUES (%s, %s, 'Test', 'User', %s, '1985-01-01')",
        (customer_id, f"POL-{short}", f"{short}@test.invalid"),
    )
    cur.execute(
        "INSERT INTO policies (policy_id, policy_number, customer_id) VALUES (%s, %s, %s)",
        (policy_id, f"POL-{short}", customer_id),
    )
    bank_enc = b"\xde\xad\xbe\xef" if has_bank_account else None
    cur.execute(
        "INSERT INTO pii_vault (customer_id, ssn_hash, ssn_last4, bank_account_enc)"
        " VALUES (%s, %s, '1234', %s)",
        (customer_id, b"\x00" * 32, bank_enc),
    )
    cur.execute(
        "INSERT INTO claims (claim_id, claim_number, customer_id, policy_id, claim_stage)"
        " VALUES (%s, %s, %s, %s, 'INTAKE')",
        (claim_id, f"CLM-{short}", customer_id, policy_id),
    )
    cur.execute(
        "INSERT INTO fraud_scores (claim_id, risk_score, decision) VALUES (%s, %s, %s)",
        (claim_id, 10 if fraud_decision == "CLEAR" else 50, fraud_decision),
    )
    return customer_id, policy_id


def _teardown_claim(
    conn: psycopg.Connection,
    claim_id: str,
    customer_id: str,
    policy_id: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM settlements WHERE claim_id = %s", (claim_id,))
        cur.execute("DELETE FROM fraud_scores WHERE claim_id = %s", (claim_id,))
        cur.execute("DELETE FROM claims WHERE claim_id = %s", (claim_id,))
        cur.execute("DELETE FROM pii_vault WHERE customer_id = %s", (customer_id,))
        cur.execute("DELETE FROM policies WHERE policy_id = %s", (policy_id,))
        cur.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _tool_block(name: str, input_: dict, block_id: str | None = None) -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = input_
    b.id = block_id or f"tu_{name}"
    return b


def _text_block(text: str = "Done.") -> MagicMock:
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _response(content: list, stop_reason: str = "tool_use") -> MagicMock:
    r = MagicMock()
    r.content = content
    r.stop_reason = stop_reason
    return r


def _mock_client(*responses: MagicMock) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _processor_tokens(
    km: KeypairManager, conn: psycopg.Connection
) -> dict[str, CapabilityToken]:
    tokens = {
        t: issue_token(km, agent_id=CLAIMS_PROCESSOR_AGENT_ID, tool=t, scope={})
        for t in (
            "classify_damage",
            "lookup_coverage",
            "score_fraud",
            "search_policy_docs",
            "search_fraud_rules",
        )
    }
    for token in tokens.values():
        persist_issuance(conn, token)
    conn.commit()
    return tokens


def _settlement_tokens(
    km: KeypairManager, conn: psycopg.Connection
) -> dict[str, CapabilityToken]:
    tokens = {
        t: issue_token(km, agent_id=SETTLEMENT_AGENT_ID, tool=t, scope={})
        for t in ("calculate_settlement", "request_payout", "draft_summary")
    }
    for token in tokens.values():
        persist_issuance(conn, token)
    conn.commit()
    return tokens


# ---------------------------------------------------------------------------
# LLM mock response factories
# ---------------------------------------------------------------------------


def _processor_mock(cid: str) -> MagicMock:
    """Mock: call classify_damage + lookup_coverage + score_fraud then end."""
    return _mock_client(
        _response(
            [
                _tool_block("classify_damage", {"evidence_ref": f"ev-{cid[:8]}"}),
                _tool_block("lookup_coverage", {"claim_id": cid}),
                _tool_block("score_fraud", {"claim_id": cid}),
            ],
            "tool_use",
        ),
        _response([_text_block()], "end_turn"),
    )


def _settlement_mock_settled(cid: str) -> MagicMock:
    """Mock: calc → payout → summary → end (SETTLED path)."""
    offered = calculate_settlement(cid).value["offered_amount"]
    return _mock_client(
        _response([_tool_block("calculate_settlement", {"claim_id": cid})], "tool_use"),
        _response([_tool_block("request_payout", {"claim_id": cid})], "tool_use"),
        _response(
            [
                _tool_block(
                    "draft_summary",
                    {
                        "claim_id": cid,
                        "outcome": "SETTLED",
                        "offered_amount": offered,
                        "payout_reference": "e2e-placeholder-ref",
                    },
                )
            ],
            "tool_use",
        ),
        _response([_text_block()], "end_turn"),
    )


def _settlement_mock_amount_esc(cid: str) -> MagicMock:
    """Mock: calc → summary (ESCALATED, no payout) → end."""
    offered = calculate_settlement(cid).value["offered_amount"]
    return _mock_client(
        _response([_tool_block("calculate_settlement", {"claim_id": cid})], "tool_use"),
        _response(
            [
                _tool_block(
                    "draft_summary",
                    {
                        "claim_id": cid,
                        "outcome": "ESCALATED",
                        "offered_amount": offered,
                        "payout_reference": "",
                    },
                )
            ],
            "tool_use",
        ),
        _response([_text_block()], "end_turn"),
    )


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------


def _run_pipeline(
    conn: psycopg.Connection,
    cid: str,
    *,
    processor_mock: MagicMock,
    settlement_mock: MagicMock | None,
    km: KeypairManager,
    session_id: str,
) -> tuple:
    """Run the full pipeline for one claim.

    settlement_mock=None skips the settlement actor (fraud-escalated path).
    Returns (processor_envelope, settlement_envelope | None).

    Commit strategy: the caller commits after each transition; actors commit
    internally after each ToolRegistry invoke.  All writes are visible to
    subsequent DB reads on the same connection.
    """
    pub = km.public_key_bytes
    orchestrator = Orchestrator(session_id)

    # Drive orchestrator through early stages (no actors needed for these)
    orchestrator.request_transition(
        ClaimStage.IDENTITY_PENDING, TransitionGuardContext(intake_complete=True)
    )
    orchestrator.request_transition(
        ClaimStage.IDENTITY_VERIFIED, TransitionGuardContext(identity_verified=True)
    )
    orchestrator.request_transition(ClaimStage.PROCESSING, TransitionGuardContext())

    # ── Claims processor (real ToolRegistry + DB, mocked LLM) ────────────────
    proc_env = run_claims_processor_actor(
        claim_id=cid,
        evidence_ref=f"ev-{cid[:8]}",
        pre_issued_tokens=_processor_tokens(km, conn),
        orchestrator_public_key=pub,
        client=processor_mock,
        session_id=session_id,
        conn=conn,
    )
    conn.commit()

    # ── PROCESSING → DECIDED: write claim_stage to DB ────────────────────────
    # Required so request_payout Guard 1 (claim_stage='DECIDED') passes.
    orchestrator.request_transition(
        ClaimStage.DECIDED,
        TransitionGuardContext(
            damage_assessment=proc_env.damage_assessment,
            coverage_calculation=proc_env.coverage_calculation,
            fraud_decision=proc_env.fraud_signal,
        ),
        claim_id=cid,
        conn=conn,
    )
    conn.commit()

    s = calculate_settlement(cid).value
    limit = float(s["auto_approve_limit"])

    if settlement_mock is None:
        # Fraud-escalated: skip settlement actor, transition straight to ESCALATED
        orchestrator.request_transition(
            ClaimStage.ESCALATED,
            TransitionGuardContext(
                fraud_decision=proc_env.fraud_signal,
                settlement_amount=None,
                auto_approve_limit=limit,
            ),
            claim_id=cid,
            conn=conn,
        )
        conn.commit()
        return proc_env, None

    # ── Settlement actor (real DB guards, mocked LLM) ─────────────────────────
    settlement_env = run_settlement_actor(
        claim_id=cid,
        pre_issued_tokens=_settlement_tokens(km, conn),
        orchestrator_public_key=pub,
        client=settlement_mock,
        session_id=session_id,
        conn=conn,
    )
    conn.commit()

    # ── Final orchestrator transition ─────────────────────────────────────────
    if settlement_env.payout_status == "approved":
        orchestrator.request_transition(
            ClaimStage.SETTLED,
            TransitionGuardContext(
                fraud_decision=proc_env.fraud_signal,
                settlement_amount=settlement_env.settlement_amount,
                auto_approve_limit=limit,
            ),
            claim_id=cid,
            conn=conn,
        )
        conn.commit()
        orchestrator.request_transition(
            ClaimStage.CLOSED, TransitionGuardContext(), claim_id=cid, conn=conn
        )
        conn.commit()
    else:
        orchestrator.request_transition(
            ClaimStage.ESCALATED,
            TransitionGuardContext(
                fraud_decision=proc_env.fraud_signal,
                settlement_amount=settlement_env.settlement_amount,
                auto_approve_limit=limit,
            ),
            claim_id=cid,
            conn=conn,
        )
        conn.commit()

    return proc_env, settlement_env


# ---------------------------------------------------------------------------
# Tests — SETTLED paths (×5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("idx", _SETTLED_INDICES)
def test_settled_pipeline(idx: int) -> None:
    """Full pipeline for a SETTLED claim: DB claim_stage updated to DECIDED,
    all request_payout guards pass, envelope.payout_status == 'approved'."""
    cid = _cid(idx)
    session_id = f"e2e-settled-{idx}"
    km = KeypairManager.generate("orchestrator")

    conn = _admin()
    customer_id: str | None = None
    policy_id: str | None = None
    try:
        with conn.cursor() as cur:
            customer_id, policy_id = _seed_claim(cur, cid)
        conn.commit()

        _, envelope = _run_pipeline(
            conn,
            cid,
            processor_mock=_processor_mock(cid),
            settlement_mock=_settlement_mock_settled(cid),
            km=km,
            session_id=session_id,
        )

        assert envelope is not None
        assert envelope.payout_status == "approved", (
            f"[idx={idx}] Expected payout_status='approved', got {envelope.payout_status!r}"
        )
        expected_amount = calculate_settlement(cid).value["offered_amount"]
        assert envelope.settlement_amount == expected_amount, (
            f"[idx={idx}] settlement_amount mismatch: {envelope.settlement_amount} != {expected_amount}"
        )
        assert envelope.claim_id == cid
    finally:
        conn.close()
        if customer_id and policy_id:
            with _admin() as c:
                _teardown_claim(c, cid, customer_id, policy_id)


# ---------------------------------------------------------------------------
# Tests — ESCALATED paths (×2)
# ---------------------------------------------------------------------------


def test_amount_escalated_pipeline() -> None:
    """Amount-escalated path: offered_amount > auto_approve_limit causes the
    settlement actor to skip request_payout → payout_status='escalated'."""
    cid = _cid(_AMOUNT_ESC_IDX)
    session_id = "e2e-amount-esc"
    km = KeypairManager.generate("orchestrator")

    s = calculate_settlement(cid).value
    assert s["offered_amount"] > s["auto_approve_limit"], (
        f"Precondition: offered ({s['offered_amount']}) must exceed limit ({s['auto_approve_limit']})"
    )

    conn = _admin()
    customer_id: str | None = None
    policy_id: str | None = None
    try:
        with conn.cursor() as cur:
            customer_id, policy_id = _seed_claim(cur, cid, has_bank_account=False)
        conn.commit()

        _, envelope = _run_pipeline(
            conn,
            cid,
            processor_mock=_processor_mock(cid),
            settlement_mock=_settlement_mock_amount_esc(cid),
            km=km,
            session_id=session_id,
        )

        assert envelope is not None
        assert envelope.payout_status == "escalated"
    finally:
        conn.close()
        if customer_id and policy_id:
            with _admin() as c:
                _teardown_claim(c, cid, customer_id, policy_id)


def test_fraud_escalated_pipeline() -> None:
    """Fraud-escalated path: score_fraud hash returns FLAG for this claim_id,
    so the claims processor sets fraud_signal='FLAG', the orchestrator
    transitions DECIDED → ESCALATED, and no settlement actor is called."""
    cid = _cid(_FRAUD_ESC_IDX)
    session_id = "e2e-fraud-esc"
    km = KeypairManager.generate("orchestrator")

    conn = _admin()
    customer_id: str | None = None
    policy_id: str | None = None
    try:
        with conn.cursor() as cur:
            # fraud_decision in DB is set to FLAG for consistency; the
            # claims processor itself uses the hash-based score_fraud() tool.
            customer_id, policy_id = _seed_claim(cur, cid, fraud_decision="FLAG")
        conn.commit()

        proc_env, settlement_env = _run_pipeline(
            conn,
            cid,
            processor_mock=_processor_mock(cid),
            settlement_mock=None,
            km=km,
            session_id=session_id,
        )

        assert settlement_env is None, "No settlement actor should run on fraud-escalated path"
        assert proc_env.fraud_signal in ("FLAG", "DENY"), (
            f"Expected FLAG/DENY from claims processor, got {proc_env.fraud_signal!r}"
        )
    finally:
        conn.close()
        if customer_id and policy_id:
            with _admin() as c:
                _teardown_claim(c, cid, customer_id, policy_id)
