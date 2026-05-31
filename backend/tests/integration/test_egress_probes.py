"""
Sprint 5.1.5 — URL/PII Egress Adversarial Probe Suite (Integration Layer)
==========================================================================

DB-backed probes that run filter_output() against a live PostgreSQL connection
and verify that:
  - Each violation type writes the correct audit_log row (action, security_event)
  - The audit hash-chain stays intact after multiple violation events
  - Stacked violations produce the correct number and order of log entries

Attack IDs covered:
  - Attack #25 (URL-based Exfiltration)
  - Attack #20 (Direct Exfiltration via PII leakage / SECRET label)

Prerequisites: `make up && make migrate` must have run successfully.
"""

from __future__ import annotations

import os
import uuid

import psycopg
from psycopg.rows import dict_row
import pytest

from agent_system.egress.filter import (
    MAX_OUTPUT_CHARS,
    REFUSAL_MESSAGE,
    filter_output,
)
from agent_system.ifc.labels import DataLabel, Label
from audit.chain import verify_chain

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

# ── labels ───────────────────────────────────────────────────────────────────
_PUBLIC = Label(level=DataLabel.PUBLIC)
_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL)
_SECRET = Label(level=DataLabel.SECRET)

# ── helpers ─────────────────────────────────────────────────────────────────

def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def _app() -> psycopg.Connection:
    return psycopg.connect(APP_DSN, autocommit=False)


def _audit_rows_for_trace(
    admin_conn: psycopg.Connection, trace_id: uuid.UUID
) -> list[dict]:
    with admin_conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT log_id, agent_id, action, security_event, details "
            "FROM audit_log WHERE trace_id = %s ORDER BY log_id",
            (trace_id,),
        )
        return cur.fetchall()


def _run_filter(
    text: str,
    label: Label = _PUBLIC,
    *,
    agent_id: str = "probe_agent",
    trace_id: uuid.UUID | None = None,
) -> tuple[object, uuid.UUID]:
    """Run filter_output with a real app-role connection.  Commits.  Returns (result, trace_id)."""
    if trace_id is None:
        trace_id = uuid.uuid4()
    conn = _app()
    try:
        result = filter_output(
            conn,
            text=text,
            source_label=label,
            calling_agent_id=agent_id,
            trace_id=trace_id,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return result, trace_id


# ── module-level audit log isolation ─────────────────────────────────────────

def setup_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
        conn.commit()


def teardown_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM audit_log")
        conn.commit()


# ── Attack #25: URL strip writes audit rows ──────────────────────────────────

class TestURLStripAuditTrail:
    """
    Attack #25 (URL-based Exfiltration).

    Each stripped URL must produce an audit_log row with:
      action = 'egress_url_stripped'
      security_event = TRUE
      details.url = the stripped URL
    """

    def test_single_disallowed_url_writes_one_audit_row(self):
        trace_id = uuid.uuid4()
        bad_url = "https://attacker.io/exfil"
        result, _ = _run_filter(f"see {bad_url} for data", trace_id=trace_id)
        assert result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 1, f"Expected 1 audit row, got {len(rows)}"
        assert rows[0]["action"] == "egress_url_stripped"
        assert rows[0]["security_event"] is True
        assert rows[0]["details"]["url"] == bad_url

    def test_two_disallowed_urls_write_two_audit_rows(self):
        trace_id = uuid.uuid4()
        result, _ = _run_filter(
            "A: https://evil1.com/x B: https://evil2.com/y",
            trace_id=trace_id,
        )
        assert result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 2
        actions = {r["action"] for r in rows}
        assert actions == {"egress_url_stripped"}
        for r in rows:
            assert r["security_event"] is True

    def test_allowed_url_writes_no_audit_row(self):
        trace_id = uuid.uuid4()
        result, _ = _run_filter(
            "see https://docs.secureclaim.example/faq here",
            trace_id=trace_id,
        )
        assert result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert rows == [], "Allowed URL must not produce any audit row"

    def test_userinfo_bypass_url_stripped_and_audited(self):
        """
        Attack #25: http://docs.secureclaim.example@evil.com/exfil
        The filter must strip and audit this — userinfo trick rejected.
        """
        trace_id = uuid.uuid4()
        bad_url = "http://docs.secureclaim.example@evil.com/exfil"
        result, _ = _run_filter(f"report at {bad_url}", trace_id=trace_id)
        assert result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 1
        assert rows[0]["action"] == "egress_url_stripped"
        assert bad_url in rows[0]["details"]["url"]

    def test_ip_literal_url_stripped_and_audited(self):
        """Attack #25: IPv4 literal http://192.0.2.1/steal must be audited."""
        trace_id = uuid.uuid4()
        result, _ = _run_filter("data at http://192.0.2.1/steal now", trace_id=trace_id)
        assert result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 1
        assert rows[0]["action"] == "egress_url_stripped"
        assert rows[0]["security_event"] is True


# ── Attack #20: PII block writes audit row ───────────────────────────────────

class TestPIIBlockAuditTrail:
    """
    Attack #20 (Direct Exfiltration via PII).

    A PII block must produce exactly one audit_log row with:
      action = 'egress_blocked_pii'
      security_event = TRUE
      details.pii_types = list of matched types
    The response must be the standard refusal message.
    """

    def test_ssn_block_writes_audit_row(self):
        trace_id = uuid.uuid4()
        result, _ = _run_filter("your SSN is 123-45-6789", trace_id=trace_id)
        assert not result.ok
        assert result.output == REFUSAL_MESSAGE

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        pii_rows = [r for r in rows if r["action"] == "egress_blocked_pii"]
        assert len(pii_rows) == 1
        assert pii_rows[0]["security_event"] is True
        assert "ssn" in pii_rows[0]["details"]["pii_types"]

    def test_credit_card_block_writes_audit_row(self):
        trace_id = uuid.uuid4()
        result, _ = _run_filter("card 4242 4242 4242 4242 processed", trace_id=trace_id)
        assert not result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        pii_rows = [r for r in rows if r["action"] == "egress_blocked_pii"]
        assert pii_rows
        assert "credit_card" in pii_rows[0]["details"]["pii_types"]

    def test_phone_block_writes_audit_row(self):
        trace_id = uuid.uuid4()
        result, _ = _run_filter("call (555) 123-4567 for support", trace_id=trace_id)
        assert not result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        pii_rows = [r for r in rows if r["action"] == "egress_blocked_pii"]
        assert pii_rows
        assert "phone" in pii_rows[0]["details"]["pii_types"]

    def test_pii_past_truncation_boundary_blocked_and_audited(self):
        """
        Attack #20 invariant: PII at position MAX_OUTPUT_CHARS + 500 still
        produces an audit row and blocks the response.
        """
        trace_id = uuid.uuid4()
        text = "a" * (MAX_OUTPUT_CHARS + 500) + " SSN 123-45-6789"
        result, _ = _run_filter(text, trace_id=trace_id)
        assert not result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        pii_rows = [r for r in rows if r["action"] == "egress_blocked_pii"]
        assert pii_rows, (
            "[Attack #20] PII past truncation boundary must be audited "
            "even though truncation would have removed it from output"
        )

    def test_pii_in_allowed_url_blocked_and_audited(self):
        """
        SSN embedded in an allowed URL query string: URL not stripped (allowed),
        PII still detected → blocked + audited.
        """
        trace_id = uuid.uuid4()
        text = "see https://docs.secureclaim.example/?ssn=123-45-6789 now"
        result, _ = _run_filter(text, trace_id=trace_id)
        assert not result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        pii_rows = [r for r in rows if r["action"] == "egress_blocked_pii"]
        url_rows = [r for r in rows if r["action"] == "egress_url_stripped"]
        assert pii_rows, "PII in allowed URL must be audited"
        assert not url_rows, "Allowed URL must not generate url_stripped row"


# ── Attack #20: SECRET label kill-switch audit ───────────────────────────────

class TestSecretLabelAuditTrail:
    """
    Attack #20 — SECRET label short-circuit.

    A SECRET-labeled response must produce exactly one audit_log row:
      action = 'egress_blocked_secret'
      security_event = TRUE
    No URL-strip or PII-block rows should exist for the same trace.
    """

    def test_secret_block_writes_single_audit_row(self):
        trace_id = uuid.uuid4()
        result, _ = _run_filter("The settlement amount is $52,000.", _SECRET, trace_id=trace_id)
        assert not result.ok
        assert result.output == REFUSAL_MESSAGE

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 1
        assert rows[0]["action"] == "egress_blocked_secret"
        assert rows[0]["security_event"] is True

    def test_secret_short_circuits_url_and_pii_checks(self):
        """
        SECRET must short-circuit before URL stripping or PII detection.
        Only one audit row should exist.
        """
        trace_id = uuid.uuid4()
        text = "https://evil.com/x and SSN 123-45-6789"
        result, _ = _run_filter(text, _SECRET, trace_id=trace_id)
        assert not result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 1, (
            f"SECRET must short-circuit — expected 1 row, got {len(rows)}: "
            f"{[r['action'] for r in rows]}"
        )
        assert rows[0]["action"] == "egress_blocked_secret"


# ── Stacked violations ───────────────────────────────────────────────────────

class TestStackedViolationAuditTrail:
    """
    Tests that exercise multiple steps of the filter pipeline in a single
    request and verify the full audit trail.
    """

    def test_url_strip_then_pii_block_writes_both_audit_rows(self):
        """
        Attack #25 + #20: disallowed URL stripped (non-blocking), then SSN found
        in remaining text → PII blocks.  Both events must be in audit_log.
        """
        trace_id = uuid.uuid4()
        text = "see https://evil.com/x then SSN 123-45-6789 here"
        result, _ = _run_filter(text, trace_id=trace_id)
        assert not result.ok  # PII blocks

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        actions = [r["action"] for r in rows]
        assert "egress_url_stripped" in actions, "URL strip must be audited"
        assert "egress_blocked_pii" in actions, "PII block must be audited"
        # URL strip row must come before PII block row (filter step order)
        url_idx = next(i for i, r in enumerate(rows) if r["action"] == "egress_url_stripped")
        pii_idx = next(i for i, r in enumerate(rows) if r["action"] == "egress_blocked_pii")
        assert url_idx < pii_idx, "URL strip audit row must precede PII block row"

    def test_url_strip_then_truncation_writes_both_rows(self):
        """
        Disallowed URL stripped + clean remaining text is long → truncated.
        URL event: security_event=TRUE; truncation event: security_event=FALSE.
        """
        trace_id = uuid.uuid4()
        text = "https://evil.com/x " + "clean text. " * 200
        result, _ = _run_filter(text, trace_id=trace_id)
        assert result.ok  # neither strip nor truncation blocks

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        actions = [r["action"] for r in rows]
        assert "egress_url_stripped" in actions
        assert "egress_truncated" in actions

        url_row = next(r for r in rows if r["action"] == "egress_url_stripped")
        trunc_row = next(r for r in rows if r["action"] == "egress_truncated")
        assert url_row["security_event"] is True
        assert trunc_row["security_event"] is False

    def test_truncation_only_one_row(self):
        """Clean long text → exactly one audit row (truncation), not a security event."""
        trace_id = uuid.uuid4()
        text = "Safe response. " * 200  # no URLs, no PII
        result, _ = _run_filter(text, trace_id=trace_id)
        assert result.ok

        with _admin() as conn:
            rows = _audit_rows_for_trace(conn, trace_id)

        assert len(rows) == 1
        assert rows[0]["action"] == "egress_truncated"
        assert rows[0]["security_event"] is False


# ── Audit hash-chain integrity ───────────────────────────────────────────────

class TestAuditChainIntegrityAfterEgressEvents:
    """
    Verify that egress violation events do not break the audit hash-chain.
    Each filter_output call appends rows via append_log which chains them.
    verify_chain() must return [] (no broken links) after a series of probes.
    """

    def test_chain_intact_after_multiple_egress_events(self):
        """
        Run several filter_output calls (URL strip, PII block, SECRET block,
        truncation) and confirm verify_chain() finds no integrity failures.
        """
        for text, label in [
            ("https://evil.com/x clean text", _PUBLIC),
            ("SSN 123-45-6789 present", _PUBLIC),
            ("secret settlement data", _SECRET),
            ("safe " * 300, _PUBLIC),
        ]:
            _run_filter(text, label)

        with _admin() as conn:
            broken = verify_chain(conn)

        assert broken == [], (
            f"Audit hash-chain has broken links after egress probe events: {broken}"
        )
