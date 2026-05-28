"""Integration tests for capability token persistence (task 1.2.2).

Verifies that persist_issuance() and record_use() read and write the correct
rows in capability_token_log, and that the DB CHECK constraint on use_result
rejects unexpected values.

Prerequisites: `make up && make migrate` must have run successfully.
"""
from __future__ import annotations

import json
import os
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import (
    DenyReason,
    VerifyResult,
    issue_token,
    persist_issuance,
    record_use,
)

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)
ORCHESTRATOR_DSN = os.environ.get(
    "TEST_ORCHESTRATOR_DSN",
    "postgresql://role_orchestrator:role_orchestrator@localhost:5432/secureclaim",
)


def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def _orchestrator() -> psycopg.Connection:
    return psycopg.connect(ORCHESTRATOR_DSN, autocommit=False)


def setup_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_token_log")
        conn.commit()


def teardown_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_token_log")
        conn.commit()


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="approve_claim",
        scope={"claim_id": "CLM-INT-001", "max_amount": 5000},
    )


# ---------------------------------------------------------------------------
# persist_issuance — DB writes
# ---------------------------------------------------------------------------


class TestPersistIssuance:
    def test_row_is_written(self, token):
        with _admin() as conn:
            persist_issuance(conn, token)
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM capability_token_log WHERE token_id = %s",
                    (token.token_id,),
                )
                row = cur.fetchone()

        assert row is not None

    def test_persisted_fields_match_token(self, token):
        with _admin() as conn:
            persist_issuance(conn, token)
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT * FROM capability_token_log WHERE token_id = %s",
                    (token.token_id,),
                )
                row = cur.fetchone()

        assert str(row["token_id"]) == str(token.token_id)
        assert row["issued_by"] == "orchestrator"
        assert row["agent_id"] == token.agent_id
        assert row["tool"] == token.tool
        assert row["scope"] == token.scope
        # Timestamps stored as UTC, compare as timezone-aware
        assert row["issued_at"].utctimetuple() == token.issued_at.utctimetuple()
        assert row["expires_at"].utctimetuple() == token.expires_at.utctimetuple()

    def test_used_at_and_use_result_are_null_after_issuance(self, token):
        with _admin() as conn:
            persist_issuance(conn, token)
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT used_at, use_result FROM capability_token_log WHERE token_id = %s",
                    (token.token_id,),
                )
                row = cur.fetchone()

        assert row["used_at"] is None
        assert row["use_result"] is None

    def test_scope_stored_as_jsonb(self, orchestrator_km):
        scope = {"policy_id": "POL-99", "nested": {"x": 1}}
        t = issue_token(orchestrator_km, agent_id="intake_actor", tool="read_policy", scope=scope)
        with _admin() as conn:
            persist_issuance(conn, t)
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT scope FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                row = cur.fetchone()

        assert row["scope"] == scope

    def test_orchestrator_role_can_persist(self, orchestrator_km):
        """role_orchestrator has INSERT on capability_token_log."""
        t = issue_token(
            orchestrator_km, agent_id="settlement_actor", tool="pay_claim", scope={}
        )
        with _orchestrator() as conn:
            persist_issuance(conn, t)
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT token_id FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                assert cur.fetchone() is not None


# ---------------------------------------------------------------------------
# record_use — DB updates
# ---------------------------------------------------------------------------


class TestRecordUse:
    def _issue_and_persist(self, orchestrator_km, agent_id="claims_processor", tool="approve_claim"):
        t = issue_token(orchestrator_km, agent_id=agent_id, tool=tool, scope={})
        with _admin() as conn:
            persist_issuance(conn, t)
            conn.commit()
        return t

    def test_record_ok_sets_used_at_and_result(self, orchestrator_km):
        t = self._issue_and_persist(orchestrator_km)
        with _admin() as conn:
            record_use(conn, t.token_id, VerifyResult.success())
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT used_at, use_result FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                row = cur.fetchone()

        assert row["used_at"] is not None
        assert row["use_result"] == "OK"

    def test_record_denied_signature(self, orchestrator_km):
        t = self._issue_and_persist(orchestrator_km)
        with _admin() as conn:
            record_use(conn, t.token_id, VerifyResult.denied(DenyReason.SIGNATURE))
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT use_result FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                row = cur.fetchone()

        assert row["use_result"] == "DENIED_SIGNATURE"

    def test_record_denied_expired(self, orchestrator_km):
        t = self._issue_and_persist(orchestrator_km)
        with _admin() as conn:
            record_use(conn, t.token_id, VerifyResult.denied(DenyReason.EXPIRED))
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT use_result FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                row = cur.fetchone()

        assert row["use_result"] == "DENIED_EXPIRED"

    def test_record_denied_scope(self, orchestrator_km):
        t = self._issue_and_persist(orchestrator_km)
        with _admin() as conn:
            record_use(conn, t.token_id, VerifyResult.denied(DenyReason.SCOPE))
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT use_result FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                row = cur.fetchone()

        assert row["use_result"] == "DENIED_SCOPE"

    def test_missing_token_id_raises(self, orchestrator_km):
        phantom_id = uuid.uuid4()
        with _admin() as conn:
            with pytest.raises(ValueError, match="capability_token_log has no row"):
                record_use(conn, phantom_id, VerifyResult.success())

    def test_use_result_check_constraint_rejects_bad_value(self, orchestrator_km):
        """DB CHECK constraint rejects any value not in the allowed set."""
        t = self._issue_and_persist(orchestrator_km)
        with _admin() as conn:
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE capability_token_log SET use_result = 'INVALID' WHERE token_id = %s",
                        (t.token_id,),
                    )
            conn.rollback()

    def test_orchestrator_role_can_record_use(self, orchestrator_km):
        """role_orchestrator has UPDATE on capability_token_log."""
        t = self._issue_and_persist(orchestrator_km)
        with _orchestrator() as conn:
            record_use(conn, t.token_id, VerifyResult.success())
            conn.commit()

        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT use_result FROM capability_token_log WHERE token_id = %s",
                    (t.token_id,),
                )
                row = cur.fetchone()

        assert row["use_result"] == "OK"
