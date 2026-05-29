"""Unit tests for signed inter-agent message envelopes (task 2.2.2 — P8).

Pure unit tests — no database required.

Coverage:
  - EnvelopeDenyReason values (wire-contract stability)
  - EnvelopeVerifyResult bool behaviour and factory methods
  - SignedEnvelope model validation (agent whitelist, message_type literal, UTC coercion)
  - sign_envelope: field correctness, uniqueness, timestamp UTC, trace_id optional
  - _canonical_bytes invariant: bytes produced by sign path == bytes used in verify path
  - verify_envelope: happy path and all failure modes (SIGNATURE, EXPIRED, REPLAY)
  - ReplayStore: new/seen nonce behaviour
  - Attack simulations: #40 impersonation, #47 replay
  - Pipeline wiring: multi-hop signing round-trip without a real actor
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.unit

from agent_system.identity.envelope import (
    TIMESTAMP_WINDOW_SECONDS,
    EnvelopeDenyReason,
    EnvelopeVerifyResult,
    ReplayStore,
    SignedEnvelope,
    _canonical_bytes,
    sign_envelope,
    verify_envelope,
)
from agent_system.identity.keys import KeypairManager, KeyRegistry
from agent_system.identity.signing import verify_message


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def intake_km() -> KeypairManager:
    return KeypairManager.generate("intake_actor")


@pytest.fixture()
def orchestrator_km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def registry(intake_km: KeypairManager, orchestrator_km: KeypairManager) -> KeyRegistry:
    reg = KeyRegistry()
    reg.register("intake_actor", intake_km.public_key_bytes)
    reg.register("orchestrator", orchestrator_km.public_key_bytes)
    return reg


@pytest.fixture()
def fresh_store() -> ReplayStore:
    return ReplayStore()


@pytest.fixture()
def valid_envelope(intake_km: KeypairManager) -> SignedEnvelope:
    return sign_envelope(
        intake_km,
        target_agent="orchestrator",
        message_type="task_result",
        claim_id="CLM-001",
        payload={"outcome": "ready_for_identity"},
    )


# ---------------------------------------------------------------------------
# EnvelopeDenyReason — wire-contract stability
# ---------------------------------------------------------------------------


class TestEnvelopeDenyReasonValues:
    def test_signature_value(self):
        assert EnvelopeDenyReason.SIGNATURE.value == "DENIED_SIGNATURE"

    def test_expired_value(self):
        assert EnvelopeDenyReason.EXPIRED.value == "DENIED_EXPIRED"

    def test_replay_value(self):
        assert EnvelopeDenyReason.REPLAY.value == "DENIED_REPLAY"

    def test_all_reasons_covered(self):
        values = {r.value for r in EnvelopeDenyReason}
        assert values == {"DENIED_SIGNATURE", "DENIED_EXPIRED", "DENIED_REPLAY"}


# ---------------------------------------------------------------------------
# EnvelopeVerifyResult — bool behaviour and factory methods
# ---------------------------------------------------------------------------


class TestEnvelopeVerifyResult:
    def test_success_is_truthy(self):
        assert EnvelopeVerifyResult.success()

    def test_denied_is_falsy(self):
        assert not EnvelopeVerifyResult.denied(EnvelopeDenyReason.REPLAY)

    def test_success_has_no_deny_reason(self):
        r = EnvelopeVerifyResult.success()
        assert r.ok is True
        assert r.deny_reason is None

    def test_denied_carries_reason(self):
        r = EnvelopeVerifyResult.denied(EnvelopeDenyReason.EXPIRED)
        assert r.ok is False
        assert r.deny_reason is EnvelopeDenyReason.EXPIRED

    def test_repr_success(self):
        assert "ok=True" in repr(EnvelopeVerifyResult.success())

    def test_repr_denied(self):
        r = EnvelopeVerifyResult.denied(EnvelopeDenyReason.SIGNATURE)
        assert "SIGNATURE" in repr(r)


# ---------------------------------------------------------------------------
# SignedEnvelope model validation
# ---------------------------------------------------------------------------


class TestSignedEnvelopeModel:
    def _base_fields(self, km: KeypairManager, sig: str = "aa" * 64) -> dict:
        return {
            "message_id": uuid.uuid4(),
            "trace_id": None,
            "source_agent": km.agent_id,
            "target_agent": "orchestrator",
            "message_type": "task_result",
            "claim_id": "CLM-001",
            "payload": {},
            "timestamp": datetime.now(tz=timezone.utc),
            "signature": sig,
        }

    def test_unknown_source_agent_raises(self, intake_km):
        fields = self._base_fields(intake_km)
        fields["source_agent"] = "rogue_agent"
        with pytest.raises(Exception, match="Unknown agent"):
            SignedEnvelope(**fields)

    def test_unknown_target_agent_raises(self, intake_km):
        fields = self._base_fields(intake_km)
        fields["target_agent"] = "rogue_target"
        with pytest.raises(Exception, match="Unknown agent"):
            SignedEnvelope(**fields)

    def test_invalid_message_type_raises(self, intake_km):
        fields = self._base_fields(intake_km)
        fields["message_type"] = "invalid_type"
        with pytest.raises(Exception):
            SignedEnvelope(**fields)

    def test_all_valid_message_types_accepted(self, intake_km):
        for mt in ("task", "task_result", "event"):
            fields = self._base_fields(intake_km)
            fields["message_type"] = mt
            e = SignedEnvelope(**fields)
            assert e.message_type == mt

    def test_naive_timestamp_coerced_to_utc(self, intake_km):
        fields = self._base_fields(intake_km)
        fields["timestamp"] = datetime(2025, 6, 1, 12, 0, 0)  # naive
        e = SignedEnvelope(**fields)
        assert e.timestamp.tzinfo is not None

    def test_model_is_frozen(self, valid_envelope):
        with pytest.raises(Exception):
            valid_envelope.claim_id = "tampered"  # type: ignore[misc]

    def test_trace_id_can_be_none(self, intake_km):
        fields = self._base_fields(intake_km)
        fields["trace_id"] = None
        e = SignedEnvelope(**fields)
        assert e.trace_id is None

    def test_trace_id_can_be_uuid(self, intake_km):
        tid = uuid.uuid4()
        fields = self._base_fields(intake_km)
        fields["trace_id"] = tid
        e = SignedEnvelope(**fields)
        assert e.trace_id == tid


# ---------------------------------------------------------------------------
# sign_envelope — field correctness
# ---------------------------------------------------------------------------


class TestSignEnvelope:
    def test_returns_signed_envelope(self, intake_km):
        e = sign_envelope(
            intake_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-001",
            payload={},
        )
        assert isinstance(e, SignedEnvelope)

    def test_source_agent_set_from_km(self, intake_km):
        e = sign_envelope(
            intake_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-001",
            payload={},
        )
        assert e.source_agent == "intake_actor"

    def test_fields_match_arguments(self, intake_km):
        e = sign_envelope(
            intake_km,
            target_agent="orchestrator",
            message_type="event",
            claim_id="CLM-XYZ",
            payload={"key": "value"},
        )
        assert e.target_agent == "orchestrator"
        assert e.message_type == "event"
        assert e.claim_id == "CLM-XYZ"
        assert e.payload == {"key": "value"}

    def test_message_id_unique_per_call(self, intake_km):
        e1 = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        e2 = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        assert e1.message_id != e2.message_id

    def test_timestamp_is_utc(self, intake_km):
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        assert e.timestamp.tzinfo is not None

    def test_timestamp_is_recent(self, intake_km):
        before = datetime.now(tz=timezone.utc)
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        after = datetime.now(tz=timezone.utc)
        assert before <= e.timestamp <= after

    def test_trace_id_none_by_default(self, intake_km):
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        assert e.trace_id is None

    def test_trace_id_propagated_when_supplied(self, intake_km):
        tid = uuid.uuid4()
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={},
            trace_id=tid,
        )
        assert e.trace_id == tid

    def test_signature_is_valid_hex_64_bytes(self, intake_km):
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        sig_bytes = bytes.fromhex(e.signature)
        assert len(sig_bytes) == 64

    def test_unknown_target_agent_raises(self, intake_km):
        with pytest.raises(Exception, match="Unknown agent"):
            sign_envelope(
                intake_km, target_agent="rogue_agent",
                message_type="task_result", claim_id="CLM-001", payload={}
            )


# ---------------------------------------------------------------------------
# _canonical_bytes invariant
# ---------------------------------------------------------------------------


class TestCanonicalBytesInvariant:
    """Prove the bytes signed in sign_envelope() == bytes reconstructed in verify_envelope()."""

    def test_canonical_bytes_verify_against_signature(self, intake_km):
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        canonical = _canonical_bytes(e)
        sig_bytes = bytes.fromhex(e.signature)
        assert verify_message(intake_km.public_key_bytes, canonical, sig_bytes)

    def test_canonical_bytes_excludes_signature_field(self, valid_envelope):
        data = json.loads(_canonical_bytes(valid_envelope))
        assert "signature" not in data

    def test_canonical_bytes_includes_all_other_fields(self, valid_envelope):
        data = json.loads(_canonical_bytes(valid_envelope))
        expected = {"message_id", "trace_id", "source_agent", "target_agent",
                    "message_type", "claim_id", "payload", "timestamp"}
        assert set(data.keys()) == expected

    def test_canonical_bytes_deterministic(self, valid_envelope):
        assert _canonical_bytes(valid_envelope) == _canonical_bytes(valid_envelope)

    def test_canonical_bytes_with_nested_payload(self, intake_km):
        payload = {
            "outcome": "ready_for_identity",
            "metadata": {"score": 0.95, "flags": ["a", "b"]},
            "count": 42,
        }
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-002", payload=payload
        )
        canonical = _canonical_bytes(e)
        sig_bytes = bytes.fromhex(e.signature)
        assert verify_message(intake_km.public_key_bytes, canonical, sig_bytes)

    def test_canonical_bytes_with_trace_id(self, intake_km):
        tid = uuid.uuid4()
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-003", payload={},
            trace_id=tid,
        )
        canonical = _canonical_bytes(e)
        sig_bytes = bytes.fromhex(e.signature)
        assert verify_message(intake_km.public_key_bytes, canonical, sig_bytes)

    def test_canonical_bytes_uses_sort_keys(self, intake_km):
        payload = {"z": 1, "a": 2, "m": 3}
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-004", payload=payload
        )
        raw = _canonical_bytes(e).decode()
        # Top-level keys must be sorted
        assert raw.index('"claim_id"') < raw.index('"message_id"')
        assert raw.index('"message_id"') < raw.index('"source_agent"')


# ---------------------------------------------------------------------------
# ReplayStore
# ---------------------------------------------------------------------------


class TestReplayStore:
    def test_new_id_accepted(self, fresh_store):
        mid = uuid.uuid4()
        assert fresh_store.check_and_record(mid) is True

    def test_seen_id_rejected(self, fresh_store):
        mid = uuid.uuid4()
        fresh_store.check_and_record(mid)
        assert fresh_store.check_and_record(mid) is False

    def test_different_ids_both_accepted(self, fresh_store):
        assert fresh_store.check_and_record(uuid.uuid4()) is True
        assert fresh_store.check_and_record(uuid.uuid4()) is True

    def test_independent_stores_do_not_share_state(self):
        mid = uuid.uuid4()
        s1 = ReplayStore()
        s2 = ReplayStore()
        s1.check_and_record(mid)
        assert s2.check_and_record(mid) is True


# ---------------------------------------------------------------------------
# verify_envelope — happy path and all failure modes
# ---------------------------------------------------------------------------


class TestVerifyEnvelope:
    def test_happy_path_succeeds(self, valid_envelope, registry, fresh_store):
        result = verify_envelope(valid_envelope, registry, replay_store=fresh_store)
        assert result

    def test_result_is_truthy_on_success(self, valid_envelope, registry, fresh_store):
        result = verify_envelope(valid_envelope, registry, replay_store=fresh_store)
        assert bool(result) is True

    # Check 1: Signature
    def test_unregistered_source_agent_denied_signature(self, intake_km, fresh_store):
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        empty_registry = KeyRegistry()
        # register only orchestrator, not intake_actor
        result = verify_envelope(e, empty_registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE

    def test_tampered_signature_denied(self, valid_envelope, registry, fresh_store):
        bad = valid_envelope.model_copy(update={"signature": "bb" * 64})
        result = verify_envelope(bad, registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE

    def test_invalid_hex_signature_denied(self, valid_envelope, registry, fresh_store):
        bad = valid_envelope.model_copy(update={"signature": "not-hex!!"})
        result = verify_envelope(bad, registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE

    def test_wrong_public_key_denied(self, intake_km, fresh_store):
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        attacker_km = KeypairManager.generate("intake_actor")
        bad_registry = KeyRegistry()
        bad_registry.register("intake_actor", attacker_km.public_key_bytes)
        bad_registry.register("orchestrator", attacker_km.public_key_bytes)
        result = verify_envelope(e, bad_registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE

    # Check 2: Timestamp
    def test_expired_envelope_denied(self, intake_km, registry, fresh_store):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=TIMESTAMP_WINDOW_SECONDS + 10)
        unsigned = {
            "message_id": str(uuid.uuid4()),
            "trace_id": None,
            "source_agent": "intake_actor",
            "target_agent": "orchestrator",
            "message_type": "task_result",
            "claim_id": "CLM-001",
            "payload": {},
            "timestamp": past.isoformat(),
        }
        payload_bytes = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        sig_hex = intake_km.sign(payload_bytes).hex()
        expired = SignedEnvelope(**unsigned, signature=sig_hex)

        result = verify_envelope(expired, registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.EXPIRED

    def test_future_envelope_beyond_window_denied(self, intake_km, registry, fresh_store):
        future = datetime.now(tz=timezone.utc) + timedelta(seconds=TIMESTAMP_WINDOW_SECONDS + 10)
        unsigned = {
            "message_id": str(uuid.uuid4()),
            "trace_id": None,
            "source_agent": "intake_actor",
            "target_agent": "orchestrator",
            "message_type": "task_result",
            "claim_id": "CLM-001",
            "payload": {},
            "timestamp": future.isoformat(),
        }
        payload_bytes = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        sig_hex = intake_km.sign(payload_bytes).hex()
        future_e = SignedEnvelope(**unsigned, signature=sig_hex)

        result = verify_envelope(future_e, registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.EXPIRED

    # Check 3: Replay
    def test_second_use_of_same_envelope_denied_replay(
        self, valid_envelope, registry, fresh_store
    ):
        first = verify_envelope(valid_envelope, registry, replay_store=fresh_store)
        assert first

        second = verify_envelope(valid_envelope, registry, replay_store=fresh_store)
        assert not second
        assert second.deny_reason == EnvelopeDenyReason.REPLAY

    # Check ordering
    def test_signature_checked_before_expiry(self, intake_km, registry, fresh_store):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=TIMESTAMP_WINDOW_SECONDS + 10)
        unsigned = {
            "message_id": str(uuid.uuid4()),
            "trace_id": None,
            "source_agent": "intake_actor",
            "target_agent": "orchestrator",
            "message_type": "task_result",
            "claim_id": "CLM-001",
            "payload": {},
            "timestamp": past.isoformat(),
        }
        payload_bytes = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        sig_hex = intake_km.sign(payload_bytes).hex()
        expired = SignedEnvelope(**unsigned, signature=sig_hex)
        bad_sig = expired.model_copy(update={"signature": "cc" * 64})

        result = verify_envelope(bad_sig, registry, replay_store=fresh_store)
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE

    def test_expiry_checked_before_replay(self, intake_km, registry):
        past = datetime.now(tz=timezone.utc) - timedelta(seconds=TIMESTAMP_WINDOW_SECONDS + 10)
        unsigned = {
            "message_id": str(uuid.uuid4()),
            "trace_id": None,
            "source_agent": "intake_actor",
            "target_agent": "orchestrator",
            "message_type": "task_result",
            "claim_id": "CLM-001",
            "payload": {},
            "timestamp": past.isoformat(),
        }
        payload_bytes = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
        sig_hex = intake_km.sign(payload_bytes).hex()
        expired = SignedEnvelope(**unsigned, signature=sig_hex)

        # Record the nonce first so replay would trigger — but expiry should win
        seen_store = ReplayStore()
        seen_store.check_and_record(expired.message_id)

        result = verify_envelope(expired, registry, replay_store=seen_store)
        assert result.deny_reason == EnvelopeDenyReason.EXPIRED

    def test_uses_default_store_when_none_passed(self, intake_km, registry):
        from agent_system.identity.envelope import _DEFAULT_REPLAY_STORE
        e = sign_envelope(
            intake_km, target_agent="orchestrator",
            message_type="task_result", claim_id="CLM-001", payload={}
        )
        # First verify with explicit None — should use default store
        result = verify_envelope(e, registry, replay_store=None)
        assert result


# ---------------------------------------------------------------------------
# Attack simulations
# ---------------------------------------------------------------------------


class TestAttackSimulations:
    def test_attack_40_impersonation_attacker_with_different_keys_denied(self, fresh_store):
        """Attack #40: attacker has intake_actor's agent_id but a different keypair.

        The registry contains the real intake_actor public key. The attacker
        signs an envelope with their own private key. verify_envelope must
        return DENIED_SIGNATURE.
        """
        legitimate_km = KeypairManager.generate("intake_actor")
        attacker_km = KeypairManager.generate("intake_actor")  # different keypair, same agent_id

        registry = KeyRegistry()
        registry.register("intake_actor", legitimate_km.public_key_bytes)  # legitimate key only
        registry.register("orchestrator", KeypairManager.generate("orchestrator").public_key_bytes)

        # Attacker signs with their own private key, claiming to be intake_actor
        forged = sign_envelope(
            attacker_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-FORGED",
            payload={"outcome": "ready_for_identity"},
        )

        result = verify_envelope(forged, registry, replay_store=fresh_store)
        assert not result, "Forged envelope must be rejected"
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE

    def test_attack_47_replay_same_envelope_twice_denied(self, intake_km, registry):
        """Attack #47: attacker replays a legitimately signed envelope.

        First delivery succeeds. Second delivery of the same message_id must
        return DENIED_REPLAY.
        """
        store = ReplayStore()
        e = sign_envelope(
            intake_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-REPLAY",
            payload={"outcome": "ready_for_identity"},
        )

        first = verify_envelope(e, registry, replay_store=store)
        assert first, "Legitimate first delivery must succeed"

        replayed = verify_envelope(e, registry, replay_store=store)
        assert not replayed, "Replayed message must be rejected"
        assert replayed.deny_reason == EnvelopeDenyReason.REPLAY

    def test_attack_40_tampered_payload_invalidates_signature(self, intake_km, registry, fresh_store):
        """A man-in-the-middle modifying the payload must be caught by signature check."""
        e = sign_envelope(
            intake_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-TAMPER",
            payload={"outcome": "ready_for_identity"},
        )
        tampered = e.model_copy(update={"payload": {"outcome": "ESCALATED"}})

        result = verify_envelope(tampered, registry, replay_store=fresh_store)
        assert not result
        assert result.deny_reason == EnvelopeDenyReason.SIGNATURE


# ---------------------------------------------------------------------------
# Pipeline wiring — multi-hop signing round-trip
# ---------------------------------------------------------------------------


class TestSigningWiredInPipeline:
    """Demonstrates P8 signing at each actor handoff without a real LLM or DB.

    Each handoff is modelled as:
      sender.sign_envelope(payload) → recipient.verify_envelope → passes if valid
    """

    def _make_registry(self, *kms: KeypairManager) -> KeyRegistry:
        reg = KeyRegistry()
        for km in kms:
            reg.register(km.agent_id, km.public_key_bytes)
        return reg

    def test_intake_actor_to_orchestrator_handoff(self):
        intake_km = KeypairManager.generate("intake_actor")
        orchestrator_km = KeypairManager.generate("orchestrator")
        registry = self._make_registry(intake_km, orchestrator_km)
        store = ReplayStore()

        env = sign_envelope(
            intake_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-001",
            payload={"outcome": "ready_for_identity", "summary": "Collision claim intake done."},
        )
        result = verify_envelope(env, registry, replay_store=store)
        assert result, f"Handoff 1 failed: {result.deny_reason}"

    def test_identity_verifier_to_orchestrator_handoff(self):
        id_km = KeypairManager.generate("identity_verifier")
        orchestrator_km = KeypairManager.generate("orchestrator")
        registry = self._make_registry(id_km, orchestrator_km)
        store = ReplayStore()

        env = sign_envelope(
            id_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-001",
            payload={"outcome": "identity_verified", "policy_number": "POL-0001"},
        )
        result = verify_envelope(env, registry, replay_store=store)
        assert result, f"Handoff 2 failed: {result.deny_reason}"

    def test_claims_processor_to_orchestrator_handoff(self):
        cp_km = KeypairManager.generate("claims_processor")
        orchestrator_km = KeypairManager.generate("orchestrator")
        registry = self._make_registry(cp_km, orchestrator_km)
        store = ReplayStore()

        env = sign_envelope(
            cp_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-001",
            payload={
                "fraud_signal": "CLEAR",
                "damage_assessment": "collision_minor",
                "coverage_calculation": "full_coverage_applicable",
            },
        )
        result = verify_envelope(env, registry, replay_store=store)
        assert result, f"Handoff 3 failed: {result.deny_reason}"

    def test_settlement_actor_to_orchestrator_handoff(self):
        sa_km = KeypairManager.generate("settlement_actor")
        orchestrator_km = KeypairManager.generate("orchestrator")
        registry = self._make_registry(sa_km, orchestrator_km)
        store = ReplayStore()

        env = sign_envelope(
            sa_km,
            target_agent="orchestrator",
            message_type="task_result",
            claim_id="CLM-001",
            payload={"settlement_amount": 4500.0, "payout_status": "approved"},
        )
        result = verify_envelope(env, registry, replay_store=store)
        assert result, f"Handoff 4 failed: {result.deny_reason}"

    def test_full_pipeline_four_hop_chain_all_verified(self):
        """Simulate all four signing handoffs in sequence with trace_id propagation."""
        intake_km = KeypairManager.generate("intake_actor")
        id_km = KeypairManager.generate("identity_verifier")
        cp_km = KeypairManager.generate("claims_processor")
        sa_km = KeypairManager.generate("settlement_actor")
        orchestrator_km = KeypairManager.generate("orchestrator")

        registry = self._make_registry(intake_km, id_km, cp_km, sa_km, orchestrator_km)
        store = ReplayStore()
        trace = uuid.uuid4()

        hop1 = sign_envelope(
            intake_km, target_agent="orchestrator", message_type="task_result",
            claim_id="CLM-E2E", payload={"outcome": "ready_for_identity"}, trace_id=trace,
        )
        hop2 = sign_envelope(
            id_km, target_agent="orchestrator", message_type="task_result",
            claim_id="CLM-E2E", payload={"outcome": "identity_verified"}, trace_id=trace,
        )
        hop3 = sign_envelope(
            cp_km, target_agent="orchestrator", message_type="task_result",
            claim_id="CLM-E2E", payload={"fraud_signal": "CLEAR"}, trace_id=trace,
        )
        hop4 = sign_envelope(
            sa_km, target_agent="orchestrator", message_type="task_result",
            claim_id="CLM-E2E", payload={"settlement_amount": 4500.0}, trace_id=trace,
        )

        for i, hop in enumerate([hop1, hop2, hop3, hop4], start=1):
            r = verify_envelope(hop, registry, replay_store=store)
            assert r, f"Hop {i} failed: {r.deny_reason}"
            assert hop.trace_id == trace

    def test_distinct_message_ids_prevent_cross_hop_replay(self):
        """Each hop must have a unique message_id even with same claim_id and trace."""
        intake_km = KeypairManager.generate("intake_actor")
        id_km = KeypairManager.generate("identity_verifier")
        orchestrator_km = KeypairManager.generate("orchestrator")

        registry = self._make_registry(intake_km, id_km, orchestrator_km)
        store = ReplayStore()
        trace = uuid.uuid4()

        hop1 = sign_envelope(
            intake_km, target_agent="orchestrator", message_type="task_result",
            claim_id="CLM-E2E", payload={"hop": 1}, trace_id=trace,
        )
        hop2 = sign_envelope(
            id_km, target_agent="orchestrator", message_type="task_result",
            claim_id="CLM-E2E", payload={"hop": 2}, trace_id=trace,
        )

        assert hop1.message_id != hop2.message_id

        r1 = verify_envelope(hop1, registry, replay_store=store)
        r2 = verify_envelope(hop2, registry, replay_store=store)
        assert r1 and r2
