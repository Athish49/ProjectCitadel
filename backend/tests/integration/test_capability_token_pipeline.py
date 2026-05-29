"""Integration tests for capability-token pipeline enforcement (task 2.2.3).

Verifies:
  - Happy path: intake actor with DB-backed ToolRegistry succeeds; tool_call_ok
    written to audit_log; capability_token_log.use_result = "OK".
  - Bad scope: token issued with narrow scope; LLM calls with mismatched params;
    tool_call_denied written to audit_log; capability_token_log.use_result = "DENIED_SCOPE".

Prerequisites: `make up && make migrate` must have run.
Run via: make test-capability-token-pipeline
"""
from __future__ import annotations

import os
import uuid
from datetime import date
from unittest.mock import MagicMock

import psycopg
import pytest
from psycopg.rows import dict_row

from agent_system.actors.intake_actor import (
    ACTOR_AGENT_ID as INTAKE_ACTOR_AGENT_ID,
    run_intake_actor,
)
from agent_system.identity.keys import KeypairManager
from agent_system.parser.schemas import IncidentType, IntakeOutput
from agent_system.tools.capability_tokens import issue_token, persist_issuance

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)

_SESSION_PREFIX = "cap-token-pipeline-"


def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def _simple_intake_output() -> IntakeOutput:
    return IntakeOutput(
        schema_version="intake@1",
        incident_type=IncidentType.collision,
        incident_date=date(2025, 3, 15),
        incident_location="Main St, Springfield",
        damage_description="Front bumper cracked.",
        police_report_filed=True,
        other_parties_involved=False,
        injuries_reported=False,
        intake_complete=True,
        missing_fields=[],
    )


def _tool_block(name: str, input_: dict, block_id: str = "tu_001") -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = input_
    b.id = block_id
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


def setup_module(_) -> None:
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
            cur.execute("DELETE FROM capability_token_log")
        conn.commit()


def teardown_module(_) -> None:
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
            cur.execute("DELETE FROM capability_token_log")
        conn.commit()


class TestCapabilityTokenPipelineHappyPath:
    def test_tool_call_ok_written_to_audit_log(self) -> None:
        session_id = _SESSION_PREFIX + str(uuid.uuid4())
        orchestrator_km = KeypairManager.generate("orchestrator")
        pub = orchestrator_km.public_key_bytes

        tokens = {
            name: issue_token(
                orchestrator_km,
                agent_id=INTAKE_ACTOR_AGENT_ID,
                tool=name,
                scope={},
            )
            for name in ("mark_intake_complete", "request_more_info", "search_public_faq")
        }
        with _admin() as conn:
            for token in tokens.values():
                persist_issuance(conn, token)
            conn.commit()

        summary_text = "Collision at Main St. Full coverage. Intake complete."
        mock_client = _mock_client(
            _response(
                [_tool_block("mark_intake_complete", {"structured_summary": summary_text})],
                "tool_use",
            )
        )

        with _admin() as conn:
            envelope = run_intake_actor(
                _simple_intake_output(),
                pre_issued_tokens=tokens,
                orchestrator_public_key=pub,
                client=mock_client,
                session_id=session_id,
                conn=conn,
            )

        assert envelope.outcome == "ready_for_identity"

        token_id_str = str(tokens["mark_intake_complete"].token_id)

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT agent_id, action, details "
                    "FROM audit_log "
                    "WHERE action = 'tool_call_ok' "
                    "  AND details->>'token_id' = %s",
                    (token_id_str,),
                )
                rows = cur.fetchall()

        assert len(rows) == 1, f"Expected 1 tool_call_ok row, got {len(rows)}"
        assert rows[0]["agent_id"] == INTAKE_ACTOR_AGENT_ID

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT use_result FROM capability_token_log WHERE token_id = %s",
                    (tokens["mark_intake_complete"].token_id,),
                )
                row = cur.fetchone()

        assert row is not None
        assert row["use_result"] == "OK"


class TestCapabilityTokenPipelineBadScope:
    def test_bad_scope_denied_and_audited(self) -> None:
        session_id = _SESSION_PREFIX + str(uuid.uuid4())
        orchestrator_km = KeypairManager.generate("orchestrator")
        pub = orchestrator_km.public_key_bytes

        # Issue a narrow-scoped token: only the exact expected summary is permitted.
        expected_summary = "only this exact summary is permitted by the token scope"
        bad_scope_token = issue_token(
            orchestrator_km,
            agent_id=INTAKE_ACTOR_AGENT_ID,
            tool="mark_intake_complete",
            scope={"structured_summary": expected_summary},
        )
        with _admin() as conn:
            persist_issuance(conn, bad_scope_token)
            conn.commit()

        # LLM calls with a different summary — scope constraint violated.
        mock_client = _mock_client(
            _response(
                [_tool_block(
                    "mark_intake_complete",
                    {"structured_summary": "a totally different summary"},
                )],
                "tool_use",
            ),
            # After receiving the error, LLM stops.
            _response([], "end_turn"),
        )

        with _admin() as conn:
            envelope = run_intake_actor(
                _simple_intake_output(),
                pre_issued_tokens={"mark_intake_complete": bad_scope_token},
                orchestrator_public_key=pub,
                client=mock_client,
                session_id=session_id,
                conn=conn,
            )

        # No terminal tool succeeded — actor falls back to reject.
        assert envelope.outcome == "reject_as_out_of_scope"

        token_id_str = str(bad_scope_token.token_id)

        # audit_log must have a tool_call_denied row with DENIED_SCOPE.
        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT agent_id, action, details "
                    "FROM audit_log "
                    "WHERE action = 'tool_call_denied' "
                    "  AND details->>'token_id' = %s",
                    (token_id_str,),
                )
                rows = cur.fetchall()

        assert len(rows) == 1, f"Expected 1 tool_call_denied row, got {len(rows)}"
        assert rows[0]["agent_id"] == INTAKE_ACTOR_AGENT_ID
        assert rows[0]["details"]["deny_reason"] == "DENIED_SCOPE"

        # capability_token_log must record the denial.
        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT use_result FROM capability_token_log WHERE token_id = %s",
                    (bad_scope_token.token_id,),
                )
                row = cur.fetchone()

        assert row is not None
        assert row["use_result"] == "DENIED_SCOPE"
