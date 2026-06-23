-- Migration 006: SECURITY DEFINER function for pii_vault access (P12, attack #17).
--
-- get_vault_data() is the sole entry-point to pii_vault data for
-- role_identity_verifier and secureclaim_app.  Both roles hold NO direct
-- SELECT on pii_vault (see migration 003 / 002); this function escalates
-- privilege only for the duration of its execution.
--
-- Hardening:
--   SET search_path = ''        — prevents caller-controlled search_path injection
--   REVOKE EXECUTE FROM PUBLIC  — PostgreSQL grants EXECUTE to PUBLIC by default
--   STABLE                      — read-only; allows query planner optimisation
--   Schema-qualified refs       — all table references use public.<table>
--
-- LEFT JOIN (not INNER JOIN) is intentional: a customer row with no pii_vault
-- row returns (customer_id, dob, NULL) so verify.py can audit "vault_row_missing"
-- separately from "policy_not_found" (no row returned at all).

CREATE OR REPLACE FUNCTION public.get_vault_data(p_policy_number TEXT)
RETURNS TABLE(
    out_customer_id   UUID,
    out_date_of_birth DATE,
    out_ssn_last4     VARCHAR(4)
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = ''
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.customer_id,
        c.date_of_birth,
        v.ssn_last4
    FROM public.customers c
    LEFT JOIN public.pii_vault v ON v.customer_id = c.customer_id
    WHERE c.policy_number = p_policy_number;
END;
$$;

-- Revoke default PUBLIC execute before granting to specific roles.
REVOKE EXECUTE ON FUNCTION public.get_vault_data(TEXT) FROM PUBLIC;

-- Grant to the two roles that perform identity verification.
GRANT EXECUTE ON FUNCTION public.get_vault_data(TEXT) TO role_identity_verifier;
GRANT EXECUTE ON FUNCTION public.get_vault_data(TEXT) TO secureclaim_app;
