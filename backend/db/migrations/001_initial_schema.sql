-- Migration 001: Initial schema
-- Creates all tables per Doc 03 §2. Enables RLS + FORCE RLS on all customer-scoped tables.
-- RLS policies use current_setting('app.current_customer_id', true) — missing_ok=true
-- means an unset customer_id returns NULL, causing all rows to be hidden (fail-closed).

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── customers (PERSONAL) ────────────────────────────────────────────────────
CREATE TABLE customers (
    customer_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_number   VARCHAR(20) UNIQUE NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    date_of_birth   DATE        NOT NULL,
    address_line1   VARCHAR(200),
    city            VARCHAR(100),
    state           VARCHAR(50),
    zip_code        VARCHAR(10),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers FORCE ROW LEVEL SECURITY;

CREATE POLICY customers_self_only ON customers
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id', true)::uuid)
    WITH CHECK (customer_id = current_setting('app.current_customer_id', true)::uuid);


-- ── pii_vault (SECRET) ──────────────────────────────────────────────────────
-- No agent has direct SELECT on this table.
-- Access only via the server-side verify_identity() function (Sprint 1.2.7).
CREATE TABLE pii_vault (
    customer_id             UUID    PRIMARY KEY REFERENCES customers(customer_id),
    ssn_hash                BYTEA   NOT NULL,
    ssn_last4               VARCHAR(4) NOT NULL,
    drivers_license_enc     BYTEA,
    dl_iv                   BYTEA,
    bank_routing_enc        BYTEA,
    bank_account_enc        BYTEA,
    ba_iv                   BYTEA,
    br_iv                   BYTEA,
    security_answer_hash    BYTEA,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- No RLS; access restricted entirely via GRANT (no SELECT granted to any app role).


-- ── policies (CONFIDENTIAL) ─────────────────────────────────────────────────
CREATE TABLE policies (
    policy_id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_number       VARCHAR(20) UNIQUE NOT NULL,
    customer_id         UUID        NOT NULL REFERENCES customers(customer_id),
    policy_type         VARCHAR(50),
    policy_csl          VARCHAR(20),
    policy_deductible   INTEGER,
    coverage_type       VARCHAR(50),
    policy_bind_date    DATE,
    policy_expiry_date  DATE,
    policy_status       VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (policy_status IN ('ACTIVE', 'LAPSED', 'CANCELLED')),
    auto_approve_limit  INTEGER     NOT NULL DEFAULT 10000
);

ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies FORCE ROW LEVEL SECURITY;

CREATE POLICY policies_customer_scope ON policies
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id', true)::uuid)
    WITH CHECK (customer_id = current_setting('app.current_customer_id', true)::uuid);


-- ── vehicles (PERSONAL) ─────────────────────────────────────────────────────
CREATE TABLE vehicles (
    vehicle_id  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID        NOT NULL REFERENCES customers(customer_id),
    policy_id   UUID        NOT NULL REFERENCES policies(policy_id),
    auto_make   VARCHAR(100),
    auto_model  VARCHAR(100),
    auto_year   INTEGER,
    vin         VARCHAR(17)
);

ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles FORCE ROW LEVEL SECURITY;

CREATE POLICY vehicles_customer_scope ON vehicles
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id', true)::uuid)
    WITH CHECK (customer_id = current_setting('app.current_customer_id', true)::uuid);


-- ── claims (CONFIDENTIAL) ───────────────────────────────────────────────────
CREATE TABLE claims (
    claim_id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_number            VARCHAR(20) UNIQUE NOT NULL,
    customer_id             UUID        NOT NULL REFERENCES customers(customer_id),
    policy_id               UUID        NOT NULL REFERENCES policies(policy_id),
    incident_date           DATE,
    incident_type           VARCHAR(50),
    incident_description    TEXT,
    total_claim_amount      NUMERIC(10, 2),
    claim_stage             VARCHAR(30) NOT NULL DEFAULT 'INTAKE'
        CHECK (claim_stage IN (
            'INTAKE', 'IDENTITY_PENDING', 'IDENTITY_VERIFIED',
            'PROCESSING', 'DECIDED', 'SETTLED', 'ESCALATED', 'DENIED', 'CLOSED'
        )),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims FORCE ROW LEVEL SECURITY;

CREATE POLICY claims_customer_scope ON claims
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id', true)::uuid)
    WITH CHECK (customer_id = current_setting('app.current_customer_id', true)::uuid);


-- ── evidence (CONFIDENTIAL; raw bytes UNTRUSTED until sanitised) ────────────
-- No customer_id column; RLS policies join through claims.
CREATE TABLE evidence (
    evidence_id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id                UUID        NOT NULL REFERENCES claims(claim_id),
    evidence_type           VARCHAR(20) NOT NULL CHECK (evidence_type IN ('PHOTO', 'PDF', 'OTHER')),
    original_filename       VARCHAR(200),
    sha256_original         CHAR(64),
    sanitised_path          VARCHAR(500),
    sha256_sanitised        CHAR(64),
    sanitisation_status     VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (sanitisation_status IN ('PENDING', 'CLEAN', 'FLAGGED', 'REJECTED')),
    sanitisation_flags      JSONB,
    extracted_text_label    VARCHAR(20) NOT NULL DEFAULT 'UNTRUSTED',
    uploaded_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence FORCE ROW LEVEL SECURITY;

CREATE POLICY evidence_customer_scope ON evidence
    FOR ALL
    USING (claim_id IN (
        SELECT claim_id FROM claims
        WHERE customer_id = current_setting('app.current_customer_id', true)::uuid
    ))
    WITH CHECK (claim_id IN (
        SELECT claim_id FROM claims
        WHERE customer_id = current_setting('app.current_customer_id', true)::uuid
    ));


-- ── fraud_scores (SECRET) ───────────────────────────────────────────────────
-- Never customer-visible. Claims processor accesses via score_fraud() tool only.
-- IFC label on risk_score + risk_factors is SECRET; only decision reaches the orchestrator.
CREATE TABLE fraud_scores (
    score_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id        UUID        NOT NULL UNIQUE REFERENCES claims(claim_id),
    risk_score      INTEGER     CHECK (risk_score BETWEEN 0 AND 100),
    risk_factors    JSONB,
    decision        VARCHAR(20) NOT NULL CHECK (decision IN ('CLEAR', 'FLAG', 'DENY')),
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- No RLS; access restricted entirely via GRANT (no SELECT granted to customer-facing roles).


-- ── settlements (CONFIDENTIAL) ──────────────────────────────────────────────
-- No customer_id column; RLS joins through claims.
CREATE TABLE settlements (
    settlement_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id            UUID        NOT NULL UNIQUE REFERENCES claims(claim_id),
    offered_amount      NUMERIC(10, 2),
    deductible_applied  NUMERIC(10, 2),
    approval_status     VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (approval_status IN ('PENDING', 'AUTO_APPROVED', 'HUMAN_APPROVED', 'DENIED')),
    payout_status       VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (payout_status IN ('PENDING', 'PROCESSED', 'FAILED')),
    payout_reference    VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements FORCE ROW LEVEL SECURITY;

CREATE POLICY settlements_customer_scope ON settlements
    FOR ALL
    USING (claim_id IN (
        SELECT claim_id FROM claims
        WHERE customer_id = current_setting('app.current_customer_id', true)::uuid
    ))
    WITH CHECK (claim_id IN (
        SELECT claim_id FROM claims
        WHERE customer_id = current_setting('app.current_customer_id', true)::uuid
    ));


-- ── audit_log (CONFIDENTIAL, append-only, hash-chained) ─────────────────────
-- INSERT-only for application roles; enforced via GRANT in migration 002.
CREATE TABLE audit_log (
    log_id          BIGSERIAL   PRIMARY KEY,
    trace_id        UUID,
    prev_hash       CHAR(64),
    row_hash        CHAR(64),
    agent_id        VARCHAR(50),
    action          VARCHAR(100),
    target          VARCHAR(200),
    details         JSONB,
    data_label      VARCHAR(20),
    security_event  BOOLEAN     NOT NULL DEFAULT false,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- No RLS; log is INSERT-only — UPDATE/DELETE not granted to any app role.


-- ── capability_token_log (CONFIDENTIAL) ─────────────────────────────────────
CREATE TABLE capability_token_log (
    token_id    UUID        PRIMARY KEY,
    issued_by   VARCHAR(50) NOT NULL,
    agent_id    VARCHAR(50) NOT NULL,
    tool        VARCHAR(100) NOT NULL,
    scope       JSONB       NOT NULL,
    issued_at   TIMESTAMPTZ NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    use_result  VARCHAR(20)
        CHECK (use_result IN ('OK', 'DENIED_SCOPE', 'DENIED_EXPIRED', 'DENIED_SIGNATURE'))
);


-- ── security_events (CONFIDENTIAL) ──────────────────────────────────────────
CREATE TABLE security_events (
    event_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id    UUID,
    event_type  VARCHAR(100) NOT NULL,
    attack_id   INTEGER,
    severity    VARCHAR(10) NOT NULL CHECK (severity IN ('info', 'warn', 'critical')),
    details     JSONB,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── identity_attempts (CONFIDENTIAL) ────────────────────────────────────────
CREATE TABLE identity_attempts (
    attempt_id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID        NOT NULL,
    customer_id             UUID,
    attempted_policy_number VARCHAR(20) NOT NULL,
    outcome                 VARCHAR(20) NOT NULL
        CHECK (outcome IN ('SUCCESS', 'FAIL_MATCH', 'LOCKOUT')),
    ts                      TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ── complaints (CONFIDENTIAL) ────────────────────────────────────────────────
CREATE TABLE complaints (
    complaint_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID        NOT NULL,
    customer_id         UUID        NOT NULL REFERENCES customers(customer_id),
    related_claim_id    UUID        REFERENCES claims(claim_id),
    category            VARCHAR(50) NOT NULL
        CHECK (category IN ('service', 'coverage', 'decision', 'process', 'other')),
    description         TEXT,
    status              VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'ESCALATED', 'RESOLVED')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE complaints ENABLE ROW LEVEL SECURITY;
ALTER TABLE complaints FORCE ROW LEVEL SECURITY;

CREATE POLICY complaints_customer_scope ON complaints
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id', true)::uuid)
    WITH CHECK (customer_id = current_setting('app.current_customer_id', true)::uuid);
