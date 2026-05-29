"""End-to-end vertical slice integration test (task 2.2.1).

Flow: chat → intake parser (P1) → intake actor (P4) → identity verifier (P4)
      → claims processor stub → settlement actor stub → CLOSED

Verifies:
  - All 6 orchestrator stage transitions succeed on the happy path
  - Final stage is ClaimStage.CLOSED
  - Hash-chained audit log is intact after the full run (verify_chain == [])
  - Every actor emits at least one audit row under its agent_id
  - No security_event=True rows on the happy path

LLM calls are mocked; real Ed25519 key material and capability tokens are used (P4).
Prerequisites: `make up && make migrate` must have run.

Run via:
  make test-vertical-slice
"""
from __future__ import annotations

import json
import os
import uuid
from unittest.mock import MagicMock

import psycopg
import pytest
from psycopg.rows import dict_row

from agent_system.actors.claims_processor_actor import (
    ACTOR_AGENT_ID as CLAIMS_PROCESSOR_AGENT_ID,
    run_claims_processor_stub,
)
from agent_system.actors.identity_verifier_actor import (
    ACTOR_AGENT_ID as IDENTITY_VERIFIER_AGENT_ID,
    run_identity_verifier_actor,
)
from agent_system.actors.intake_actor import (
    ACTOR_AGENT_ID as INTAKE_ACTOR_AGENT_ID,
    run_intake_actor,
)
from agent_system.actors.settlement_actor import (
    ACTOR_AGENT_ID as SETTLEMENT_AGENT_ID,
    run_settlement_actor_stub,
)
from agent_system.identity.keys import KeypairManager
from agent_system.orchestrator.state import Orchestrator
from agent_system.orchestrator.transitions import ClaimStage, TransitionGuardContext
from agent_system.parser.intake_parser import PARSER_AGENT_ID, run_intake_parser
from agent_system.tools.capability_tokens import issue_token
from audit.chain import append_log, verify_chain

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)

# Unique per test-module run so parallel runs don't collide.
_SESSION_ID = "e2e-vs-" + str(uuid.uuid4())
_CLAIM_ID = "claim-" + str(uuid.uuid4())


def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def setup_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
        conn.commit()


def teardown_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
        conn.commit()


# ---------------------------------------------------------------------------
# Mock helpers (mirror the pattern from tests/unit/test_intake_actor.py)
# ---------------------------------------------------------------------------


def _tool_block(name: str, input_: dict, block_id: str = "tu_001") -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = input_
    b.id = block_id
    return b


def _text_block(text: str) -> MagicMock:
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def _response(content: list, stop_reason: str = "tool_use") -> MagicMock:
    r = MagicMock()
    r.content = content
    r.stop_reason = stop_reason
    return r


def _mock_client(*responses) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


# ---------------------------------------------------------------------------
# Shared audit_fn factory
# ---------------------------------------------------------------------------


def _make_audit_fn(conn: psycopg.Connection):
    """Return a callable matching AuditFn that writes to *conn* and commits."""

    def audit_fn(
        *,
        agent_id: str,
        action: str,
        target: str,
        data_label: str,
        trace_id=None,
        details=None,
        security_event: bool = False,
    ) -> None:
        resolved_trace: uuid.UUID | None = None
        if isinstance(trace_id, str):
            resolved_trace = uuid.UUID(trace_id)
        elif isinstance(trace_id, uuid.UUID):
            resolved_trace = trace_id
        append_log(
            conn,
            agent_id=agent_id,
            action=action,
            target=target,
            data_label=data_label,
            trace_id=resolved_trace,
            details=details,
            security_event=security_event,
        )
        conn.commit()

    return audit_fn


# ---------------------------------------------------------------------------
# Happy-path vertical slice
# ---------------------------------------------------------------------------


class TestVerticalSliceHappyPath:
    def test_full_pipeline_reaches_closed_with_intact_chain(self):
        # ── Infrastructure ──────────────────────────────────────────────────
        orchestrator_km = KeypairManager.generate("orchestrator")
        pub = orchestrator_km.public_key_bytes

        conn = _admin()
        audit_fn = _make_audit_fn(conn)

        orchestrator = Orchestrator(_SESSION_ID, audit_fn=audit_fn)
        assert orchestrator.stage == ClaimStage.INTAKE

        # ── Step 1: Intake parser (P1 — quarantined, no tools) ──────────────
        _parser_json = json.dumps({
            "schema_version": "intake@1",
            "incident_type": "collision",
            "incident_date": "2025-03-15",
            "incident_location": "Main St, Springfield",
            "damage_description": "Front bumper cracked.",
            "police_report_filed": True,
            "other_parties_involved": False,
            "injuries_reported": False,
            "intake_complete": True,
            "missing_fields": [],
        })
        parser_client = _mock_client(
            _response([_text_block(_parser_json)], "end_turn")
        )
        intake_output = run_intake_parser(
            "I had a collision on March 15th at Main St, Springfield. "
            "Front bumper is cracked. Police report filed. No other parties.",
            client=parser_client,
            audit_fn=audit_fn,
            session_id=_SESSION_ID,
        )
        assert intake_output.intake_complete is True

        # ── Step 2: Intake actor (P4 — capability-token-gated tools) ────────
        intake_tokens = {
            name: issue_token(
                orchestrator_km, agent_id=INTAKE_ACTOR_AGENT_ID, tool=name, scope={}
            )
            for name in ("mark_intake_complete", "request_more_info", "search_public_faq")
        }
        intake_actor_client = _mock_client(
            _response(
                [_tool_block(
                    "mark_intake_complete",
                    {"structured_summary": "Collision at Main St. Full coverage. Intake complete."},
                )],
                "tool_use",
            )
        )
        intake_envelope = run_intake_actor(
            intake_output,
            pre_issued_tokens=intake_tokens,
            orchestrator_public_key=pub,
            client=intake_actor_client,
            audit_fn=audit_fn,
            session_id=_SESSION_ID,
        )
        assert intake_envelope.outcome == "ready_for_identity"

        # ── Transition 1: INTAKE → IDENTITY_PENDING ─────────────────────────
        orchestrator.request_transition(
            ClaimStage.IDENTITY_PENDING,
            TransitionGuardContext(
                intake_complete=(intake_envelope.outcome == "ready_for_identity")
            ),
        )
        assert orchestrator.stage == ClaimStage.IDENTITY_PENDING

        # ── Step 3: Identity verifier (P4 — single terminal tool) ───────────
        identity_tokens = {
            "request_identity_check": issue_token(
                orchestrator_km,
                agent_id=IDENTITY_VERIFIER_AGENT_ID,
                tool="request_identity_check",
                scope={},
            )
        }
        identity_client = _mock_client(
            _response(
                [_tool_block(
                    "request_identity_check",
                    {"policy_number": "POL-0001", "dob_hint": "1985-06-20", "ssn_last4": "7890"},
                )],
                "tool_use",
            )
        )

        def _vault_check(policy_number: str, dob_hint: str, ssn_last4: str) -> dict:
            return {"verified": True, "outcome": "SUCCESS", "attempts_remaining": 3}

        identity_envelope = run_identity_verifier_actor(
            policy_number="POL-0001",
            dob_hint="1985-06-20",
            ssn_last4="7890",
            pre_issued_tokens=identity_tokens,
            orchestrator_public_key=pub,
            identity_check_fn=_vault_check,
            client=identity_client,
            audit_fn=audit_fn,
            session_id=_SESSION_ID,
        )
        assert identity_envelope.outcome == "identity_verified"

        # ── Transition 2: IDENTITY_PENDING → IDENTITY_VERIFIED ──────────────
        orchestrator.request_transition(
            ClaimStage.IDENTITY_VERIFIED,
            TransitionGuardContext(
                identity_verified=(identity_envelope.outcome == "identity_verified")
            ),
        )
        assert orchestrator.stage == ClaimStage.IDENTITY_VERIFIED

        # ── Transition 3: IDENTITY_VERIFIED → PROCESSING ────────────────────
        orchestrator.request_transition(
            ClaimStage.PROCESSING,
            TransitionGuardContext(),
        )
        assert orchestrator.stage == ClaimStage.PROCESSING

        # ── Step 4: Claims processor stub (no LLM) ───────────────────────────
        processor_envelope = run_claims_processor_stub(
            claim_id=_CLAIM_ID,
            session_id=_SESSION_ID,
            audit_fn=audit_fn,
        )
        assert processor_envelope.fraud_signal == "CLEAR"

        # ── Transition 4: PROCESSING → DECIDED ──────────────────────────────
        orchestrator.request_transition(
            ClaimStage.DECIDED,
            TransitionGuardContext(
                damage_assessment=processor_envelope.damage_assessment,
                coverage_calculation=processor_envelope.coverage_calculation,
                fraud_decision=processor_envelope.fraud_signal,
            ),
        )
        assert orchestrator.stage == ClaimStage.DECIDED

        # ── Step 5: Settlement actor stub (no LLM) ───────────────────────────
        settlement_envelope = run_settlement_actor_stub(
            claim_id=_CLAIM_ID,
            session_id=_SESSION_ID,
            audit_fn=audit_fn,
        )
        assert settlement_envelope.settlement_amount <= 10_000.0

        # ── Transition 5: DECIDED → SETTLED ─────────────────────────────────
        orchestrator.request_transition(
            ClaimStage.SETTLED,
            TransitionGuardContext(
                fraud_decision=processor_envelope.fraud_signal,
                settlement_amount=settlement_envelope.settlement_amount,
            ),
        )
        assert orchestrator.stage == ClaimStage.SETTLED

        # ── Transition 6: SETTLED → CLOSED ───────────────────────────────────
        orchestrator.request_transition(
            ClaimStage.CLOSED,
            TransitionGuardContext(),
        )
        assert orchestrator.stage == ClaimStage.CLOSED

        conn.close()

        # ── Assertion 1: audit chain integrity ───────────────────────────────
        with _admin() as verify_conn:
            broken = verify_chain(verify_conn)
        assert broken == [], f"Audit chain broken at log_ids: {broken}"

        # ── Assertion 2: per-agent audit coverage ─────────────────────────────
        with _admin() as read_conn:
            with read_conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT agent_id, COUNT(*) AS cnt FROM audit_log GROUP BY agent_id"
                )
                rows_by_agent: dict[str, int] = {
                    r["agent_id"]: r["cnt"] for r in cur.fetchall()
                }

        expected_agents = {
            PARSER_AGENT_ID,
            INTAKE_ACTOR_AGENT_ID,
            IDENTITY_VERIFIER_AGENT_ID,
            CLAIMS_PROCESSOR_AGENT_ID,
            SETTLEMENT_AGENT_ID,
            Orchestrator.AGENT_ID,
        }
        for agent_id in expected_agents:
            assert agent_id in rows_by_agent, (
                f"No audit rows found for agent_id={agent_id!r}. "
                f"Present agents: {set(rows_by_agent)}"
            )

        # ── Assertion 3: no security events on happy path ────────────────────
        with _admin() as sec_conn:
            with sec_conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT log_id, agent_id, action "
                    "FROM audit_log WHERE security_event = TRUE"
                )
                security_rows = cur.fetchall()
        assert security_rows == [], (
            f"Unexpected security_event=TRUE rows on happy path: "
            + ", ".join(
                f"log_id={r['log_id']} agent={r['agent_id']} action={r['action']}"
                for r in security_rows
            )
        )
