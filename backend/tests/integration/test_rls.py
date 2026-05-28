"""
Integration tests for PostgreSQL Row-Level Security (P7).

Verifies that all customer-scoped tables:
  - Return only the authenticated customer's rows (read isolation)
  - Reject attempts to read rows belonging to another customer (fail-closed)
  - Reject INSERT/UPDATE that would write into another customer's scope (write isolation)
  - Return zero rows when app.current_customer_id is unset (fail-closed default)

Also covers indirect-RLS tables (evidence, settlements) whose policies use a
subquery join through claims rather than a direct customer_id column.

Prerequisites: `make up && make migrate` must have run successfully.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import psycopg.errors
import pytest

# ── connection strings ──────────────────────────────────────────────────────
ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)
APP_DSN = os.environ.get(
    "TEST_APP_DSN",
    "postgresql://secureclaim_app:secureclaim_app@localhost:5432/secureclaim",
)

pytestmark = pytest.mark.integration


# ── helpers ─────────────────────────────────────────────────────────────────

def admin_conn() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def app_conn() -> psycopg.Connection:
    return psycopg.connect(APP_DSN, autocommit=False)


def set_customer(cur: psycopg.Cursor, customer_id: uuid.UUID) -> None:
    # SET LOCAL does not accept bind parameters; use set_config() with is_local=true,
    # which is equivalent to SET LOCAL but accepts a parameterised value safely.
    cur.execute(
        "SELECT set_config('app.current_customer_id', %s, true)",
        (str(customer_id),),
    )


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def two_customers():
    """
    Insert two independent customers (A and B) via the superuser connection.
    Yields (id_a, id_b). Cleans up after the test.
    """
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    pol_a = f"TST-{id_a.hex[:8].upper()}"
    pol_b = f"TST-{id_b.hex[:8].upper()}"

    conn = admin_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO customers "
                "(customer_id, policy_number, first_name, last_name, email, date_of_birth) "
                "VALUES (%s, %s, 'Alice', 'A', 'alice_rls@test.invalid', '1990-01-01')",
                (id_a, pol_a),
            )
            cur.execute(
                "INSERT INTO customers "
                "(customer_id, policy_number, first_name, last_name, email, date_of_birth) "
                "VALUES (%s, %s, 'Bob', 'B', 'bob_rls@test.invalid', '1985-06-15')",
                (id_b, pol_b),
            )
        conn.commit()

        yield id_a, id_b

    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customers WHERE customer_id IN (%s, %s)", (id_a, id_b))
        conn.commit()
        conn.close()


@pytest.fixture()
def customer_with_claim(two_customers):
    """
    Extends two_customers with one claim per customer, for indirect-RLS table tests.
    Yields (id_a, id_b, claim_a_id, claim_b_id).
    """
    id_a, id_b = two_customers

    conn = admin_conn()
    try:
        # Need policies before claims
        pol_a_id = uuid.uuid4()
        pol_b_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO policies "
                "(policy_id, policy_number, customer_id, policy_status) "
                "VALUES (%s, %s, %s, 'ACTIVE')",
                (pol_a_id, f"POL-A-{id_a.hex[:6].upper()}", id_a),
            )
            cur.execute(
                "INSERT INTO policies "
                "(policy_id, policy_number, customer_id, policy_status) "
                "VALUES (%s, %s, %s, 'ACTIVE')",
                (pol_b_id, f"POL-B-{id_b.hex[:6].upper()}", id_b),
            )
        conn.commit()

        claim_a_id = uuid.uuid4()
        claim_b_id = uuid.uuid4()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO claims "
                "(claim_id, claim_number, customer_id, policy_id, claim_stage) "
                "VALUES (%s, %s, %s, %s, 'INTAKE')",
                (claim_a_id, f"CLM-A-{id_a.hex[:6].upper()}", id_a, pol_a_id),
            )
            cur.execute(
                "INSERT INTO claims "
                "(claim_id, claim_number, customer_id, policy_id, claim_stage) "
                "VALUES (%s, %s, %s, %s, 'INTAKE')",
                (claim_b_id, f"CLM-B-{id_b.hex[:6].upper()}", id_b, pol_b_id),
            )
        conn.commit()

        yield id_a, id_b, claim_a_id, claim_b_id

    finally:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM claims WHERE claim_id IN (%s, %s)",
                (claim_a_id, claim_b_id),
            )
            cur.execute(
                "DELETE FROM policies WHERE policy_id IN (%s, %s)",
                (pol_a_id, pol_b_id),
            )
        conn.commit()
        conn.close()


# ── customers table ──────────────────────────────────────────────────────────

class TestCustomersRLS:
    def test_customer_a_sees_only_own_row(self, two_customers):
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows == [id_a], f"Expected only A's row; got {rows}"

    def test_customer_b_sees_only_own_row(self, two_customers):
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_b)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows == [id_b], f"Expected only B's row; got {rows}"

    def test_no_customer_setting_returns_empty(self, two_customers):
        """Fail-closed: when app.current_customer_id is unset, zero rows returned."""
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                # Deliberately do NOT call set_customer()
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], "fail-closed: missing customer_id setting must return zero rows"

    def test_cross_customer_insert_blocked(self, two_customers):
        """WITH CHECK: cannot INSERT a row with another customer's UUID."""
        id_a, id_b = two_customers
        foreign_id = uuid.uuid4()  # not id_a; should be blocked by WITH CHECK
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute(
                        "INSERT INTO customers "
                        "(customer_id, policy_number, first_name, last_name, email, date_of_birth) "
                        "VALUES (%s, 'POL-EVIL', 'Evil', 'Insert', 'evil@test.invalid', '1990-01-01')",
                        (foreign_id,),
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_cross_customer_update_affects_zero_rows(self, two_customers):
        """USING: UPDATE targeting another customer's row silently touches 0 rows."""
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "UPDATE customers SET email = 'pwned@evil.invalid' WHERE customer_id = %s",
                    (id_b,),
                )
                affected = cur.rowcount
        finally:
            conn.rollback()
            conn.close()

        assert affected == 0, "USING policy must prevent cross-customer UPDATE"


# ── policies table ───────────────────────────────────────────────────────────

class TestPoliciesRLS:
    def test_isolation(self, customer_with_claim):
        id_a, id_b, *_ = customer_with_claim
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT customer_id FROM policies WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert all(r == id_a for r in rows), f"Policies RLS leak: got {rows}"
        assert len(rows) == 1


# ── claims table ─────────────────────────────────────────────────────────────

class TestClaimsRLS:
    def test_isolation(self, customer_with_claim):
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT claim_id FROM claims WHERE claim_id IN (%s, %s)",
                    (claim_a_id, claim_b_id),
                )
                rows = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows == [claim_a_id], f"Claims RLS leak: got {rows}"


# ── evidence table (indirect RLS via claims subquery) ────────────────────────

class TestEvidenceRLS:
    @pytest.fixture()
    def two_evidence_rows(self, customer_with_claim):
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        ev_a = uuid.uuid4()
        ev_b = uuid.uuid4()
        conn = admin_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO evidence "
                    "(evidence_id, claim_id, evidence_type) VALUES (%s, %s, 'PHOTO')",
                    (ev_a, claim_a_id),
                )
                cur.execute(
                    "INSERT INTO evidence "
                    "(evidence_id, claim_id, evidence_type) VALUES (%s, %s, 'PHOTO')",
                    (ev_b, claim_b_id),
                )
            conn.commit()
            yield id_a, id_b, ev_a, ev_b
        finally:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM evidence WHERE evidence_id IN (%s, %s)", (ev_a, ev_b)
                )
            conn.commit()
            conn.close()

    def test_evidence_isolation(self, two_evidence_rows):
        id_a, id_b, ev_a, ev_b = two_evidence_rows
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT evidence_id FROM evidence WHERE evidence_id IN (%s, %s)",
                    (ev_a, ev_b),
                )
                rows = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows == [ev_a], f"Evidence indirect-RLS leak: got {rows}"

    def test_evidence_no_setting_returns_empty(self, two_evidence_rows):
        _, _, ev_a, ev_b = two_evidence_rows
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT evidence_id FROM evidence WHERE evidence_id IN (%s, %s)",
                    (ev_a, ev_b),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], "fail-closed: no customer_id set → no evidence rows"


# ── settlements table (indirect RLS via claims subquery) ─────────────────────

class TestSettlementsRLS:
    @pytest.fixture()
    def two_settlements(self, customer_with_claim):
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        set_a = uuid.uuid4()
        set_b = uuid.uuid4()
        conn = admin_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO settlements (settlement_id, claim_id) VALUES (%s, %s)",
                    (set_a, claim_a_id),
                )
                cur.execute(
                    "INSERT INTO settlements (settlement_id, claim_id) VALUES (%s, %s)",
                    (set_b, claim_b_id),
                )
            conn.commit()
            yield id_a, id_b, set_a, set_b
        finally:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM settlements WHERE settlement_id IN (%s, %s)",
                    (set_a, set_b),
                )
            conn.commit()
            conn.close()

    def test_settlements_isolation(self, two_settlements):
        id_a, _, set_a, set_b = two_settlements
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT settlement_id FROM settlements WHERE settlement_id IN (%s, %s)",
                    (set_a, set_b),
                )
                rows = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows == [set_a], f"Settlements indirect-RLS leak: got {rows}"

    def test_settlements_no_setting_returns_empty(self, two_settlements):
        _, _, set_a, set_b = two_settlements
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT settlement_id FROM settlements WHERE settlement_id IN (%s, %s)",
                    (set_a, set_b),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], "fail-closed: no customer_id set → no settlement rows"


# ── grant boundary tests (omission-based controls from migration 002) ────────

class TestGrantBoundaries:
    """
    Verify that migration 002's omission-based controls are enforced.
    These tests check what secureclaim_app *cannot* do, not just what it can.
    """

    def test_app_role_cannot_select_pii_vault(self):
        """Doc 03 §2.2: No agent has DB access to pii_vault."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT 1 FROM pii_vault LIMIT 1")
        finally:
            conn.rollback()
            conn.close()

    def test_app_role_cannot_select_fraud_scores(self):
        """Doc 03 §2.7: fraud_scores accessible via function-call only."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT 1 FROM fraud_scores LIMIT 1")
        finally:
            conn.rollback()
            conn.close()

    def test_app_role_cannot_update_audit_log(self):
        """Doc 03 §2.9: No UPDATE granted to any application role on audit_log."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("UPDATE audit_log SET action = 'x' WHERE log_id = 1")
        finally:
            conn.rollback()
            conn.close()

    def test_app_role_cannot_delete_audit_log(self):
        """Doc 03 §2.9: No DELETE granted to any application role on audit_log."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("DELETE FROM audit_log WHERE log_id = 1")
        finally:
            conn.rollback()
            conn.close()

    def test_app_role_can_insert_audit_log(self):
        """Positive: INSERT must succeed (audit_log is INSERT-only for the app role)."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log (agent_id, action, target, data_label) "
                    "VALUES ('test_suite', 'rls_boundary_check', 'audit_log', 'CONFIDENTIAL')"
                )
        finally:
            conn.rollback()
            conn.close()


# ── complaints table ─────────────────────────────────────────────────────────

class TestComplaintsRLS:
    def test_isolation(self, two_customers):
        id_a, id_b = two_customers
        comp_a = uuid.uuid4()
        comp_b = uuid.uuid4()
        sess = uuid.uuid4()

        conn_admin = admin_conn()
        try:
            with conn_admin.cursor() as cur:
                cur.execute(
                    "INSERT INTO complaints (complaint_id, session_id, customer_id, category) "
                    "VALUES (%s, %s, %s, 'service')",
                    (comp_a, sess, id_a),
                )
                cur.execute(
                    "INSERT INTO complaints (complaint_id, session_id, customer_id, category) "
                    "VALUES (%s, %s, %s, 'coverage')",
                    (comp_b, sess, id_b),
                )
            conn_admin.commit()

            conn = app_conn()
            try:
                with conn.cursor() as cur:
                    set_customer(cur, id_a)
                    cur.execute(
                        "SELECT complaint_id FROM complaints "
                        "WHERE complaint_id IN (%s, %s)",
                        (comp_a, comp_b),
                    )
                    rows = [r[0] for r in cur.fetchall()]
            finally:
                conn.rollback()
                conn.close()

        finally:
            with conn_admin.cursor() as cur:
                cur.execute(
                    "DELETE FROM complaints WHERE complaint_id IN (%s, %s)",
                    (comp_a, comp_b),
                )
            conn_admin.commit()
            conn_admin.close()

        assert rows == [comp_a], f"Complaints RLS leak: got {rows}"
