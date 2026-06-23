-- Migration 004: Grant SELECT(log_id, row_hash) on audit_log to audit writers
--
-- append_log() needs to read the previous row_hash to compute the next link
-- in the hash chain.  The hash is a SHA-256 digest — it contains no PII.
-- All agent roles inherit role_audit_writer; secureclaim_app writes via the
-- egress filter and must also be able to chain.
--
-- We grant only the two columns needed for chaining; the rest of the audit
-- content (action, target, details, data_label, …) remains unreadable to
-- non-admin roles.

GRANT SELECT(log_id, row_hash) ON audit_log TO role_audit_writer;
GRANT SELECT(log_id, row_hash) ON audit_log TO secureclaim_app;
