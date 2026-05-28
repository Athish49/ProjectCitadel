"""Unit tests for capability token issuer and verifier (task 1.2.2).

Pure unit tests — no database required.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.tools.capability_tokens import (
    CapabilityToken,
    DenyReason,
    VerifyResult,
    _canonical_payload,
    _scope_satisfied,
    issue_token,
    verify_token,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def valid_token(orchestrator_km: KeypairManager) -> CapabilityToken:
    return issue_token(
        orchestrator_km,
        agent_id="claims_processor",
        tool="approve_claim",
        scope={"claim_id": "CLM-001", "max_amount": 5000},
    )


# ---------------------------------------------------------------------------
# DenyReason — values must match DB CHECK constraint
# ---------------------------------------------------------------------------


class TestDenyReasonValues:
    def test_signature_value(self):
        assert DenyReason.SIGNATURE.value == "DENIED_SIGNATURE"

    def test_expired_value(self):
        assert DenyReason.EXPIRED.value == "DENIED_EXPIRED"

    def test_scope_value(self):
        assert DenyReason.SCOPE.value == "DENIED_SCOPE"

    def test_all_deny_reasons_covered(self):
        values = {r.value for r in DenyReason}
        assert values == {"DENIED_SIGNATURE", "DENIED_EXPIRED", "DENIED_SCOPE"}


# ---------------------------------------------------------------------------
# VerifyResult — bool behaviour and factory methods
# ---------------------------------------------------------------------------


class TestVerifyResult:
    def test_success_is_truthy(self):
        assert VerifyResult.success()

    def test_denied_is_falsy(self):
        assert not VerifyResult.denied(DenyReason.SCOPE)

    def test_success_has_no_deny_reason(self):
        r = VerifyResult.success()
        assert r.ok is True
        assert r.deny_reason is None

    def test_denied_carries_reason(self):
        r = VerifyResult.denied(DenyReason.EXPIRED)
        assert r.ok is False
        assert r.deny_reason is DenyReason.EXPIRED

    def test_repr_success(self):
        assert "ok=True" in repr(VerifyResult.success())

    def test_repr_denied(self):
        r = VerifyResult.denied(DenyReason.SIGNATURE)
        assert "SIGNATURE" in repr(r)


# ---------------------------------------------------------------------------
# issue_token — creation and field correctness
# ---------------------------------------------------------------------------


class TestIssueToken:
    def test_returns_capability_token(self, orchestrator_km):
        token = issue_token(
            orchestrator_km,
            agent_id="intake_actor",
            tool="submit_claim",
            scope={"policy_id": "POL-42"},
        )
        assert isinstance(token, CapabilityToken)

    def test_issued_by_is_orchestrator(self, orchestrator_km):
        token = issue_token(
            orchestrator_km, agent_id="intake_actor", tool="submit_claim", scope={}
        )
        assert token.issued_by == "orchestrator"

    def test_fields_match_arguments(self, orchestrator_km):
        scope = {"claim_id": "CLM-007"}
        token = issue_token(
            orchestrator_km, agent_id="identity_verifier", tool="verify_id", scope=scope
        )
        assert token.agent_id == "identity_verifier"
        assert token.tool == "verify_id"
        assert token.scope == scope

    def test_token_id_is_unique(self, orchestrator_km):
        t1 = issue_token(orchestrator_km, agent_id="intake_actor", tool="t", scope={})
        t2 = issue_token(orchestrator_km, agent_id="intake_actor", tool="t", scope={})
        assert t1.token_id != t2.token_id

    def test_expires_after_ttl(self, orchestrator_km):
        ttl = 120
        token = issue_token(
            orchestrator_km, agent_id="intake_actor", tool="t", scope={}, ttl_seconds=ttl
        )
        delta = (token.expires_at - token.issued_at).total_seconds()
        assert abs(delta - ttl) < 1

    def test_timestamps_are_utc(self, orchestrator_km):
        token = issue_token(orchestrator_km, agent_id="intake_actor", tool="t", scope={})
        assert token.issued_at.tzinfo == timezone.utc
        assert token.expires_at.tzinfo == timezone.utc

    def test_signature_is_nonempty_hex_string(self, orchestrator_km):
        token = issue_token(orchestrator_km, agent_id="intake_actor", tool="t", scope={})
        # Must be valid hex
        sig_bytes = bytes.fromhex(token.signature)
        assert len(sig_bytes) == 64

    def test_unknown_agent_raises(self, orchestrator_km):
        with pytest.raises(ValueError, match="Unknown agent_id"):
            issue_token(orchestrator_km, agent_id="rogue_agent", tool="t", scope={})

    def test_token_is_frozen(self, valid_token):
        with pytest.raises(Exception):
            valid_token.tool = "tampered_tool"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# _canonical_payload — determinism and sign/verify alignment
# ---------------------------------------------------------------------------


class TestCanonicalPayload:
    def test_is_bytes(self, valid_token):
        assert isinstance(_canonical_payload(valid_token), bytes)

    def test_deterministic(self, valid_token):
        assert _canonical_payload(valid_token) == _canonical_payload(valid_token)

    def test_excludes_signature(self, valid_token):
        payload = _canonical_payload(valid_token)
        data = json.loads(payload)
        assert "signature" not in data

    def test_includes_all_other_fields(self, valid_token):
        payload = _canonical_payload(valid_token)
        data = json.loads(payload)
        expected_keys = {"token_id", "issued_by", "agent_id", "tool", "scope", "issued_at", "expires_at"}
        assert set(data.keys()) == expected_keys

    def test_payload_matches_sign_path(self, orchestrator_km):
        """Canonical payload from model must match what issue_token signed."""
        token = issue_token(
            orchestrator_km, agent_id="claims_processor", tool="approve_claim", scope={}
        )
        from agent_system.identity.signing import verify_message
        payload = _canonical_payload(token)
        sig_bytes = bytes.fromhex(token.signature)
        assert verify_message(orchestrator_km.public_key_bytes, payload, sig_bytes)

    def test_scope_is_sorted_keys(self, orchestrator_km):
        scope = {"z_key": 1, "a_key": 2}
        token = issue_token(
            orchestrator_km, agent_id="intake_actor", tool="t", scope=scope
        )
        payload_str = _canonical_payload(token).decode()
        # Verify the JSON uses sort_keys by checking key order in the raw string
        assert payload_str.index('"a_key"') < payload_str.index('"z_key"')


# ---------------------------------------------------------------------------
# verify_token — all six checks
# ---------------------------------------------------------------------------


class TestVerifyToken:
    def _call(self, token, orchestrator_km, *, agent_id=None, tool=None, params=None):
        return verify_token(
            token,
            calling_agent_id=agent_id or token.agent_id,
            tool=tool or token.tool,
            params=params if params is not None else dict(token.scope),
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )

    def test_valid_token_succeeds(self, valid_token, orchestrator_km):
        result = self._call(valid_token, orchestrator_km)
        assert result

    # Check 1 — issued_by
    def test_wrong_issuer_denied_signature(self, valid_token, orchestrator_km):
        bad = valid_token.model_copy(update={"issued_by": "rogue"})
        result = self._call(bad, orchestrator_km)
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE

    # Check 2 — signature
    def test_tampered_signature_denied(self, valid_token, orchestrator_km):
        bad_sig = "aa" * 64
        bad = valid_token.model_copy(update={"signature": bad_sig})
        result = self._call(bad, orchestrator_km)
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_invalid_hex_signature_denied(self, valid_token, orchestrator_km):
        bad = valid_token.model_copy(update={"signature": "not-hex!!"})
        result = self._call(bad, orchestrator_km)
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_wrong_public_key_denied(self, valid_token):
        attacker_km = KeypairManager.generate("orchestrator")
        result = verify_token(
            valid_token,
            calling_agent_id=valid_token.agent_id,
            tool=valid_token.tool,
            params=dict(valid_token.scope),
            orchestrator_public_key=attacker_km.public_key_bytes,
        )
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE

    # Check 3 — expiry
    def test_expired_token_denied(self, orchestrator_km):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        expired = issue_token(
            orchestrator_km, agent_id="intake_actor", tool="t", scope={}, ttl_seconds=-1
        )
        # Re-issue with a past expires_at by monkey-patching through model_copy
        # Actually issue_token with ttl_seconds=-1 sets expires_at in the past
        result = verify_token(
            expired,
            calling_agent_id=expired.agent_id,
            tool=expired.tool,
            params={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert not result
        assert result.deny_reason == DenyReason.EXPIRED

    # Check 4 — agent identity
    def test_wrong_agent_denied_scope(self, valid_token, orchestrator_km):
        result = self._call(valid_token, orchestrator_km, agent_id="settlement_actor")
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    # Check 5 — tool name
    def test_wrong_tool_denied_scope(self, valid_token, orchestrator_km):
        result = self._call(valid_token, orchestrator_km, tool="other_tool")
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    # Check 6 — scope
    def test_missing_scope_param_denied(self, valid_token, orchestrator_km):
        result = self._call(valid_token, orchestrator_km, params={"claim_id": "CLM-001"})
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_wrong_scope_value_denied(self, valid_token, orchestrator_km):
        params = dict(valid_token.scope)
        params["claim_id"] = "CLM-999"
        result = self._call(valid_token, orchestrator_km, params=params)
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_extra_params_allowed(self, valid_token, orchestrator_km):
        params = dict(valid_token.scope)
        params["extra_key"] = "extra_value"
        result = self._call(valid_token, orchestrator_km, params=params)
        assert result

    def test_empty_scope_always_satisfied(self, orchestrator_km):
        token = issue_token(
            orchestrator_km, agent_id="intake_actor", tool="read_policy", scope={}
        )
        result = verify_token(
            token,
            calling_agent_id="intake_actor",
            tool="read_policy",
            params={"irrelevant": "data"},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert result

    # Check ordering — signature fails before expiry
    def test_signature_checked_before_expiry(self, orchestrator_km):
        expired = issue_token(
            orchestrator_km, agent_id="intake_actor", tool="t", scope={}, ttl_seconds=-1
        )
        bad = expired.model_copy(update={"signature": "aa" * 64})
        result = verify_token(
            bad,
            calling_agent_id=bad.agent_id,
            tool=bad.tool,
            params={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert result.deny_reason == DenyReason.SIGNATURE


# ---------------------------------------------------------------------------
# _scope_satisfied — edge cases
# ---------------------------------------------------------------------------


class TestScopeSatisfied:
    def test_exact_match(self):
        assert _scope_satisfied({"k": "v"}, {"k": "v"})

    def test_missing_key_fails(self):
        assert not _scope_satisfied({"k": "v"}, {})

    def test_wrong_value_fails(self):
        assert not _scope_satisfied({"k": "v"}, {"k": "w"})

    def test_extra_params_ignored(self):
        assert _scope_satisfied({"k": "v"}, {"k": "v", "extra": "x"})

    def test_empty_scope_always_true(self):
        assert _scope_satisfied({}, {})
        assert _scope_satisfied({}, {"any": "param"})

    def test_integer_string_equivalence(self):
        # json.dumps normalisation: int 100 and string "100" are NOT equal
        # because json.dumps(100) == "100" but json.dumps("100") == '"100"'
        assert not _scope_satisfied({"amount": 100}, {"amount": "100"})

    def test_uuid_object_vs_string(self):
        uid = uuid.uuid4()
        # json.dumps(uuid) raises TypeError, so compare as strings
        assert _scope_satisfied({"id": str(uid)}, {"id": str(uid)})

    def test_none_value_in_params(self):
        assert not _scope_satisfied({"k": "v"}, {"k": None})

    def test_nested_dict_scope(self):
        scope = {"filter": {"status": "pending"}}
        assert _scope_satisfied(scope, {"filter": {"status": "pending"}})
        assert not _scope_satisfied(scope, {"filter": {"status": "approved"}})

    def test_list_value_scope(self):
        scope = {"ids": [1, 2, 3]}
        assert _scope_satisfied(scope, {"ids": [1, 2, 3]})
        assert not _scope_satisfied(scope, {"ids": [1, 2]})
