"""Integration tests for audit log hash-chain (task 1.1.4).

Verifies:
  - append_log() inserts rows whose row_hash is verifiable by verify_chain()
  - First row uses GENESIS_HASH as prev_hash
  - Each successive row's prev_hash equals the prior row's row_hash
  - verify_chain() returns [] on an intact chain
  - verify_chain() returns the tampered log_id after a direct UPDATE
  - Agent roles can still INSERT into audit_log via inherited role_audit_writer

Prerequisites: `make up && make migrate` must have run successfully.
"""
from __future__ import annotations

import json
import os
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from audit.chain import GENESIS_HASH, append_log, verify_chain, compute_row_hash, canonical_fields

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


class TestAppendAndVerify:
    def test_single_row_chain_intact(self):
        with _admin() as conn:
            log_id = append_log(
                conn,
                agent_id="orchestrator",
                action="test_action",
                target="claims/test",
                data_label="CONFIDENTIAL",
            )
            conn.commit()

        with _admin() as conn:
            broken = verify_chain(conn)

        assert log_id > 0
        assert broken == []

    def test_first_row_uses_genesis_hash(self):
        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT prev_hash FROM audit_log ORDER BY log_id LIMIT 1"
                )
                row = cur.fetchone()

        assert row is not None
        assert row["prev_hash"] == GENESIS_HASH

    def test_five_row_chain_intact(self):
        with _admin() as conn:
            for i in range(5):
                append_log(
                    conn,
                    agent_id=f"agent_{i}",
                    action=f"action_{i}",
                    target=f"target/{i}",
                    data_label="CONFIDENTIAL",
                    details={"step": i},
                )
            conn.commit()

        with _admin() as conn:
            broken = verify_chain(conn)

        assert broken == []

    def test_prev_hash_links_are_correct(self):
        with _admin() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT log_id, prev_hash, row_hash FROM audit_log ORDER BY log_id")
                rows = cur.fetchall()

        assert len(rows) >= 2
        for i in range(1, len(rows)):
            assert rows[i]["prev_hash"] == rows[i - 1]["row_hash"], (
                f"Row {rows[i]['log_id']}: prev_hash should equal prior row_hash"
            )

    def test_with_trace_id_and_security_event(self):
        trace = uuid.uuid4()
        with _admin() as conn:
            append_log(
                conn,
                agent_id="orchestrator",
                action="suspicious_activity",
                target="security",
                data_label="CONFIDENTIAL",
                trace_id=trace,
                details={"reason": "test"},
                security_event=True,
            )
            conn.commit()

        with _admin() as conn:
            broken = verify_chain(conn)

        assert broken == []


class TestTamperDetection:
    def test_tampered_row_detected(self):
        with _admin() as conn:
            log_id = append_log(
                conn,
                agent_id="orchestrator",
                action="tamper_target",
                target="claims/tamper",
                data_label="CONFIDENTIAL",
            )
            conn.commit()

        # Directly tamper with the action field — simulates DB-level manipulation.
        with _admin() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE audit_log SET action = 'TAMPERED' WHERE log_id = %s",
                    (log_id,),
                )
            conn.commit()

        with _admin() as conn:
            broken = verify_chain(conn)

        assert log_id in broken

    def test_tampered_prev_hash_detected(self):
        with _admin() as conn:
            log_id = append_log(
                conn,
                agent_id="orchestrator",
                action="prev_hash_target",
                target="claims/prev",
                data_label="CONFIDENTIAL",
            )
            conn.commit()

        with _admin() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE audit_log SET prev_hash = %s WHERE log_id = %s",
                    ("f" * 64, log_id),
                )
            conn.commit()

        with _admin() as conn:
            broken = verify_chain(conn)

        assert log_id in broken

    def test_intact_rows_not_in_broken_list(self):
        with _admin() as conn:
            good_id = append_log(
                conn,
                agent_id="orchestrator",
                action="good_action",
                target="claims/good",
                data_label="CONFIDENTIAL",
            )
            bad_id = append_log(
                conn,
                agent_id="orchestrator",
                action="bad_action",
                target="claims/bad",
                data_label="CONFIDENTIAL",
            )
            conn.commit()

        with _admin() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE audit_log SET agent_id = 'ATTACKER' WHERE log_id = %s",
                    (bad_id,),
                )
            conn.commit()

        with _admin() as conn:
            broken = verify_chain(conn)

        assert bad_id in broken
        # good_id inserted before bad_id; its own hash is still intact
        # (bad_id tamper only affects bad_id's row_hash and cascades forward,
        #  but good_id's position precedes it).
        # Verify good_id's row is not reported broken.
        assert good_id not in broken


class TestAgentRoleInheritedInsert:
    def test_orchestrator_can_insert_audit_log_raw(self):
        """role_orchestrator inherits role_audit_writer → INSERT on audit_log."""
        with psycopg.connect(ORCHESTRATOR_DSN, autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log (
                        prev_hash, row_hash, agent_id, action, target, data_label
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "0" * 64,
                        "1" * 64,
                        "orchestrator",
                        "raw_insert_test",
                        "test",
                        "CONFIDENTIAL",
                    ),
                )
            conn.rollback()  # Don't pollute the chain with a synthetic row.
