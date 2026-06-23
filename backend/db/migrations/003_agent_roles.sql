-- Migration 003: Per-agent DB roles with column-scoped GRANTs
-- Implements Doc 03 §3 access matrix.
--
-- Six roles created here:
--   role_audit_writer       — NOLOGIN group; inherited by all agent roles for audit_log INSERT
--   role_orchestrator       — state-machine driver; sole role with UPDATE on claims.claim_stage (P2)
--   role_intake_actor       — customer name lookup + new claim INSERT
--   role_identity_verifier  — identity_attempts read/write; NO direct pii_vault access
--   role_claims_processor   — RLS read on policies/vehicles/claims/evidence; complaints read/write
--   role_settlement_actor   — customer address lookup + settlements write; NO claim_stage UPDATE (P2)
--
-- Parsers (intake_parser, document_parser) are quarantined sub-processes with no direct DB
-- connections; the orchestrator logs audit rows on their behalf. They will get roles if they
-- ever need direct DB access (sprint 4.x). For now they inherit the orchestrator's audit path.
--
-- All login roles: NOSUPERUSER NOBYPASSRLS — RLS is the authoritative boundary.

-- ── role_audit_writer (NOLOGIN group role) ────────────────────────────────────
-- Every agent role is a member; provides INSERT on audit_log via role inheritance.
CREATE ROLE role_audit_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO role_audit_writer;
GRANT INSERT ON audit_log TO role_audit_writer;
GRANT USAGE ON SEQUENCE audit_log_log_id_seq TO role_audit_writer;


-- ── role_orchestrator ─────────────────────────────────────────────────────────
-- Drives the claims state machine. The ONLY role with UPDATE on claims.claim_stage (P2).
-- Sees the minimum fields needed per table; column grants enforce this at the DB layer.
CREATE ROLE role_orchestrator
    WITH LOGIN PASSWORD 'role_orchestrator'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO role_orchestrator', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO role_orchestrator;
GRANT role_audit_writer TO role_orchestrator;

-- customers: customer_id only (RLS active)
GRANT SELECT(customer_id) ON customers TO role_orchestrator;
-- claims: id + stage for state-machine transitions; UPDATE limited to claim_stage + updated_at
GRANT SELECT(claim_id, customer_id, claim_stage) ON claims TO role_orchestrator;
GRANT UPDATE(claim_stage, updated_at) ON claims TO role_orchestrator;
-- settlements: status check only (RLS via join through claims)
GRANT SELECT(settlement_id, claim_id, approval_status, payout_status) ON settlements TO role_orchestrator;
-- fraud_scores: decision only — risk_score and risk_factors are SECRET and never reach orchestrator
GRANT SELECT(score_id, claim_id, decision) ON fraud_scores TO role_orchestrator;
-- complaints: id + status to drive ESCALATED transition
GRANT SELECT(complaint_id, customer_id, status) ON complaints TO role_orchestrator;
-- capability_token_log: orchestrator issues and records all capability tokens
GRANT SELECT, INSERT, UPDATE ON capability_token_log TO role_orchestrator;
-- security_events: read + write
GRANT SELECT, INSERT ON security_events TO role_orchestrator;


-- ── role_intake_actor ─────────────────────────────────────────────────────────
-- Looks up customer name to confirm identity pre-claim; inserts new claim records.
-- No SELECT on claims (it only writes them); no access to PII or financial tables.
CREATE ROLE role_intake_actor
    WITH LOGIN PASSWORD 'role_intake_actor'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO role_intake_actor', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO role_intake_actor;
GRANT role_audit_writer TO role_intake_actor;

-- customers: id + name only (RLS active); no DOB, no contact details, no address
GRANT SELECT(customer_id, first_name, last_name) ON customers TO role_intake_actor;
-- claims: INSERT new claims only; no SELECT or UPDATE (orchestrator reads them)
GRANT INSERT ON claims TO role_intake_actor;
-- capability_token_log: SELECT to verify tokens received from orchestrator
GRANT SELECT ON capability_token_log TO role_intake_actor;
-- security_events: INSERT for logging injection findings during intake
GRANT INSERT ON security_events TO role_intake_actor;


-- ── role_identity_verifier ────────────────────────────────────────────────────
-- Tracks verification attempts and enforces lockout. No direct pii_vault access —
-- identity is verified via verify_identity() SECURITY DEFINER function (sprint 1.2.7).
CREATE ROLE role_identity_verifier
    WITH LOGIN PASSWORD 'role_identity_verifier'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO role_identity_verifier', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO role_identity_verifier;
GRANT role_audit_writer TO role_identity_verifier;

-- identity_attempts: full read-write to record outcomes and check lockout counts
GRANT SELECT, INSERT ON identity_attempts TO role_identity_verifier;
-- pii_vault: NO grant — access only via SECURITY DEFINER function (sprint 1.2.7)
-- capability_token_log: SELECT to verify tokens
GRANT SELECT ON capability_token_log TO role_identity_verifier;
-- security_events: INSERT for lockout and verification-failure events
GRANT INSERT ON security_events TO role_identity_verifier;


-- ── role_claims_processor ─────────────────────────────────────────────────────
-- Reads all customer-scoped claim data (RLS enforced). Writes complaint records.
-- No direct access to fraud_scores — uses score_fraud() SECURITY DEFINER (sprint 4.1.3).
CREATE ROLE role_claims_processor
    WITH LOGIN PASSWORD 'role_claims_processor'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO role_claims_processor', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO role_claims_processor;
GRANT role_audit_writer TO role_claims_processor;

-- policies: RLS read own customer's policy
GRANT SELECT ON policies TO role_claims_processor;
-- vehicles: RLS read own
GRANT SELECT ON vehicles TO role_claims_processor;
-- claims: RLS read own
GRANT SELECT ON claims TO role_claims_processor;
-- evidence: RLS read (indirect via claims join); processors read sanitised artefacts
GRANT SELECT ON evidence TO role_claims_processor;
-- fraud_scores: NO SELECT — function-only via score_fraud() SECURITY DEFINER (sprint 4.1.3)
-- complaints: RLS read/write own — creates complaint records, reads own history
GRANT SELECT, INSERT, UPDATE ON complaints TO role_claims_processor;
-- capability_token_log: SELECT to verify received tokens
GRANT SELECT ON capability_token_log TO role_claims_processor;
-- security_events: read + write
GRANT SELECT, INSERT ON security_events TO role_claims_processor;


-- ── role_settlement_actor ─────────────────────────────────────────────────────
-- Reads customer address for payout; writes settlement records.
-- Does NOT update claims.claim_stage — that transition (→ SETTLED) belongs to the
-- orchestrator after observing settlements.payout_status = PROCESSED (P2).
CREATE ROLE role_settlement_actor
    WITH LOGIN PASSWORD 'role_settlement_actor'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO role_settlement_actor', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO role_settlement_actor;
GRANT role_audit_writer TO role_settlement_actor;

-- customers: id + name + address fields (RLS active); no DOB, no email/phone
GRANT SELECT(customer_id, first_name, last_name, address_line1, city, state, zip_code)
    ON customers TO role_settlement_actor;
-- claims: RLS read own; no UPDATE — claim_stage transitions owned by orchestrator (P2)
GRANT SELECT ON claims TO role_settlement_actor;
-- settlements: full write access; RLS is enforced via join through claims
GRANT SELECT, INSERT, UPDATE ON settlements TO role_settlement_actor;
-- fraud_scores: decision only — gates payout authorisation; risk details remain SECRET
GRANT SELECT(score_id, claim_id, decision) ON fraud_scores TO role_settlement_actor;
-- capability_token_log: SELECT to verify received tokens
GRANT SELECT ON capability_token_log TO role_settlement_actor;
-- security_events: INSERT for payout-related security events
GRANT INSERT ON security_events TO role_settlement_actor;
