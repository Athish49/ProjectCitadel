"""
Sprint 5.1.6 — Capability-Token Bypass Adversarial Probe Suite (Unit Layer)
============================================================================

Adversarial probes targeting the P4 capability-token enforcement layer.

Attack IDs covered:
  - Attack #4  (Token/Credential Forgery): self-signed tokens, signature transplant
  - Attack #29 (Tool Misuse): scope widening, cross-agent token reuse, field tampering

These tests are COMPLEMENTARY to test_capability_tokens.py (which covers the
six verify_token checks, _scope_satisfied edge cases, and basic tamper cases).
They target adversarial *attack scenarios* that the basic tests don't frame.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from agent_system.identity.keys import KNOWN_AGENTS, KeypairManager
from agent_system.tools.capability_tokens import (
    CapabilityToken,
    DenyReason,
    _canonical_payload,
    _scope_satisfied,
    issue_token,
    verify_token,
)

pytestmark = pytest.mark.unit

# ── shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture(scope="module")
def attacker_km() -> KeypairManager:
    """Separate keypair representing an attacker's self-generated orchestrator key."""
    return KeypairManager.generate("orchestrator")


def _verify(token: CapabilityToken, km: KeypairManager, **overrides) -> object:
    return verify_token(
        token,
        calling_agent_id=overrides.get("agent_id", token.agent_id),
        tool=overrides.get("tool", token.tool),
        params=overrides.get("params", dict(token.scope)),
        orchestrator_public_key=overrides.get("pubkey", km.public_key_bytes),
    )


# ── Attack #4: self-signed token forgery ─────────────────────────────────────

class TestSelfSignedForgery:
    """
    Attack #4 (Token/Credential Forgery).

    An attacker generates their own Ed25519 keypair, labels it "orchestrator",
    and issues a token to themselves.  The token has a valid signature — but
    only against the attacker's key, not the real orchestrator's key.

    verify_token must reject it when given the real orchestrator's public key.
    This is distinct from "tampered signature" probes: here the signature is
    cryptographically valid against a different key, not random garbage.
    """

    def test_self_signed_token_rejected(self, orchestrator_km, attacker_km):
        """
        Attacker self-signs a token with their own keypair and presents it.
        Verification against the real orchestrator pubkey → DENIED_SIGNATURE.
        """
        self_token = issue_token(
            attacker_km,  # attacker's keypair, NOT the real orchestrator's
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-SELF-001"},
        )
        result = verify_token(
            self_token,
            calling_agent_id="claims_processor",
            tool="approve_claim",
            params={"claim_id": "CLM-SELF-001"},
            orchestrator_public_key=orchestrator_km.public_key_bytes,  # real pubkey
        )
        assert not result, "[Attack #4] Self-signed token passed real-pubkey verification"
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_self_signed_token_verifies_against_own_key(self, attacker_km):
        """Sanity: self-signed token IS valid against the attacker's own key."""
        self_token = issue_token(
            attacker_km,
            agent_id="intake_actor",
            tool="submit_claim",
            scope={},
        )
        result = verify_token(
            self_token,
            calling_agent_id="intake_actor",
            tool="submit_claim",
            params={},
            orchestrator_public_key=attacker_km.public_key_bytes,  # attacker's key
        )
        assert result, "Self-signed token must verify against its own key (sanity check)"

    def test_real_token_rejected_by_attacker_pubkey(self, orchestrator_km, attacker_km):
        """
        Inverse: a legitimately-issued token must not verify against the attacker's
        public key — proving the two keypairs are independent.
        """
        real_token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={},
        )
        result = verify_token(
            real_token,
            calling_agent_id="claims_processor",
            tool="approve_claim",
            params={},
            orchestrator_public_key=attacker_km.public_key_bytes,  # wrong pubkey
        )
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE


# ── Attack #4: signature transplant ──────────────────────────────────────────

class TestSignatureTransplant:
    """
    Attack #4 (Token Forgery via Signature Reuse).

    An attacker holds a legitimately-issued token A and wants to use its
    valid signature to authorize a different (tampered) token B.  Because
    the canonical payload includes all fields, any change to B's fields
    makes B's payload differ from A's — the transplanted signature is invalid.
    """

    def test_signature_from_token_a_rejected_on_tampered_tool(self, orchestrator_km):
        """
        Token A issued for tool 'approve_claim'; attacker copies sig to
        token B with tool 'request_payout'.  Sig is invalid for B's payload.
        """
        token_a = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TRANS-001"},
        )
        # Token B has the same token_id, agent, scope — but different tool.
        # Signature from A is transplanted unchanged.
        token_b = token_a.model_copy(update={"tool": "request_payout"})
        assert token_b.signature == token_a.signature  # transplanted

        result = verify_token(
            token_b,
            calling_agent_id="claims_processor",
            tool="request_payout",
            params={"claim_id": "CLM-TRANS-001"},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert not result, "[Attack #4] Transplanted signature accepted on tampered tool"
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_signature_from_token_a_rejected_on_widened_scope(self, orchestrator_km):
        """
        Token A scoped to claim_id='CLM-A'; attacker transplants sig to token B
        with scope={} (no constraints).  Any change to scope changes the payload.
        """
        token_a = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TRANS-002"},
        )
        token_b = token_a.model_copy(update={"scope": {}})

        result = verify_token(
            token_b,
            calling_agent_id="claims_processor",
            tool="approve_claim",
            params={"extra": "param"},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert not result, "[Attack #4] Transplanted signature accepted on widened scope"
        assert result.deny_reason == DenyReason.SIGNATURE


# ── Attack #29: field tamper with original signature ─────────────────────────

class TestFieldTamperKeepsSig:
    """
    Attack #29 (Tool Misuse via Token Manipulation).

    An LLM or adversary tampers with high-value token fields to escalate
    privileges while keeping the original signature.  All variants produce
    DENIED_SIGNATURE because the canonical payload changes.

    Tests focus on the three most security-relevant mutations:
      - scope widened to no constraints
      - expires_at extended to far future (replay after expiry)
      - tool escalated to a more powerful tool
    """

    def test_tamper_scope_to_wildcard_denied(self, orchestrator_km):
        """Scope replaced with {} (no constraints) + original sig → SIGNATURE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TAMPER-001", "amount": 5000},
        )
        widened = token.model_copy(update={"scope": {}})

        result = _verify(widened, orchestrator_km, params={})
        assert not result, "[Attack #29] Scope-widened tampered token accepted"
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_tamper_expires_at_to_future_denied(self, orchestrator_km):
        """expires_at extended 10 years + original sig → SIGNATURE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-TAMPER-002"},
        )
        extended = token.model_copy(
            update={"expires_at": datetime.now(tz=timezone.utc) + timedelta(days=3650)}
        )
        result = _verify(extended, orchestrator_km)
        assert not result, "[Attack #29] Future-dated tampered token accepted"
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_tamper_tool_to_escalated_tool_denied(self, orchestrator_km):
        """tool changed to a higher-privilege tool + original sig → SIGNATURE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="classify_damage",
            scope={},
        )
        escalated = token.model_copy(update={"tool": "request_payout"})

        result = verify_token(
            escalated,
            calling_agent_id="claims_processor",
            tool="request_payout",
            params={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert not result, "[Attack #29] Tool-escalated tampered token accepted"
        assert result.deny_reason == DenyReason.SIGNATURE


# ── Attack #29: scope widening via parameter manipulation ────────────────────

class TestScopeWideningProbes:
    """
    Attack #29 (Tool Misuse via Scope Bypass).

    An LLM prompted adversarially may try to call a scoped tool with parameter
    values designed to widen or bypass the scope constraint.

    These probes verify that no common bypass trick defeats _scope_satisfied.
    """

    def test_wildcard_string_does_not_bypass_scope(self, orchestrator_km):
        """claim_id='*' — scope comparison is exact; '*' ≠ 'CLM-001' → SCOPE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-WILD-001"},
        )
        result = _verify(token, orchestrator_km, params={"claim_id": "*"})
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_empty_string_does_not_bypass_scope(self, orchestrator_km):
        """claim_id='' → exact comparison; '' ≠ 'CLM-001' → SCOPE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-WILD-002"},
        )
        result = _verify(token, orchestrator_km, params={"claim_id": ""})
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_omitting_scoped_param_denied(self, orchestrator_km):
        """Calling with no params when scope is non-empty → SCOPE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-WILD-003", "amount": 1000},
        )
        result = _verify(token, orchestrator_km, params={})
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_amount_escalation_denied(self, orchestrator_km):
        """Token scoped to amount=5000, call with amount=50000 → SCOPE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-WILD-004", "amount": 5000},
        )
        result = _verify(
            token, orchestrator_km,
            params={"claim_id": "CLM-WILD-004", "amount": 50000},
        )
        assert not result
        assert result.deny_reason == DenyReason.SCOPE

    def test_extra_params_do_not_widen_scope(self, orchestrator_km):
        """
        Extra params beyond the scope constraints are allowed.
        This is a POSITIVE CONTROL — extra params cannot widen scope because
        scope only checks that all scope keys are constrained, not vice versa.
        """
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={"claim_id": "CLM-WILD-005"},
        )
        result = _verify(
            token, orchestrator_km,
            params={"claim_id": "CLM-WILD-005", "admin_override": True},
        )
        assert result, (
            "Extra params must not cause denial — scope checks constraints only. "
            "If this assertion fails, the scope check regressed."
        )


# ── Attack #29: cross-agent token reuse ──────────────────────────────────────

class TestCrossAgentTokenReuse:
    """
    Attack #29 (Tool Misuse via Cross-Agent Token Reuse).

    A compromised or adversarially-prompted agent attempts to reuse a token
    issued to a different agent.  The agent_id check must deny all of these.
    """

    @pytest.mark.parametrize("issuer_agent,caller_agent", [
        ("intake_actor",     "claims_processor"),
        ("claims_processor", "settlement_actor"),
        ("settlement_actor", "identity_verifier"),
        ("identity_verifier","intake_actor"),
    ])
    def test_cross_agent_token_denied(self, orchestrator_km, issuer_agent, caller_agent):
        """Token issued for issuer_agent cannot be used by caller_agent."""
        token = issue_token(
            orchestrator_km,
            agent_id=issuer_agent,
            tool="some_tool",
            scope={},
        )
        result = verify_token(
            token,
            calling_agent_id=caller_agent,
            tool="some_tool",
            params={},
            orchestrator_public_key=orchestrator_km.public_key_bytes,
        )
        assert not result, (
            f"[Attack #29] Token for {issuer_agent} accepted when called by {caller_agent}"
        )
        assert result.deny_reason == DenyReason.SCOPE


# ── Attack #4: empty/malformed signature handling ────────────────────────────

class TestMalformedSignatureProbes:
    """
    Attack #4 (Token Forgery via Signature Manipulation).

    Edge cases in signature byte handling that could produce unexpected behavior.
    """

    def test_empty_signature_hex_denied(self, orchestrator_km):
        """
        "" (empty hex string) → bytes.fromhex("") = b"" → 0 bytes → fails
        verify_message's length check in cryptography library → SIGNATURE.
        """
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={},
        )
        malformed = token.model_copy(update={"signature": ""})
        result = _verify(malformed, orchestrator_km)
        assert not result, "Empty signature must be rejected"
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_truncated_signature_hex_denied(self, orchestrator_km):
        """32-byte (64 hex char) signature instead of 64-byte (128 hex char) → SIGNATURE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={},
        )
        truncated = token.model_copy(update={"signature": "ab" * 32})  # 32 bytes, not 64
        result = _verify(truncated, orchestrator_km)
        assert not result, "Truncated signature must be rejected"
        assert result.deny_reason == DenyReason.SIGNATURE

    def test_non_hex_signature_denied(self, orchestrator_km):
        """Non-hex signature string → ValueError in bytes.fromhex → SIGNATURE."""
        token = issue_token(
            orchestrator_km,
            agent_id="claims_processor",
            tool="approve_claim",
            scope={},
        )
        malformed = token.model_copy(update={"signature": "not-valid-hex!!!"})
        result = _verify(malformed, orchestrator_km)
        assert not result
        assert result.deny_reason == DenyReason.SIGNATURE
