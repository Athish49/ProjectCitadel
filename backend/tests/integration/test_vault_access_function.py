"""Integration tests for the get_vault_data() SECURITY DEFINER function (P12, migration 006).

Verifies:
  - role_identity_verifier has NO direct SELECT on pii_vault
  - role_identity_verifier CAN call get_vault_data() and get a result
  - secureclaim_app has NO direct SELECT on pii_vault
  - secureclaim_app CAN call get_vault_data() and get a result
  - The function is defined SECURITY DEFINER with SET search_path = ''
    (verified via pg_proc system catalog)
  - Correct return for unknown policy_number (no rows)
  - Correct return for known policy_number (row with ssn_last4)
"""
from __future__ import annotations

import os
import uuid
from datetime import date

import psycopg
import pytest
from psycopg.errors import InsufficientPrivilege

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN", "postgresql://postgres:postgres@localhost:5432/secureclaim"
)
IDENTITY_VERIFIER_DSN = os.environ.get(
    "TEST_IDENTITY_VERIFIER_DSN",
    "postgresql://role_identity_verifier:role_identity_verifier@localhost:5432/secureclaim",
)
APP_DSN = os.environ.get(
    "TEST_APP_DSN",
    "postgresql://secureclaim_app:secureclaim_app@localhost:5432/secureclaim",
)

# Deterministic IDs so teardown finds rows even on partial failures.
_CUST_ID = uuid.UUID("00000006-0000-0000-0000-000000000001")
_POLICY_NUM = "POL-VAULT-FUNC-001"
_DOB = date(1985, 7, 22)
_SSN_LAST4 = "6789"


@pytest.fixture(scope="module", autouse=True)
def _seed_and_teardown():
    """Insert one customer + pii_vault row; remove both after all tests in this module."""
    with psycopg.connect(ADMIN_DSN, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO customers
                    (customer_id, policy_number, first_name, last_name, email, phone,
                     date_of_birth, address_line1, city, state, zip_code)
                VALUES (%s, %s, 'Vault', 'TestUser', 'vault@test.example', '5550000001',
                        %s, '1 Vault St', 'Testville', 'TX', '00001')
                ON CONFLICT (customer_id) DO NOTHING
                """,
                (_CUST_ID, _POLICY_NUM, _DOB),
            )
            cur.execute(
                """
                INSERT INTO pii_vault (customer_id, ssn_last4, ssn_hash)
                VALUES (%s, %s, 'deadbeef')
                ON CONFLICT (customer_id) DO NOTHING
                """,
                (_CUST_ID, _SSN_LAST4),
            )
        conn.commit()

    yield

    with psycopg.connect(ADMIN_DSN, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pii_vault WHERE customer_id = %s", (_CUST_ID,))
            cur.execute("DELETE FROM customers WHERE customer_id = %s", (_CUST_ID,))
        conn.commit()


# ── Negative: direct pii_vault access is denied ──────────────────────────────


class TestDirectPiiVaultAccessDenied:
    def test_identity_verifier_cannot_select_pii_vault(self):
        with psycopg.connect(IDENTITY_VERIFIER_DSN) as conn:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT ssn_last4 FROM pii_vault LIMIT 1")

    def test_app_role_cannot_select_pii_vault(self):
        with psycopg.connect(APP_DSN) as conn:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT ssn_last4 FROM pii_vault LIMIT 1")

    def test_identity_verifier_cannot_select_star_pii_vault(self):
        with psycopg.connect(IDENTITY_VERIFIER_DSN) as conn:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT * FROM pii_vault LIMIT 1")


# ── Positive: get_vault_data() is callable and returns correct data ───────────


class TestGetVaultDataFunction:
    def test_identity_verifier_can_call_function_known_policy(self):
        with psycopg.connect(IDENTITY_VERIFIER_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT out_customer_id, out_date_of_birth, out_ssn_last4"
                    " FROM public.get_vault_data(%s)",
                    (_POLICY_NUM,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == _CUST_ID
        assert row[1] == _DOB
        assert row[2] == _SSN_LAST4

    def test_app_role_can_call_function_known_policy(self):
        with psycopg.connect(APP_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT out_customer_id, out_date_of_birth, out_ssn_last4"
                    " FROM public.get_vault_data(%s)",
                    (_POLICY_NUM,),
                )
                row = cur.fetchone()
        assert row is not None
        assert row[0] == _CUST_ID
        assert row[1] == _DOB
        assert row[2] == _SSN_LAST4

    def test_unknown_policy_returns_no_rows_via_identity_verifier(self):
        with psycopg.connect(IDENTITY_VERIFIER_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT out_customer_id FROM public.get_vault_data(%s)",
                    ("POL-DOES-NOT-EXIST",),
                )
                row = cur.fetchone()
        assert row is None

    def test_unknown_policy_returns_no_rows_via_app_role(self):
        with psycopg.connect(APP_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT out_customer_id FROM public.get_vault_data(%s)",
                    ("POL-DOES-NOT-EXIST",),
                )
                row = cur.fetchone()
        assert row is None


# ── Catalog: verify SECURITY DEFINER + search_path hardening ─────────────────


class TestFunctionHardening:
    def test_function_is_security_definer(self):
        with psycopg.connect(ADMIN_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT prosecdef
                    FROM pg_proc
                    WHERE proname = 'get_vault_data'
                      AND pronamespace = (
                          SELECT oid FROM pg_namespace WHERE nspname = 'public'
                      )
                    """,
                )
                row = cur.fetchone()
        assert row is not None, "get_vault_data function not found"
        assert row[0] is True, "get_vault_data must be SECURITY DEFINER"

    def test_function_has_locked_search_path(self):
        with psycopg.connect(ADMIN_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT proconfig
                    FROM pg_proc
                    WHERE proname = 'get_vault_data'
                      AND pronamespace = (
                          SELECT oid FROM pg_namespace WHERE nspname = 'public'
                      )
                    """,
                )
                row = cur.fetchone()
        assert row is not None, "get_vault_data function not found"
        config: list[str] | None = row[0]
        assert config is not None, "get_vault_data must have SET search_path"
        assert any("search_path" in c for c in config), (
            f"search_path not locked; proconfig={config}"
        )

    def test_public_cannot_execute_function(self):
        """PUBLIC execute should be revoked; only granted roles can call it.

        In pg_proc, an ACL entry for PUBLIC (empty grantee) granting EXECUTE
        looks like '=X/<owner>'.  We verify no such entry exists.
        """
        with psycopg.connect(ADMIN_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        proacl IS NOT NULL AND NOT EXISTS (
                            SELECT 1 FROM unnest(proacl) AS ace
                            WHERE ace::text LIKE '=X/%%'
                        ) AS public_revoked
                    FROM pg_proc
                    WHERE proname = 'get_vault_data'
                      AND pronamespace = (
                          SELECT oid FROM pg_namespace WHERE nspname = 'public'
                      )
                    """,
                )
                row = cur.fetchone()
        assert row is not None, "get_vault_data function not found"
        assert row[0] is True, "EXECUTE should NOT be granted to PUBLIC"
