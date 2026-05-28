"""Unit tests for ToolRegistry (task 1.2.3).

All DB interactions are stubbed — only the pure logic paths are exercised here.
Integration tests cover the real DB paths (persist, replay, audit row).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import (
    DenyReason,
    VerifyResult,
    issue_token,
)
from agent_system.tools.implementations.sample_tools import approve_claim, score_fraud
from agent_system.tools.registry import InvokeResult, ToolRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("approve_claim", approve_claim)
    r.register("score_fraud", score_fraud)
    return r


@pytest.fixture()
def valid_token(orchestrator_km):
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="approve_claim",
        scope={"claim_id": "CLM-001", "amount": 4000},
    )


def _make_conn(used_at=None, row_exists=True):
    """Build a minimal psycopg Connection mock for unit tests.

    The mock's cursor context manager returns a cursor whose fetchone() result
    can be configured per test.
    """
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    # fetchone() for SELECT used_at ... FOR UPDATE
    cur.fetchone.return_value = (used_at,) if row_exists else None
    conn.cursor.return_value = cur
    return conn


# ---------------------------------------------------------------------------
# InvokeResult
# ---------------------------------------------------------------------------


class TestInvokeResult:
    def test_success_is_truthy(self):
        r = InvokeResult.success(value={"x": 1}, log_id=42)
        assert r
        assert r.value == {"x": 1}
        assert r.log_id == 42
        assert r.deny_reason is None

    def test_denied_is_falsy(self):
        r = InvokeResult.denied(DenyReason.SCOPE, log_id=1)
        assert not r
        assert r.deny_reason == DenyReason.SCOPE

    def test_error_is_falsy(self):
        exc = RuntimeError("boom")
        r = InvokeResult.error(exc, log_id=5)
        assert not r
        assert r.handler_error is exc
        assert r.deny_reason is None


# ---------------------------------------------------------------------------
# Sample tools
# ---------------------------------------------------------------------------


class TestSampleTools:
    def test_approve_claim_returns_dict(self):
        result = approve_claim(claim_id="CLM-001", amount=4000)
        assert result["claim_id"] == "CLM-001"
        assert result["amount"] == 4000
        assert result["status"] == "approved"

    def test_score_fraud_returns_clear(self):
        result = score_fraud(claim_id="CLM-001")
        assert result["claim_id"] == "CLM-001"
        assert "fraud_score" in result
        assert result["decision"] == "CLEAR"


# ---------------------------------------------------------------------------
# ToolRegistry — pure logic via mocked DB
# ---------------------------------------------------------------------------


class TestToolRegistryUnit:
    """Use patch to short-circuit all DB calls so we test routing logic only."""

    def _invoke(
        self,
        registry,
        token,
        orchestrator_km,
        *,
        tool_name="approve_claim",
        params=None,
        used_at=None,
        row_exists=True,
        agent_id=None,
    ):
        """Run registry.invoke() with a fully mocked DB layer."""
        if params is None:
            params = {"claim_id": "CLM-001", "amount": 4000}
        conn = _make_conn(used_at=used_at, row_exists=row_exists)
        with (
            patch("agent_system.tools.registry.append_log", return_value=99) as mock_log,
            patch("agent_system.tools.registry.record_use") as mock_record,
            patch("agent_system.tools.registry._try_record_use") as mock_try,
        ):
            result = registry.invoke(
                conn,
                token=token,
                calling_agent_id=agent_id or token.agent_id,
                tool_name=tool_name,
                params=params,
                orchestrator_public_key=orchestrator_km.public_key_bytes,
                trace_id=uuid.uuid4(),
            )
        return result, mock_log, mock_record, mock_try

    def test_valid_invocation_succeeds(self, registry, valid_token, orchestrator_km):
        result, mock_log, mock_record, _ = self._invoke(
            registry, valid_token, orchestrator_km
        )
        assert result
        assert result.value == {"claim_id": "CLM-001", "amount": 4000, "status": "approved"}
        mock_record.assert_called_once()
        mock_log.assert_called_once()
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["action"] == "tool_call_ok"

    def test_unknown_tool_denied_scope(self, registry, valid_token, orchestrator_km):
        result, mock_log, mock_record, _ = self._invoke(
            registry, valid_token, orchestrator_km, tool_name="nonexistent_tool"
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE
        mock_record.assert_not_called()
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["action"] == "tool_call_denied"
        assert log_kwargs["security_event"] is False

    def test_wrong_agent_denied_scope(self, registry, valid_token, orchestrator_km):
        result, mock_log, mock_record, mock_try = self._invoke(
            registry, valid_token, orchestrator_km, agent_id="settlement_actor"
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE
        # record_use best-effort attempted for legitimately issued token
        mock_try.assert_called_once()

    def test_wrong_tool_in_token_denied_scope(self, registry, orchestrator_km):
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="score_fraud",  # token is for score_fraud
            scope={"claim_id": "CLM-001"},
        )
        result, _, _, _ = self._invoke(
            registry, token, orchestrator_km,
            tool_name="approve_claim",  # but call asks for approve_claim
            params={"claim_id": "CLM-001"},
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_scope_mismatch_denied_scope(self, registry, orchestrator_km):
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-001", "amount": 4000},
        )
        result, _, _, _ = self._invoke(
            registry, token, orchestrator_km,
            params={"claim_id": "CLM-999", "amount": 4000},  # wrong claim_id
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_expired_token_denied_expired(self, registry, orchestrator_km):
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-001", "amount": 4000},
            ttl_seconds=-1,
        )
        result, mock_log, _, _ = self._invoke(
            registry, token, orchestrator_km
        )
        assert not result
        assert result.deny_reason == DenyReason.EXPIRED
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["security_event"] is False  # expiry is not a security event

    def test_bad_signature_denied_signature_is_security_event(self, registry, orchestrator_km):
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-001", "amount": 4000},
        )
        forged = token.model_copy(update={"signature": "ab" * 64})
        result, mock_log, _, _ = self._invoke(registry, forged, orchestrator_km)
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["security_event"] is True

    def test_replay_denied_scope_is_security_event(self, registry, valid_token, orchestrator_km):
        # Simulate token already used: used_at is not None
        from datetime import datetime, timezone
        result, mock_log, mock_record, _ = self._invoke(
            registry, valid_token, orchestrator_km,
            used_at=datetime.now(tz=timezone.utc),
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE
        mock_record.assert_not_called()
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["security_event"] is True
        assert log_kwargs["action"] == "tool_call_replay_denied"

    def test_unissued_token_denied_is_security_event(self, registry, valid_token, orchestrator_km):
        result, mock_log, mock_record, _ = self._invoke(
            registry, valid_token, orchestrator_km, row_exists=False
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE
        mock_record.assert_not_called()
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["security_event"] is True

    def test_handler_error_returns_error_result(self, registry, valid_token, orchestrator_km):
        def boom(**kwargs):
            raise ValueError("handler failure")

        registry.register("approve_claim", boom)
        result, mock_log, mock_record, _ = self._invoke(
            registry, valid_token, orchestrator_km
        )
        assert not result
        assert result.handler_error is not None
        assert isinstance(result.handler_error, ValueError)
        mock_record.assert_called_once()  # token is consumed even on handler error
        log_kwargs = mock_log.call_args.kwargs
        assert log_kwargs["action"] == "tool_call_handler_error"
        assert log_kwargs["security_event"] is False

    def test_audit_details_exclude_raw_params(self, registry, valid_token, orchestrator_km):
        """params_keys in audit — not raw values."""
        result, mock_log, _, _ = self._invoke(
            registry, valid_token, orchestrator_km
        )
        details = mock_log.call_args.kwargs["details"]
        assert "params_keys" in details
        # Values like claim_id and amount should NOT appear as top-level keys
        assert "claim_id" not in details
        assert "amount" not in details

    def test_register_overwrites_existing_handler(self, registry, orchestrator_km):
        called = []

        def handler_v1(**kwargs):
            called.append("v1")
            return {}

        def handler_v2(**kwargs):
            called.append("v2")
            return {}

        registry.register("approve_claim", handler_v1)
        registry.register("approve_claim", handler_v2)

        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-001", "amount": 4000},
        )
        conn = _make_conn()
        with (
            patch("agent_system.tools.registry.append_log", return_value=1),
            patch("agent_system.tools.registry.record_use"),
        ):
            registry.invoke(
                conn,
                token=token,
                calling_agent_id=token.agent_id,
                tool_name="approve_claim",
                params={"claim_id": "CLM-001", "amount": 4000},
                orchestrator_public_key=orchestrator_km.public_key_bytes,
            )

        assert called == ["v2"]
