-- Migration 002: Application role for RLS enforcement
-- Creates secureclaim_app — the non-superuser role the application connects as.
-- RLS is enforced on this role (NOBYPASSRLS is explicit; it is also the default for non-superusers).
-- Per-agent restricted roles (role_intake_actor, role_claims_processor, etc.) are created
-- in migration 003 as part of Sprint 1.1.3.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'secureclaim_app') THEN
        CREATE ROLE secureclaim_app
            WITH LOGIN
            PASSWORD 'secureclaim_app'
            NOSUPERUSER
            NOBYPASSRLS
            NOCREATEDB
            NOCREATEROLE;
    END IF;
END
$$;

DO $$ BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO secureclaim_app', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO secureclaim_app;

-- ── Customer-scoped tables: read + write (RLS enforces per-customer isolation) ──
GRANT SELECT, INSERT, UPDATE ON customers            TO secureclaim_app;
GRANT SELECT, INSERT, UPDATE ON policies             TO secureclaim_app;
GRANT SELECT, INSERT, UPDATE ON vehicles             TO secureclaim_app;
GRANT SELECT, INSERT, UPDATE ON claims               TO secureclaim_app;
GRANT SELECT, INSERT, UPDATE ON evidence             TO secureclaim_app;
GRANT SELECT, INSERT, UPDATE ON settlements          TO secureclaim_app;
GRANT SELECT, INSERT, UPDATE ON complaints           TO secureclaim_app;

-- ── SECRET tables: no direct access for secureclaim_app ─────────────────────
-- pii_vault:   accessible only via verify_identity() server-side function (Sprint 1.2.7)
-- fraud_scores: accessible only via score_fraud() server-side function  (Sprint 4.1.3)
-- (No GRANT issued — omission is the control.)

-- ── Audit log: INSERT-only (no UPDATE, no DELETE) ───────────────────────────
GRANT INSERT                  ON audit_log           TO secureclaim_app;
GRANT USAGE                   ON SEQUENCE audit_log_log_id_seq TO secureclaim_app;

-- ── Supporting tables: read + write ─────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE  ON capability_token_log TO secureclaim_app;
GRANT SELECT, INSERT          ON security_events       TO secureclaim_app;
GRANT SELECT, INSERT          ON identity_attempts     TO secureclaim_app;
