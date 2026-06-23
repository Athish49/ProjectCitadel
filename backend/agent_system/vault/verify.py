"""Identity verification gate for the PII vault (task 1.2.7).

verify_identity() is the single allowed entry-point to the pii_vault table.
No agent module may import from this file directly — calls must go via the
identity-verifier actor which holds the appropriate capability token.

Architecture note
-----------------
pii_vault access is mediated entirely by the Postgres SECURITY DEFINER
function public.get_vault_data() (migration 006).  role_identity_verifier
holds no direct SELECT on pii_vault; the function runs as neondb_owner
(function owner) and returns only (customer_id, date_of_birth, ssn_last4).
The LEFT JOIN inside get_vault_data preserves the policy_not_found /
vault_row_missing audit distinction without exposing any other vault columns.

Lockout policy
--------------
3 FAIL_MATCH outcomes for a (session_id, policy_number) pair within the
same session triggers an immediate LOCKOUT on the next call.  The 3rd
failing attempt itself is recorded as FAIL_MATCH and is the last attempt
that receives a genuine credential check.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date

import psycopg

from agent_system.vault.crypto import constant_compare

MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class VerifyResult:
    verified: bool
    outcome: str          # "SUCCESS" | "FAIL_MATCH" | "LOCKOUT" | "NOT_FOUND"
    attempts_remaining: int


def verify_identity(
    conn: psycopg.Connection,
    *,
    policy_number: str,
    ssn_last4: str,
    dob_iso: str,
    session_id: uuid.UUID,
    trace_id: uuid.UUID | None = None,
) -> VerifyResult:
    """Verify identity by checking ssn_last4 + date_of_birth against pii_vault.

    Writes every attempt to identity_attempts.
    Writes a security_events row on FAIL_MATCH and LOCKOUT.
    Caller commits conn.  Never raises.
    """
    try:
        return _verify(conn, policy_number, ssn_last4, dob_iso, session_id, trace_id)
    except Exception:
        # Surface nothing to the caller — treat unexpected errors as non-match.
        return VerifyResult(verified=False, outcome="FAIL_MATCH", attempts_remaining=0)


def _verify(
    conn: psycopg.Connection,
    policy_number: str,
    ssn_last4: str,
    dob_iso: str,
    session_id: uuid.UUID,
    trace_id: uuid.UUID | None,
) -> VerifyResult:
    with conn.cursor() as cur:
        # ── Step 1: check lockout before touching vault ───────────────────
        cur.execute(
            """
            SELECT COUNT(*) FROM identity_attempts
            WHERE session_id = %s
              AND attempted_policy_number = %s
              AND outcome = 'FAIL_MATCH'
            """,
            (session_id, policy_number),
        )
        fail_count: int = cur.fetchone()[0]

        if fail_count >= MAX_ATTEMPTS:
            _insert_attempt(cur, session_id, None, policy_number, "LOCKOUT")
            _insert_security_event(
                cur,
                trace_id,
                event_type="identity_lockout",
                severity="warn",
                details={"policy_number": policy_number, "session_id": str(session_id)},
            )
            return VerifyResult(verified=False, outcome="LOCKOUT", attempts_remaining=0)

        # ── Steps 2+3: fetch customer + vault data via SECURITY DEFINER ──
        # get_vault_data() runs as the function owner (neondb_owner) so
        # role_identity_verifier never needs direct pii_vault access.
        # LEFT JOIN means: no row → policy_not_found; row with NULL ssn_last4
        # → vault_row_missing.
        cur.execute(
            "SELECT out_customer_id, out_date_of_birth, out_ssn_last4"
            " FROM public.get_vault_data(%s)",
            (policy_number,),
        )
        row = cur.fetchone()
        if row is None:
            _insert_attempt(cur, session_id, None, policy_number, "FAIL_MATCH")
            _insert_security_event(
                cur,
                trace_id,
                event_type="identity_fail_match",
                severity="warn",
                details={"reason": "policy_not_found"},
            )
            remaining = max(0, MAX_ATTEMPTS - (fail_count + 1))
            return VerifyResult(verified=False, outcome="FAIL_MATCH", attempts_remaining=remaining)

        customer_id: uuid.UUID = row[0]
        stored_dob: date = row[1]
        stored_last4: str | None = row[2]

        if stored_last4 is None:
            _insert_attempt(cur, session_id, customer_id, policy_number, "FAIL_MATCH")
            _insert_security_event(
                cur,
                trace_id,
                event_type="identity_fail_match",
                severity="warn",
                details={"reason": "vault_row_missing"},
            )
            remaining = max(0, MAX_ATTEMPTS - (fail_count + 1))
            return VerifyResult(verified=False, outcome="FAIL_MATCH", attempts_remaining=remaining)

        # ── Step 4: constant-time credential check ───────────────────────
        # Normalise DOB to ISO string for comparison.
        try:
            input_dob_str = date.fromisoformat(dob_iso).isoformat()
        except ValueError:
            input_dob_str = dob_iso
        stored_dob_str = stored_dob.isoformat()

        last4_match = constant_compare(ssn_last4.zfill(4), stored_last4.zfill(4))
        dob_match = constant_compare(input_dob_str, stored_dob_str)

        if last4_match and dob_match:
            _insert_attempt(cur, session_id, customer_id, policy_number, "SUCCESS")
            return VerifyResult(
                verified=True,
                outcome="SUCCESS",
                attempts_remaining=MAX_ATTEMPTS - fail_count,
            )

        _insert_attempt(cur, session_id, customer_id, policy_number, "FAIL_MATCH")
        _insert_security_event(
            cur,
            trace_id,
            event_type="identity_fail_match",
            severity="warn",
            details={"reason": "credential_mismatch"},
        )
        remaining = max(0, MAX_ATTEMPTS - (fail_count + 1))
        return VerifyResult(verified=False, outcome="FAIL_MATCH", attempts_remaining=remaining)


def _insert_attempt(
    cur: psycopg.Cursor,
    session_id: uuid.UUID,
    customer_id: uuid.UUID | None,
    policy_number: str,
    outcome: str,
) -> None:
    cur.execute(
        """
        INSERT INTO identity_attempts
            (session_id, customer_id, attempted_policy_number, outcome)
        VALUES (%s, %s, %s, %s)
        """,
        (session_id, customer_id, policy_number, outcome),
    )


def _insert_security_event(
    cur: psycopg.Cursor,
    trace_id: uuid.UUID | None,
    event_type: str,
    severity: str,
    details: dict,
) -> None:
    cur.execute(
        """
        INSERT INTO security_events (trace_id, event_type, severity, details)
        VALUES (%s, %s, %s, %s::jsonb)
        """,
        (trace_id, event_type, severity, json.dumps(details)),
    )
