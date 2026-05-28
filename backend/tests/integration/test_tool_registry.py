"""Integration tests for ToolRegistry with live DB (task 1.2.3).

Verifies:
  - Successful invocation: capability_token_log.use_result='OK', audit_log row present.
  - Bad scope → denied + capability_token_log.use_result='DENIED_SCOPE' + audit_log row.
  - Replay → second invoke denied + audit_log security_event=True.
  - Bad signature → denied + audit_log security_event=True.
  - Handler error → token consumed, audit_log action='tool_call_handler_error'.
  - role_orchestrator can invoke (DB-role grant check).

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
from agent_system.tools.implementations.sample_tools import approve_claim, score_fraud
from agent_system.tools.registry import ToolRegistry

pytestmark = pytest.mark.integration

ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN",
    "postgresql://postgres:postgres@localhost:5432/secureclaim",
)
ORCHESTRATOR_DSN = os.environ.get(
    "TEST_ORCHESTRATOR_DSN",
    "postgresql://role_orchestrator:role_orchestrator@localhost:5432/secureclaim",
)


def _admin() -> psycopg.Connection:
    return psycopg.connect(ADMIN_DSN, autocommit=False)


def _orchestrator() -> psycopg.Connection:
    return psycopg.connect(ORCHESTRATOR_DSN, autocommit=False)


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


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def registry(orchestrator_km) -> ToolRegistry:
    r = ToolRegistry()
    r.register("approve_claim", approve_claim)
    r.register("score_fraud", score_fraud)
    return r


def _issue_and_persist(orchestrator_km, *, agent_id, tool, scope):
    """Issue a token and write it to capability_token_log. Returns the token."""
    token = issue_token(orchestrator_km, agent_id=agent_id, tool=tool, scope=scope)
    with _admin() as conn:
        persist_issuance(conn, token)
        conn.commit()
    return token


def _fetch_token_row(token_id):
    with _admin() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM capability_token_log WHERE token_id = %s",
                (token_id,),
            )
            return cur.fetchone()


def _fetch_audit_rows(token_id_str):
    with _admin() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM audit_log WHERE details->>'token_id' = %s ORDER BY log_id",
                (token_id_str,),
            )
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Successful invocation
# ---------------------------------------------------------------------------


class TestSuccessfulInvocation:
    def test_ok_result_returned(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-INT-010", "amount": 3000},
        )
        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-INT-010", "amount": 3000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert result
        assert result.value["status"] == "approved"

    def test_capability_token_log_use_result_ok(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-INT-011", "amount": 2000},
        )
        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-INT-011", "amount": 2000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(token.token_id)
        assert row["use_result"] == "OK"
        assert row["used_at"] is not None

    def test_audit_log_row_written(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-INT-012", "amount": 1500},
        )
        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-INT-012", "amount": 1500},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        rows = _fetch_audit_rows(str(token.token_id))
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_ok"
        assert rows[0]["log_id"] == result.log_id


# ---------------------------------------------------------------------------
# Bad scope → denied + audited  (primary acceptance criterion per roadmap)
# ---------------------------------------------------------------------------


class TestBadScopeDenied:
    def test_wrong_claim_id_denied(self, registry, orchestrator_km):
        """Core showcase: token scoped to CLM-A, invoked with CLM-B → DENIED_SCOPE."""
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SCOPE-A", "amount": 5000},
        )
        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SCOPE-B", "amount": 5000},  # wrong claim
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_capability_token_log_records_denied_scope(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SCOPE-C", "amount": 5000},
        )
        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SCOPE-D", "amount": 5000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(token.token_id)
        assert row["use_result"] == "DENIED_SCOPE"

    def test_audit_log_row_written_for_denial(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SCOPE-E", "amount": 5000},
        )
        trace = uuid.uuid4()
        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SCOPE-F", "amount": 5000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                trace_id=trace,
            )
            conn.commit()

        rows = _fetch_audit_rows(str(token.token_id))
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_denied"
        assert rows[0]["log_id"] == result.log_id
        assert rows[0]["security_event"] is False

    def test_wrong_amount_in_scope_denied(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SCOPE-G", "amount": 5000},
        )
        with _admin() as conn:
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SCOPE-G", "amount": 9999},  # widened amount
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_handler_not_called_on_scope_denial(self, registry, orchestrator_km):
        """Handler must not execute when scope is wrong."""
        called = []

        def tracking_handler(**kwargs):
            called.append(kwargs)
            return {}

        registry.register("approve_claim", tracking_handler)

        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SCOPE-H", "amount": 5000},
        )
        with _admin() as conn:
            registry.invoke(
                conn,
                token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SCOPE-X", "amount": 5000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert called == [], "Handler must not be called when scope check fails"


# ---------------------------------------------------------------------------
# Replay prevention
# ---------------------------------------------------------------------------


class TestReplayPrevention:
    def test_second_invoke_denied_scope(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-REPLAY-1", "amount": 1000},
        )
        params = {"claim_id": "CLM-REPLAY-1", "amount": 1000}

        with _admin() as conn:
            first = registry.invoke(
                conn, token=token, calling_agent_id="claims_processor",
                tool_name="approve_claim", params=params,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        with _admin() as conn:
            second = registry.invoke(
                conn, token=token, calling_agent_id="claims_processor",
                tool_name="approve_claim", params=params,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert first
        assert not second
        assert second.deny_reason == DenyReason.SCOPE

    def test_replay_audit_row_is_security_event(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-REPLAY-2", "amount": 1000},
        )
        params = {"claim_id": "CLM-REPLAY-2", "amount": 1000}

        with _admin() as conn:
            registry.invoke(
                conn, token=token, calling_agent_id="claims_processor",
                tool_name="approve_claim", params=params,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        with _admin() as conn:
            registry.invoke(
                conn, token=token, calling_agent_id="claims_processor",
                tool_name="approve_claim", params=params,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        rows = _fetch_audit_rows(str(token.token_id))
        assert len(rows) == 2
        ok_row = next(r for r in rows if r["action"] == "tool_call_ok")
        replay_row = next(r for r in rows if r["action"] == "tool_call_replay_denied")
        assert ok_row["security_event"] is False
        assert replay_row["security_event"] is True


# ---------------------------------------------------------------------------
# Bad signature
# ---------------------------------------------------------------------------


class TestBadSignature:
    def test_forged_signature_denied(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SIG-1", "amount": 500},
        )
        forged = token.model_copy(update={"signature": "cc" * 64})

        with _admin() as conn:
            result = registry.invoke(
                conn, token=forged,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SIG-1", "amount": 500},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_signature_denial_is_security_event(self, registry, orchestrator_km):
        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SIG-2", "amount": 500},
        )
        forged = token.model_copy(update={"signature": "dd" * 64})

        with _admin() as conn:
            registry.invoke(
                conn, token=forged,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-SIG-2", "amount": 500},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        rows = _fetch_audit_rows(str(token.token_id))
        assert len(rows) == 1
        assert rows[0]["security_event"] is True


# ---------------------------------------------------------------------------
# Handler error
# ---------------------------------------------------------------------------


class TestHandlerError:
    def test_handler_exception_returns_error_result(self, orchestrator_km):
        def failing_tool(**kwargs):
            raise RuntimeError("downstream failure")

        reg = ToolRegistry()
        reg.register("failing_tool", failing_tool)

        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="failing_tool",
            scope={"claim_id": "CLM-ERR-1"},
        )
        with _admin() as conn:
            result = reg.invoke(
                conn, token=token,
                calling_agent_id="claims_processor",
                tool_name="failing_tool",
                params={"claim_id": "CLM-ERR-1"},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert not result
        assert isinstance(result.handler_error, RuntimeError)

    def test_token_consumed_on_handler_error(self, orchestrator_km):
        def failing_tool(**kwargs):
            raise RuntimeError("fail")

        reg = ToolRegistry()
        reg.register("failing_tool", failing_tool)

        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="failing_tool",
            scope={"claim_id": "CLM-ERR-2"},
        )
        with _admin() as conn:
            reg.invoke(
                conn, token=token,
                calling_agent_id="claims_processor",
                tool_name="failing_tool",
                params={"claim_id": "CLM-ERR-2"},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        row = _fetch_token_row(token.token_id)
        assert row["use_result"] == "OK"  # gate passed; error is in handler
        assert row["used_at"] is not None

    def test_handler_error_audit_row_action(self, orchestrator_km):
        def failing_tool(**kwargs):
            raise ValueError("bad input")

        reg = ToolRegistry()
        reg.register("failing_tool", failing_tool)

        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="failing_tool",
            scope={"claim_id": "CLM-ERR-3"},
        )
        with _admin() as conn:
            reg.invoke(
                conn, token=token,
                calling_agent_id="claims_processor",
                tool_name="failing_tool",
                params={"claim_id": "CLM-ERR-3"},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        rows = _fetch_audit_rows(str(token.token_id))
        assert len(rows) == 1
        assert rows[0]["action"] == "tool_call_handler_error"
        assert rows[0]["security_event"] is False


# ---------------------------------------------------------------------------
# DB role access
# ---------------------------------------------------------------------------


class TestRoleAccess:
    def test_orchestrator_role_can_invoke(self, orchestrator_km):
        """role_orchestrator has SELECT/INSERT/UPDATE on capability_token_log
        and INSERT on audit_log (via role_audit_writer). Full invoke must work."""
        reg = ToolRegistry()
        reg.register("approve_claim", approve_claim)

        token = _issue_and_persist(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-ROLE-1", "amount": 250},
        )
        with _orchestrator() as conn:
            result = reg.invoke(
                conn, token=token,
                calling_agent_id="claims_processor",
                tool_name="approve_claim",
                params={"claim_id": "CLM-ROLE-1", "amount": 250},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )
            conn.commit()

        assert result
