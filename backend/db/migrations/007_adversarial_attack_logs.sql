-- Migration 007: Adversarial attack log persistence
--
-- Stores every attack attempt processed by the adversarial sandbox endpoint
-- (POST /showcase/playground/submit with attack_id set).
--
-- Written by: adversarial-api container (secureclaim_app role / DSN user)
-- Read by:    main backend's adversarial SSE endpoint for history + live polling
--
-- No RLS needed — not customer-scoped data; this is security telemetry.
-- No UPDATE or DELETE granted — append-only by design.

CREATE TABLE adversarial_attack_logs (
    id                   BIGSERIAL    PRIMARY KEY,
    trace_id             UUID         NOT NULL,
    session_id           UUID         NOT NULL,
    attack_id            INTEGER      NOT NULL,
    verdict              VARCHAR(30)  NOT NULL
        CHECK (verdict IN ('BLOCKED_INGRESS', 'EVADED_INGRESS', 'API_ERROR')),
    sanitizer_detections JSONB        NOT NULL DEFAULT '[]',
    chars_stripped       INTEGER      NOT NULL DEFAULT 0,
    is_breach            BOOLEAN      NOT NULL DEFAULT false,
    ts                   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- secureclaim_app writes; SELECT is via the superuser DSN used by SSE endpoints.
GRANT INSERT ON adversarial_attack_logs TO secureclaim_app;
GRANT USAGE  ON SEQUENCE adversarial_attack_logs_id_seq TO secureclaim_app;
