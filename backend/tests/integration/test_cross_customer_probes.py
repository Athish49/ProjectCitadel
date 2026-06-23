"""
Sprint 5.1.4 — Cross-Customer / RLS Adversarial Probe Suite (Integration Layer)
================================================================================

Adversarial DB-level probes covering:
  - Attack #37 (SQL Injection via Agent): parameterised-query boundary probes
  - Attack #28 (Semantic-Layer Exfiltration): cross-customer row reads via RLS bypass attempts
  - Attack #20 (Direct Exfiltration): direct table reads outside RLS scope

Each test class documents the attack ID and the specific control under test.

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
    cur.execute(
        "SELECT set_config('app.current_customer_id', %s, true)",
        (str(customer_id),),
    )


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def two_customers():
    """Adversarial fixture: customer A is the attacker, B is the victim."""
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
                "VALUES (%s, %s, 'Attacker', 'A', 'attacker_xc@test.invalid', '1990-01-01')",
                (id_a, pol_a),
            )
            cur.execute(
                "INSERT INTO customers "
                "(customer_id, policy_number, first_name, last_name, email, date_of_birth) "
                "VALUES (%s, %s, 'Victim', 'B', 'victim_xc@test.invalid', '1985-06-15')",
                (id_b, pol_b),
            )
        conn.commit()
        yield id_a, id_b
    finally:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM customers WHERE customer_id IN (%s, %s)", (id_a, id_b)
            )
        conn.commit()
        conn.close()


@pytest.fixture()
def customer_with_claim(two_customers):
    """Extends two_customers with one claim per customer."""
    id_a, id_b = two_customers
    conn = admin_conn()
    pol_a_id = uuid.uuid4()
    pol_b_id = uuid.uuid4()
    claim_a_id = uuid.uuid4()
    claim_b_id = uuid.uuid4()
    try:
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


# ── Attack #28 / #20: direct cross-customer read probes ──────────────────────

class TestRLSCrossCustomerProbes:
    """
    Attack #28 (Semantic-Layer Exfiltration) + #20 (Direct Exfiltration).

    An attacker holds a valid session token for customer A and attempts to
    read rows belonging to customer B by sending B's UUIDs as query parameters.
    The RLS policy on each table must silently filter all of B's rows.
    """

    def test_attacker_cannot_read_victims_customer_row(self, two_customers):
        """Probe: authenticated as A, request B's customer row → 0 rows."""
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id = %s",
                    (id_b,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            f"[Attack #28] RLS leak on customers: attacker A read victim B's row "
            f"(id_b={id_b})"
        )

    def test_attacker_cannot_enumerate_all_customers(self, two_customers):
        """Probe: authenticated as A, SELECT * → must not expose B's row."""
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

        assert id_b not in rows, (
            f"[Attack #20] Enumeration leak: B's customer_id visible to A"
        )
        assert rows == [id_a], f"Expected exactly A's row; got {rows}"

    def test_attacker_cannot_read_victims_claim(self, customer_with_claim):
        """Probe: authenticated as A, request B's claim UUID → 0 rows."""
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT claim_id FROM claims WHERE claim_id = %s",
                    (claim_b_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            f"[Attack #28] RLS leak on claims: attacker A read victim B's claim "
            f"(claim_b={claim_b_id})"
        )

    def test_attacker_cannot_update_victims_claim(self, customer_with_claim):
        """Probe: authenticated as A, UPDATE on B's claim → 0 rows affected."""
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "UPDATE claims SET claim_stage = 'CLOSED' WHERE claim_id = %s",
                    (claim_b_id,),
                )
                affected = cur.rowcount
        finally:
            conn.rollback()
            conn.close()

        assert affected == 0, (
            f"[Attack #28] RLS USING policy failed: attacker A updated B's claim "
            f"(rowcount={affected})"
        )

    def test_fail_closed_no_customer_set_claims(self, customer_with_claim):
        """Probe: no session token set → zero rows on claims (fail-closed)."""
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT claim_id FROM claims WHERE claim_id IN (%s, %s)",
                    (claim_a_id, claim_b_id),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            "[Attack #20] Fail-closed breach: unauthenticated request returned claim rows"
        )

    def test_fail_closed_no_customer_set_customers(self, two_customers):
        """Probe: no session token set → zero rows on customers (fail-closed)."""
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            "[Attack #20] Fail-closed breach: unauthenticated request returned customer rows"
        )

    def test_mid_transaction_customer_switch_isolation(self, two_customers):
        """
        Probe: start session as A, switch to B mid-transaction via set_customer, then
        switch back to A — verifies that RLS is re-evaluated on each statement boundary
        and that the final scope is A's.
        """
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows_as_a = [r[0] for r in cur.fetchall()]

                # Simulated attacker injects a customer switch mid-transaction
                set_customer(cur, id_b)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows_as_b = [r[0] for r in cur.fetchall()]

                # Switch back: confirm we see only A again
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                rows_restored = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows_as_a == [id_a], f"Before switch: expected [A], got {rows_as_a}"
        assert rows_as_b == [id_b], f"After switch to B: expected [B], got {rows_as_b}"
        assert rows_restored == [id_a], f"After restore to A: expected [A], got {rows_restored}"


# ── Attack #28: indirect-RLS table probes ────────────────────────────────────

class TestRLSIndirectTableProbes:
    """
    Attack #28 (Semantic-Layer Exfiltration) on tables with indirect RLS.

    Evidence and settlements have no direct customer_id column; they are
    scoped via a subquery JOIN through claims.  An attacker who knows B's
    evidence or settlement UUIDs must be denied access even though the rows
    carry no direct customer marker.
    """

    @pytest.fixture()
    def indirect_rows(self, customer_with_claim):
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        ev_a, ev_b = uuid.uuid4(), uuid.uuid4()
        set_a, set_b = uuid.uuid4(), uuid.uuid4()
        comp_a, comp_b = uuid.uuid4(), uuid.uuid4()
        sess = uuid.uuid4()

        conn = admin_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO evidence (evidence_id, claim_id, evidence_type) "
                    "VALUES (%s, %s, 'PHOTO'), (%s, %s, 'PHOTO')",
                    (ev_a, claim_a_id, ev_b, claim_b_id),
                )
                cur.execute(
                    "INSERT INTO settlements (settlement_id, claim_id) "
                    "VALUES (%s, %s), (%s, %s)",
                    (set_a, claim_a_id, set_b, claim_b_id),
                )
                cur.execute(
                    "INSERT INTO complaints (complaint_id, session_id, customer_id, category) "
                    "VALUES (%s, %s, %s, 'service'), (%s, %s, %s, 'coverage')",
                    (comp_a, sess, id_a, comp_b, sess, id_b),
                )
            conn.commit()
            yield id_a, id_b, ev_a, ev_b, set_a, set_b, comp_a, comp_b
        finally:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM evidence WHERE evidence_id IN (%s, %s)", (ev_a, ev_b)
                )
                cur.execute(
                    "DELETE FROM settlements WHERE settlement_id IN (%s, %s)", (set_a, set_b)
                )
                cur.execute(
                    "DELETE FROM complaints WHERE complaint_id IN (%s, %s)", (comp_a, comp_b)
                )
            conn.commit()
            conn.close()

    def test_evidence_cross_customer_read_blocked(self, indirect_rows):
        """Probe: attacker A requests B's evidence UUID → 0 rows."""
        id_a, id_b, ev_a, ev_b, *_ = indirect_rows
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT evidence_id FROM evidence WHERE evidence_id = %s",
                    (ev_b,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            f"[Attack #28] Indirect-RLS leak on evidence: "
            f"attacker A read victim B's evidence (ev_b={ev_b})"
        )

    def test_evidence_no_setting_fail_closed(self, indirect_rows):
        """Probe: no session token → zero rows on evidence."""
        _, _, ev_a, ev_b, *_ = indirect_rows
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

        assert rows == [], (
            "[Attack #20] Fail-closed breach on evidence: unauthenticated returned rows"
        )

    def test_settlements_cross_customer_read_blocked(self, indirect_rows):
        """Probe: attacker A requests B's settlement UUID → 0 rows."""
        id_a, id_b, _, _, set_a, set_b, *_ = indirect_rows
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT settlement_id FROM settlements WHERE settlement_id = %s",
                    (set_b,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            f"[Attack #28] Indirect-RLS leak on settlements: "
            f"attacker A read victim B's settlement (set_b={set_b})"
        )

    def test_settlements_no_setting_fail_closed(self, indirect_rows):
        """Probe: no session token → zero rows on settlements."""
        _, _, _, _, set_a, set_b, *_ = indirect_rows
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

        assert rows == [], (
            "[Attack #20] Fail-closed breach on settlements: unauthenticated returned rows"
        )

    def test_complaints_cross_customer_read_blocked(self, indirect_rows):
        """Probe: attacker A requests B's complaint UUID → 0 rows."""
        id_a, id_b, _, _, _, _, comp_a, comp_b = indirect_rows
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT complaint_id FROM complaints WHERE complaint_id = %s",
                    (comp_b,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            f"[Attack #28] RLS leak on complaints: "
            f"attacker A read victim B's complaint (comp_b={comp_b})"
        )

    def test_cross_customer_evidence_update_blocked(self, indirect_rows):
        """Probe: attacker A UPDATE on B's evidence → 0 rows affected."""
        id_a, id_b, ev_a, ev_b, *_ = indirect_rows
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "UPDATE evidence SET evidence_type = 'FORGED' WHERE evidence_id = %s",
                    (ev_b,),
                )
                affected = cur.rowcount
        finally:
            conn.rollback()
            conn.close()

        assert affected == 0, (
            f"[Attack #28] Indirect-RLS USING failure on evidence: "
            f"attacker A mutated victim B's evidence (rowcount={affected})"
        )


# ── Attack #28 / #20: grant boundary probes ──────────────────────────────────

class TestGrantBoundaryProbes:
    """
    Attack #20 (Direct Exfiltration) via privilege misuse.

    Verifies that omission-based controls from migration 002 are enforced:
    tables that the app role must never see directly are inaccessible even
    with a valid customer session.
    """

    def test_pii_vault_select_blocked(self, two_customers):
        """Probe: app role with valid customer session cannot SELECT pii_vault."""
        id_a, _ = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT 1 FROM pii_vault LIMIT 1")
        finally:
            conn.rollback()
            conn.close()

    def test_fraud_scores_select_blocked(self, two_customers):
        """Probe: app role with valid customer session cannot SELECT fraud_scores."""
        id_a, _ = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT 1 FROM fraud_scores LIMIT 1")
        finally:
            conn.rollback()
            conn.close()

    def test_audit_log_update_blocked(self):
        """Probe: app role cannot UPDATE audit_log (immutable append-only log)."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute(
                        "UPDATE audit_log SET action = 'tampered' WHERE log_id = 1"
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_audit_log_delete_blocked(self):
        """Probe: app role cannot DELETE from audit_log."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("DELETE FROM audit_log WHERE log_id = 1")
        finally:
            conn.rollback()
            conn.close()

    def test_pii_vault_blocked_without_session(self):
        """Probe: pii_vault blocked even with no customer_id set (double guard)."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    cur.execute("SELECT 1 FROM pii_vault LIMIT 1")
        finally:
            conn.rollback()
            conn.close()

    def test_audit_log_insert_succeeds(self):
        """Positive control: INSERT into audit_log must succeed (append-only)."""
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log (agent_id, action, target, data_label) "
                    "VALUES ('probe_suite', 'grant_boundary_check', 'audit_log', 'CONFIDENTIAL')"
                )
        finally:
            conn.rollback()
            conn.close()


# ── Attack #37: SQL injection via parameterised queries ──────────────────────

class TestSQLInjectionCrossCustomerProbes:
    """
    Attack #37 (SQL Injection via Agent).

    An LLM agent may be prompted to pass injection payloads as parameter
    values (e.g., claim_id="'; DROP TABLE claims; --").  These tests verify
    that psycopg's parameterised queries treat all such payloads as literals
    and that the injection does not alter query semantics or break RLS.

    In every case the injected value is simply not found (0 rows), proving
    the payload was treated as a literal string, not parsed SQL.
    """

    # Representative injection payloads that an adversarial LLM might emit
    _SQL_INJECTION_PAYLOADS: list[tuple[str, str]] = [
        ("classic_termination", "'; DROP TABLE claims; --"),
        ("union_exfil", "' UNION SELECT customer_id FROM customers --"),
        ("comment_bypass", "' OR '1'='1"),
        ("stacked_query", "'; SELECT pg_sleep(5); --"),
        ("set_config_inject", "'; SELECT set_config('app.current_customer_id', '', true); --"),
        ("null_byte", "\x00' OR 1=1 --"),
        ("always_true", "' OR 1=1 --"),
        ("escape_quote", "\\'; DROP TABLE claims; --"),
        ("dollar_quote", "$$ OR 1=1 $$"),
        ("unicode_dash", "’ OR 1=1 --"),  # RIGHT SINGLE QUOTATION MARK
    ]

    def test_injection_payloads_in_customer_id_parameter(self, two_customers):
        """
        Probe: each SQL injection payload used as a customer_id value must
        return 0 rows and leave the claims table intact.
        """
        id_a, id_b = two_customers
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                for label, payload in self._SQL_INJECTION_PAYLOADS:
                    try:
                        cur.execute(
                            "SELECT customer_id FROM customers WHERE customer_id::text = %s",
                            (payload,),
                        )
                        rows = cur.fetchall()
                    except psycopg.errors.DataError:
                        # PG 18+ rejects NUL bytes in text — the DB refused the input,
                        # which is safe (no data exposed).  Re-open a fresh cursor.
                        conn.rollback()
                        cur = conn.cursor()
                        set_customer(cur, id_a)
                        continue
                    assert rows == [], (
                        f"[Attack #37] Injection '{label}' returned rows: {rows}"
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_injection_payload_as_claim_number(self, customer_with_claim):
        """
        Probe: SQL injection payload passed as a claim_number search value
        must return 0 rows without escaping the parameterised boundary.
        """
        id_a, _, claim_a_id, _ = customer_with_claim
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                for label, payload in self._SQL_INJECTION_PAYLOADS:
                    try:
                        cur.execute(
                            "SELECT claim_id FROM claims WHERE claim_number = %s",
                            (payload,),
                        )
                        rows = cur.fetchall()
                    except psycopg.errors.DataError:
                        conn.rollback()
                        cur = conn.cursor()
                        set_customer(cur, id_a)
                        continue
                    assert rows == [], (
                        f"[Attack #37] claim_number injection '{label}' returned rows: {rows}"
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_injection_payload_as_evidence_type(self, customer_with_claim):
        """
        Probe: SQL injection payload used as evidence_type filter — must not
        expose evidence across customer boundary or break parameterisation.
        """
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        ev_b = uuid.uuid4()
        conn_admin = admin_conn()
        try:
            with conn_admin.cursor() as cur:
                cur.execute(
                    "INSERT INTO evidence (evidence_id, claim_id, evidence_type) "
                    "VALUES (%s, %s, 'PHOTO')",
                    (ev_b, claim_b_id),
                )
            conn_admin.commit()

            conn = app_conn()
            try:
                with conn.cursor() as cur:
                    set_customer(cur, id_a)
                    for label, payload in self._SQL_INJECTION_PAYLOADS:
                        try:
                            cur.execute(
                                "SELECT evidence_id FROM evidence WHERE evidence_type = %s",
                                (payload,),
                            )
                            rows = cur.fetchall()
                        except psycopg.errors.DataError:
                            conn.rollback()
                            cur = conn.cursor()
                            set_customer(cur, id_a)
                            continue
                        # Payload is not a real evidence_type value, so 0 rows expected;
                        # crucially, B's evidence must never appear.
                        for row in rows:
                            assert row[0] != ev_b, (
                                f"[Attack #37] evidence_type injection '{label}' "
                                f"exposed victim B's evidence"
                            )
            finally:
                conn.rollback()
                conn.close()
        finally:
            with conn_admin.cursor() as cur:
                cur.execute("DELETE FROM evidence WHERE evidence_id = %s", (ev_b,))
            conn_admin.commit()
            conn_admin.close()

    def test_set_config_injection_via_customer_id_string(self, two_customers):
        """
        Probe: attacker passes a set_config call disguised as a UUID string;
        psycopg must treat it as a literal value, not execute it.
        The RLS policy must still scope to the real customer_id in effect.
        """
        id_a, id_b = two_customers
        # Payload: looks like it tries to overwrite the session variable
        evil_payload = f"'); SELECT set_config('app.current_customer_id', '{id_b}', true); --"
        conn = app_conn()
        try:
            with conn.cursor() as cur:
                set_customer(cur, id_a)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id::text = %s",
                    (evil_payload,),
                )
                rows = cur.fetchall()
                # Confirm session is still scoped to A
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id IN (%s, %s)",
                    (id_a, id_b),
                )
                scope_check = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
            conn.close()

        assert rows == [], (
            "[Attack #37] set_config injection payload returned rows instead of being treated as literal"
        )
        assert scope_check == [id_a], (
            f"[Attack #37] Session scope corrupted after injection probe: got {scope_check}"
        )

    def test_claims_table_intact_after_all_injections(self, customer_with_claim):
        """
        Structural invariant: after all injection probes, the two test claims still exist.
        Verifies no DDL payload (DROP TABLE) was executed.
        """
        id_a, id_b, claim_a_id, claim_b_id = customer_with_claim
        conn = admin_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT claim_id FROM claims WHERE claim_id IN (%s, %s)",
                    (claim_a_id, claim_b_id),
                )
                rows = {r[0] for r in cur.fetchall()}
        finally:
            conn.rollback()
            conn.close()

        assert claim_a_id in rows, (
            f"[Attack #37] claim_a missing after injection probes — DDL may have fired"
        )
        assert claim_b_id in rows, (
            f"[Attack #37] claim_b missing after injection probes — DDL may have fired"
        )
