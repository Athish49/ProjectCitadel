"""Integration tests for per-agent DB roles (task 1.1.3).

Verifies that each role can access exactly the columns/tables specified in
Doc 03 §3 — no more, no less. One positive test and one negative test per
key constraint; SELECT * on column-restricted tables must also fail.
"""
import os
import uuid

import psycopg
import pytest
from psycopg.errors import InsufficientPrivilege

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN", "postgresql://postgres:postgres@localhost:5432/secureclaim"
)
ORCHESTRATOR_DSN = os.environ.get(
    "TEST_ORCHESTRATOR_DSN",
    "postgresql://role_orchestrator:role_orchestrator@localhost:5432/secureclaim",
)
INTAKE_ACTOR_DSN = os.environ.get(
    "TEST_INTAKE_ACTOR_DSN",
    "postgresql://role_intake_actor:role_intake_actor@localhost:5432/secureclaim",
)
IDENTITY_VERIFIER_DSN = os.environ.get(
    "TEST_IDENTITY_VERIFIER_DSN",
    "postgresql://role_identity_verifier:role_identity_verifier@localhost:5432/secureclaim",
)
CLAIMS_PROCESSOR_DSN = os.environ.get(
    "TEST_CLAIMS_PROCESSOR_DSN",
    "postgresql://role_claims_processor:role_claims_processor@localhost:5432/secureclaim",
)
SETTLEMENT_ACTOR_DSN = os.environ.get(
    "TEST_SETTLEMENT_ACTOR_DSN",
    "postgresql://role_settlement_actor:role_settlement_actor@localhost:5432/secureclaim",
)

# Module-level fixture IDs — deterministic so teardown finds them even on partial failures.
_cust_a = uuid.uuid4()
_policy_a = uuid.uuid4()
_claim_a = uuid.uuid4()
_evidence_a = uuid.uuid4()
_settlement_a = uuid.uuid4()
_fraud_a = uuid.uuid4()
_complaint_a = uuid.uuid4()
_attempt_a = uuid.uuid4()
_session_a = uuid.uuid4()
_token_a = uuid.uuid4()


def _set_customer(cur: psycopg.Cursor, customer_id: uuid.UUID) -> None:
    cur.execute(
        "SELECT set_config('app.current_customer_id', %s, true)",
        (str(customer_id),),
    )


def _conn(dsn: str) -> psycopg.Connection:
    return psycopg.connect(dsn, autocommit=False)


def setup_module(module: object) -> None:
    with psycopg.connect(ADMIN_DSN, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO customers
                       (customer_id, policy_number, first_name, last_name, email,
                        phone, date_of_birth, address_line1, city, state, zip_code)
                   VALUES (%s,'POL-ROLE-001','Alice','Roles','alice@roles.test',
                           '555-9001','1985-06-15','10 Role St','Testville','TX','75001')""",
                (_cust_a,),
            )
            cur.execute(
                """INSERT INTO policies
                       (policy_id, policy_number, customer_id, policy_status)
                   VALUES (%s,'POL-ROLE-001',%s,'ACTIVE')""",
                (_policy_a, _cust_a),
            )
            cur.execute(
                """INSERT INTO claims
                       (claim_id, claim_number, customer_id, policy_id,
                        incident_description, claim_stage)
                   VALUES (%s,'CLM-ROLE-001',%s,%s,'test incident','PROCESSING')""",
                (_claim_a, _cust_a, _policy_a),
            )
            cur.execute(
                "INSERT INTO evidence(evidence_id, claim_id, evidence_type) VALUES (%s,%s,'PHOTO')",
                (_evidence_a, _claim_a),
            )
            cur.execute(
                """INSERT INTO settlements
                       (settlement_id, claim_id, offered_amount, deductible_applied)
                   VALUES (%s,%s,5000.00,500.00)""",
                (_settlement_a, _claim_a),
            )
            cur.execute(
                """INSERT INTO fraud_scores
                       (score_id, claim_id, risk_score, risk_factors, decision)
                   VALUES (%s,%s,25,'{"flags":[]}'::jsonb,'CLEAR')""",
                (_fraud_a, _claim_a),
            )
            cur.execute(
                """INSERT INTO complaints
                       (complaint_id, session_id, customer_id, category, description)
                   VALUES (%s,%s,%s,'service','test complaint')""",
                (_complaint_a, _session_a, _cust_a),
            )
            cur.execute(
                """INSERT INTO identity_attempts
                       (attempt_id, session_id, customer_id,
                        attempted_policy_number, outcome)
                   VALUES (%s,%s,%s,'POL-ROLE-001','SUCCESS')""",
                (_attempt_a, _session_a, _cust_a),
            )
            cur.execute(
                """INSERT INTO capability_token_log
                       (token_id, issued_by, agent_id, tool, scope,
                        issued_at, expires_at)
                   VALUES (%s,'orchestrator','intake_actor','lookup_customer',
                           '{"allow":["lookup_customer"]}'::jsonb,
                           now(), now() + interval '5 minutes')""",
                (_token_a,),
            )
        conn.commit()


def teardown_module(module: object) -> None:
    with psycopg.connect(ADMIN_DSN, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_token_log WHERE token_id = %s", (_token_a,))
            cur.execute("DELETE FROM identity_attempts WHERE attempt_id = %s", (_attempt_a,))
            cur.execute("DELETE FROM complaints WHERE complaint_id = %s", (_complaint_a,))
            cur.execute("DELETE FROM fraud_scores WHERE score_id = %s", (_fraud_a,))
            cur.execute("DELETE FROM settlements WHERE settlement_id = %s", (_settlement_a,))
            cur.execute("DELETE FROM evidence WHERE evidence_id = %s", (_evidence_a,))
            cur.execute("DELETE FROM claims WHERE claim_id = %s", (_claim_a,))
            cur.execute("DELETE FROM policies WHERE policy_id = %s", (_policy_a,))
            cur.execute("DELETE FROM customers WHERE customer_id = %s", (_cust_a,))
        conn.commit()


# ── role_orchestrator ─────────────────────────────────────────────────────────


class TestOrchestratorRole:
    def test_can_select_customer_id(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT customer_id FROM customers WHERE customer_id = %s", (_cust_a,)
                )
                assert cur.fetchone() == (_cust_a,)
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_customer_first_name(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT first_name FROM customers WHERE customer_id = %s", (_cust_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_star_from_customers(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT * FROM customers WHERE customer_id = %s", (_cust_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_claim_stage(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT claim_stage FROM claims WHERE claim_id = %s", (_claim_a,)
                )
                assert cur.fetchone() == ("PROCESSING",)
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_claim_description(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT incident_description FROM claims WHERE claim_id = %s", (_claim_a,)
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_update_claim_stage(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "UPDATE claims SET claim_stage = 'DECIDED', updated_at = now() "
                    "WHERE claim_id = %s",
                    (_claim_a,),
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_insert_claim(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "INSERT INTO claims(claim_id, claim_number, customer_id, policy_id) "
                        "VALUES (%s,'CLM-X',%s,%s)",
                        (uuid.uuid4(), _cust_a, _policy_a),
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_settlement_status(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT approval_status, payout_status FROM settlements "
                    "WHERE settlement_id = %s",
                    (_settlement_a,),
                )
                assert cur.fetchone() == ("PENDING", "PENDING")
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_settlement_amount(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT offered_amount FROM settlements WHERE settlement_id = %s",
                        (_settlement_a,),
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_fraud_decision(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT decision FROM fraud_scores WHERE claim_id = %s", (_claim_a,)
                )
                assert cur.fetchone() == ("CLEAR",)
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_fraud_risk_score(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT risk_score FROM fraud_scores WHERE claim_id = %s", (_claim_a,)
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_audit_log(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log(agent_id, action, target, data_label) "
                    "VALUES ('orchestrator','state_transition','claims','CONFIDENTIAL')"
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_update_audit_log(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("UPDATE audit_log SET agent_id = 'x' WHERE log_id = 1")
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_pii_vault(self) -> None:
        conn = _conn(ORCHESTRATOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT customer_id FROM pii_vault")
        finally:
            conn.rollback()
            conn.close()


# ── role_intake_actor ─────────────────────────────────────────────────────────


class TestIntakeActorRole:
    def test_can_select_customer_name(self) -> None:
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT customer_id, first_name, last_name FROM customers "
                    "WHERE customer_id = %s",
                    (_cust_a,),
                )
                row = cur.fetchone()
                assert row is not None
                assert row[1] == "Alice"
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_customer_dob(self) -> None:
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT date_of_birth FROM customers WHERE customer_id = %s", (_cust_a,)
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_claim(self) -> None:
        new_claim = uuid.uuid4()
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "INSERT INTO claims(claim_id, claim_number, customer_id, policy_id) "
                    "VALUES (%s,'CLM-INTAKE-TST',%s,%s)",
                    (new_claim, _cust_a, _policy_a),
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_claims(self) -> None:
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT claim_id FROM claims WHERE claim_id = %s", (_claim_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_policies(self) -> None:
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT policy_id FROM policies WHERE customer_id = %s", (_cust_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_pii_vault(self) -> None:
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT customer_id FROM pii_vault")
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_audit_log(self) -> None:
        conn = _conn(INTAKE_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log(agent_id, action, target, data_label) "
                    "VALUES ('intake_actor','parser_emit','claims','CONFIDENTIAL')"
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()


# ── role_identity_verifier ────────────────────────────────────────────────────


class TestIdentityVerifierRole:
    def test_cannot_select_pii_vault(self) -> None:
        conn = _conn(IDENTITY_VERIFIER_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT customer_id FROM pii_vault")
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_identity_attempts(self) -> None:
        conn = _conn(IDENTITY_VERIFIER_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT outcome FROM identity_attempts WHERE attempt_id = %s", (_attempt_a,)
                )
                assert cur.fetchone() == ("SUCCESS",)
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_identity_attempt(self) -> None:
        conn = _conn(IDENTITY_VERIFIER_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO identity_attempts"
                    "    (attempt_id, session_id, attempted_policy_number, outcome) "
                    "VALUES (%s,%s,'POL-ROLE-001','FAIL_MATCH')",
                    (uuid.uuid4(), uuid.uuid4()),
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_claims(self) -> None:
        conn = _conn(IDENTITY_VERIFIER_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT claim_id FROM claims WHERE claim_id = %s", (_claim_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_customers(self) -> None:
        conn = _conn(IDENTITY_VERIFIER_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT customer_id FROM customers")
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_audit_log(self) -> None:
        conn = _conn(IDENTITY_VERIFIER_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log(agent_id, action, target, data_label) "
                    "VALUES ('identity_verifier','tool_call','identity_attempts','CONFIDENTIAL')"
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()


# ── role_claims_processor ─────────────────────────────────────────────────────


class TestClaimsProcessorRole:
    def test_can_select_policies_rls(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT policy_id FROM policies WHERE customer_id = %s", (_cust_a,)
                )
                assert cur.fetchone() is not None
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_vehicles_rls(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                # No vehicles in fixture; query should return empty, not error.
                cur.execute("SELECT vehicle_id FROM vehicles WHERE customer_id = %s", (_cust_a,))
                assert cur.fetchone() is None
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_claims_rls(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT claim_stage FROM claims WHERE claim_id = %s", (_claim_a,)
                )
                assert cur.fetchone() == ("PROCESSING",)
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_evidence_rls(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT sanitisation_status FROM evidence WHERE evidence_id = %s",
                    (_evidence_a,),
                )
                assert cur.fetchone() == ("PENDING",)
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_fraud_scores(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT decision FROM fraud_scores WHERE claim_id = %s", (_claim_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_complaints_rls(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT status FROM complaints WHERE complaint_id = %s", (_complaint_a,)
                )
                assert cur.fetchone() == ("OPEN",)
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_complaint(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "INSERT INTO complaints"
                    "    (complaint_id, session_id, customer_id, category, description) "
                    "VALUES (%s,%s,%s,'coverage','another complaint')",
                    (uuid.uuid4(), uuid.uuid4(), _cust_a),
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_pii_vault(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT customer_id FROM pii_vault")
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_settlements(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT settlement_id FROM settlements WHERE settlement_id = %s",
                        (_settlement_a,),
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_audit_log(self) -> None:
        conn = _conn(CLAIMS_PROCESSOR_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log(agent_id, action, target, data_label) "
                    "VALUES ('claims_processor','tool_call','claims','CONFIDENTIAL')"
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()


# ── role_settlement_actor ─────────────────────────────────────────────────────


class TestSettlementActorRole:
    def test_can_select_customer_address(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "SELECT customer_id, first_name, last_name, address_line1, city, state, zip_code "
                    "FROM customers WHERE customer_id = %s",
                    (_cust_a,),
                )
                row = cur.fetchone()
                assert row is not None
                assert row[2] == "Roles"  # last_name
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_customer_dob(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT date_of_birth FROM customers WHERE customer_id = %s", (_cust_a,)
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_star_from_customers(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT * FROM customers WHERE customer_id = %s", (_cust_a,))
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_claims_rls(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute("SELECT claim_stage FROM claims WHERE claim_id = %s", (_claim_a,))
                assert cur.fetchone() == ("PROCESSING",)
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_update_claim_stage(self) -> None:
        # P2: only orchestrator drives claim_stage transitions
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "UPDATE claims SET claim_stage = 'SETTLED' WHERE claim_id = %s",
                        (_claim_a,),
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_settlement(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                new_claim = uuid.uuid4()
                # Insert a new claim (via admin to set up FK) then test settlement INSERT.
                # Use existing _claim_a as FK; INSERT second settlement would violate UNIQUE,
                # so we verify via rowcount on a rolled-back attempt with a new claim.
                # Simpler: just attempt and confirm no privilege error (UNIQUE violation is ok).
                try:
                    cur.execute(
                        "INSERT INTO settlements(settlement_id, claim_id, offered_amount) "
                        "VALUES (%s,%s,1000.00)",
                        (uuid.uuid4(), _claim_a),
                    )
                except psycopg.errors.UniqueViolation:
                    pass  # expected — the privilege check already passed
        finally:
            conn.rollback()
            conn.close()

    def test_can_update_settlement(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                _set_customer(cur, _cust_a)
                cur.execute(
                    "UPDATE settlements SET payout_status = 'PROCESSED' "
                    "WHERE settlement_id = %s",
                    (_settlement_a,),
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()

    def test_can_select_fraud_decision(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT decision FROM fraud_scores WHERE claim_id = %s", (_claim_a,)
                )
                assert cur.fetchone() == ("CLEAR",)
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_fraud_risk_score(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute(
                        "SELECT risk_score FROM fraud_scores WHERE claim_id = %s", (_claim_a,)
                    )
        finally:
            conn.rollback()
            conn.close()

    def test_cannot_select_pii_vault(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                with pytest.raises(InsufficientPrivilege):
                    cur.execute("SELECT customer_id FROM pii_vault")
        finally:
            conn.rollback()
            conn.close()

    def test_can_insert_audit_log(self) -> None:
        conn = _conn(SETTLEMENT_ACTOR_DSN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO audit_log(agent_id, action, target, data_label) "
                    "VALUES ('settlement_actor','tool_call','settlements','CONFIDENTIAL')"
                )
                assert cur.rowcount == 1
        finally:
            conn.rollback()
            conn.close()
