"""
Sprint 5.1.6 — Capability-Token Bypass Adversarial Probe Suite (Integration Layer)
====================================================================================

DB-backed probes that run token attacks *through the ToolRegistry* and verify
that the correct rows land in capability_token_log and audit_log.

Attack IDs covered:
  - Attack #4  (Token/Credential Forgery): unissued token path, tampered-field
                                           with valid token_id in DB
  - Attack #29 (Tool Misuse): cross-agent reuse via registry, expired-token replay

These tests are COMPLEMENTARY to test_tool_registry.py (which covers the
normal success/denial/replay/handler-error flow with explicit DB assertions).
They target adversarial *attack scenarios* at the registry boundary.

Enforcement notes (see registry.py):
  - Step 2 (verify_token) fires BEFORE the SELECT FOR UPDATE.
  - After a Step-2 denial, _try_record_use() attempts to update the row in
    capability_token_log; it silently swallows ValueError on missing rows.
  - SIGNATURE denials → security_event=True in audit_log.
  - SCOPE / EXPIRED denials → security_event=False in audit_log.
  - Unissued token (no row in DB) → cause="unissued_token", security_event=True.

Prerequisites: `make up && make migrate` must have run successfully.
"""
from __future__ import annotations

import os
import uuid

import psycopg
import pytest
from psycopg.rows import dict_row

from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import (
    DenyReason,
    issue_token,
    persist_issuance,
)
from agent_system.tools.implementations.sample_tools import approve_claim
from agent_system.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def _fetch_token_row(token_id: uuid.UUID) -> dict | None:
    with _admin() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM capability_token_log WHERE token_id = %s",
                (token_id,),
            )
            return cur.fetchone()


def _fetch_audit_rows_for_token(token_id: uuid.UUID) -> list[dict]:
    with _admin() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM audit_log WHERE details->>'token_id' = %s ORDER BY log_id",
                (str(token_id),),
            )
            return cur.fetchall()


def _fetch_audit_rows_for_trace(trace_id: uuid.UUID) -> list[dict]:
    with _admin() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM audit_log WHERE trace_id = %s ORDER BY log_id",
                (trace_id,),
            )
            return cur.fetchall()


def _issue_and_persist(km: KeypairManager, *, agent_id, tool, scope, **kwargs):
    token = issue_token(km, agent_id=agent_id, tool=tool, scope=scope, **kwargs)
    with _admin() as conn:
        persist_issuance(conn, token)
        conn.commit()
    return token


def _make_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("approve_claim", approve_claim)
    return r


# ── module-level isolation ────────────────────────────────────────────────────

def setup_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_token_log")
            cur.execute("DELETE FROM audit_log")
        conn.commit()


def teardown_module(_):
    with _admin() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM capability_token_log")
            cur.execute("DELETE FROM audit_log")
        conn.commit()


# ── Attack #4: unissued token (no row in DB) ─────────────────────────────────

class TestUnissuedTokenRegistryPath:
    """
    Attack #4 (Token Forgery).

    A token with a valid signature (against the real orchestrator key) is
    presented to the registry WITHOUT having been persisted via persist_issuance.
    The SELECT FOR UPDATE at Step 3 finds no row → cause="unissued_token",
    security_event=True, action="tool_call_denied".

    This is distinct from bad-signature probes: the signature is cryptographically
    valid, but the token was never issued through the proper issuance channel.
    """

    def test_unissued_token_denied_at_registry(self):
        """Token signed by the real orchestrator but never persisted → denied."""
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()

        # issue_token builds and signs — but we do NOT call persist_issuance
        token = issue_token(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-UNISSUED-001", "amount": 1000},
        )

        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-UNISSUED-001", "amount": 1000},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        assert not result, "[Attack #4] Unissued token passed registry check"
        assert result.deny_reason == DenyReason.SCOPE

    def test_unissued_token_writes_security_event(self):
        """Unissued token audit row must have security_event=True and cause='unissued_token'."""
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()
        trace_id = uuid.uuid4()

        token = issue_token(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-UNISSUED-002", "amount": 1000},
        )

        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-UNISSUED-002", "amount": 1000},
                orchestrator_public_key=km.public_key_bytes,
                trace_id=trace_id,
            )
            conn.commit()

        rows = _fetch_audit_rows_for_trace(trace_id)
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_denied"
        assert rows[0]["security_event"] is True
        assert rows[0]["details"]["cause"] == "unissued_token"

    def test_unissued_token_no_capability_token_log_row(self):
        """
        No capability_token_log row should be created for an unissued token.
        _try_record_use() silently swallows the ValueError on missing rows.
        """
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()

        token = issue_token(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-UNISSUED-003"},
        )

        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-UNISSUED-003"},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(token.token_id)
        assert row is None, (
            "[Attack #4] Unissued token must not create a capability_token_log row"
        )


# ── Attack #29: cross-agent token reuse through ToolRegistry ─────────────────

class TestCrossAgentRegistryProbe:
    """
    Attack #29 (Tool Misuse via Cross-Agent Token Reuse).

    A token issued for agent A is presented by agent B at the ToolRegistry layer.
    verify_token() fails at the agent_id check → DENIED_SCOPE.
    The token row (issued for A) gets use_result='DENIED_SCOPE' written to it
    via _try_record_use(), and the audit_log gets action='tool_call_denied'.
    """

    def test_cross_agent_reuse_denied_by_registry(self):
        """Token issued for claims_processor, presented by settlement_actor → denied."""
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()

        token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-CROSS-001", "amount": 3000},
        )

        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="settlement_actor",  # wrong agent
                tool_name="approve_claim",
                params={"claim_id": "CLM-CROSS-001", "amount": 3000},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        assert not result, "[Attack #29] Cross-agent token passed registry check"
        assert result.deny_reason == DenyReason.SCOPE

    def test_cross_agent_use_result_written_to_token_log(self):
        """
        _try_record_use() finds the persisted row and writes DENIED_SCOPE
        to capability_token_log.use_result.
        """
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()

        token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-CROSS-002", "amount": 2000},
        )

        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="intake_actor",  # wrong agent
                tool_name="approve_claim",
                params={"claim_id": "CLM-CROSS-002", "amount": 2000},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(token.token_id)
        assert row is not None
        assert row["use_result"] == "DENIED_SCOPE"

    def test_cross_agent_audit_not_a_security_event(self):
        """
        Cross-agent scope denial is NOT a security_event (only SIGNATURE is).
        """
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()
        trace_id = uuid.uuid4()

        token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-CROSS-003"},
        )

        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="settlement_actor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-CROSS-003"},
                orchestrator_public_key=km.public_key_bytes,
                trace_id=trace_id,
            )
            conn.commit()

        rows = _fetch_audit_rows_for_trace(trace_id)
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_denied"
        assert rows[0]["security_event"] is False, (
            "Cross-agent scope denial must not be a security event"
        )


# ── Attack #4: expired token through ToolRegistry ────────────────────────────

class TestExpiredTokenRegistryProbe:
    """
    Attack #4 / #29 (Token replay after expiry).

    An expired token is legitimately persisted (it was issued by the orchestrator
    with a very short TTL) then presented to the registry after it has expired.
    verify_token() fails at the expiry check → DENIED_EXPIRED.
    _try_record_use() writes DENIED_EXPIRED to capability_token_log.use_result.
    """

    def test_expired_token_denied_by_registry(self):
        """Token with ttl_seconds=-1 (already expired) → DENIED_EXPIRED at registry."""
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()

        token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-EXPIRED-001", "amount": 500},
            ttl_seconds=-1,  # immediately expired
        )

        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-EXPIRED-001", "amount": 500},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        assert not result, "[Attack #4] Expired token passed registry check"
        assert result.deny_reason == DenyReason.EXPIRED

    def test_expired_token_use_result_written(self):
        """capability_token_log.use_result must be 'DENIED_EXPIRED' for an expired token."""
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()

        token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-EXPIRED-002"},
            ttl_seconds=-1,
        )

        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-EXPIRED-002"},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(token.token_id)
        assert row is not None
        assert row["use_result"] == "DENIED_EXPIRED"

    def test_expired_token_audit_action_is_denied(self):
        """Expired token produces action='tool_call_denied' with security_event=False."""
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()
        trace_id = uuid.uuid4()

        token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-EXPIRED-003"},
            ttl_seconds=-1,
        )

        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-EXPIRED-003"},
                orchestrator_public_key=km.public_key_bytes,
                trace_id=trace_id,
            )
            conn.commit()

        rows = _fetch_audit_rows_for_trace(trace_id)
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_denied"
        assert rows[0]["security_event"] is False


# ── Attack #4: tampered field with real token_id in DB ───────────────────────

class TestTamperedFieldThroughRegistry:
    """
    Attack #4 (Token Forgery via Field Tampering).

    The real token is persisted (its token_id lives in capability_token_log).
    The attacker then tampers with a field (tool, scope, or expires_at) while
    keeping the token_id the same.  verify_token() fails at signature check
    because the canonical payload changed → DENIED_SIGNATURE.

    Because the token_id IS in the DB, _try_record_use() finds the row and
    writes use_result='DENIED_SIGNATURE'.  The audit_log row has security_event=True
    (only SIGNATURE denials are security events).
    """

    def test_tampered_tool_denied_with_security_event(self):
        """
        token.tool changed from 'approve_claim' to 'score_fraud'; token_id
        present in DB → SIGNATURE denial, security_event=True.
        """
        km = KeypairManager.generate("orchestrator")
        registry = ToolRegistry()
        registry.register("score_fraud", lambda **kw: {"risk": 0})
        trace_id = uuid.uuid4()

        real_token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TAMPER-001"},
        )
        tampered = real_token.model_copy(update={"tool": "score_fraud"})

        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=tampered,
                calling_agent_id="claims_processor",
                tool_name="score_fraud",
                params={"claim_id": "CLM-TAMPER-001"},
                orchestrator_public_key=km.public_key_bytes,
                trace_id=trace_id,
            )
            conn.commit()

        assert not result, "[Attack #4] Tampered-tool token passed registry check"
        assert result.deny_reason == DenyReason.SIGNATURE

        rows = _fetch_audit_rows_for_trace(trace_id)
        assert len(rows) == 1
        assert rows[0]["security_event"] is True

    def test_tampered_tool_use_result_written_to_db(self):
        """
        token_id IS in DB → _try_record_use() updates the row with
        use_result='DENIED_SIGNATURE'.
        """
        km = KeypairManager.generate("orchestrator")
        registry = ToolRegistry()
        registry.register("score_fraud", lambda **kw: {"risk": 0})

        real_token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TAMPER-002"},
        )
        tampered = real_token.model_copy(update={"tool": "score_fraud"})

        with _admin() as conn:
            registry.invoke(
                conn,
                token=tampered,
                calling_agent_id="claims_processor",
                tool_name="score_fraud",
                params={"claim_id": "CLM-TAMPER-002"},
                orchestrator_public_key=km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(real_token.token_id)
        assert row is not None
        assert row["use_result"] == "DENIED_SIGNATURE"

    def test_scope_widening_tamper_denied_as_security_event(self):
        """
        Scope widened (→ {}) with original sig; token_id in DB.
        Same result: DENIED_SIGNATURE, security_event=True.
        """
        km = KeypairManager.generate("orchestrator")
        registry = _make_registry()
        trace_id = uuid.uuid4()

        real_token = _issue_and_persist(
            km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TAMPER-003", "amount": 5000},
        )
        tampered = real_token.model_copy(update={"scope": {}})

        with _admin() as conn:
            registry.invoke(
                conn,
                token=tampered,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"extra": "anything"},
                orchestrator_public_key=km.public_key_bytes,
                trace_id=trace_id,
            )
            conn.commit()

        rows = _fetch_audit_rows_for_trace(trace_id)
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_denied"
        assert rows[0]["security_event"] is True

        row = _fetch_token_row(real_token.token_id)
        assert row["use_result"] == "DENIED_SIGNATURE"
