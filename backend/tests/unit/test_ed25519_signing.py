"""Unit tests for Ed25519 keypair manager and signing helpers (task 1.2.1)."""
from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from agent_system.identity.keys import KNOWN_AGENTS, KeypairManager, KeyRegistry
from agent_system.identity.signing import sign_message, verify_message


# ---------------------------------------------------------------------------
# sign_message / verify_message — low-level stateless helpers
# ---------------------------------------------------------------------------


class TestSignVerify:
    def test_roundtrip(self):
        km = KeypairManager.generate("orchestrator")
        msg = b"capability_token_payload"
        sig = km.sign(msg)
        assert verify_message(km.public_key_bytes, msg, sig)

    def test_tampered_message_fails(self):
        km = KeypairManager.generate("orchestrator")
        msg = b"original message"
        sig = km.sign(msg)
        assert not verify_message(km.public_key_bytes, b"tampered message", sig)

    def test_wrong_key_fails(self):
        km1 = KeypairManager.generate("orchestrator")
        km2 = KeypairManager.generate("intake_actor")
        msg = b"some message"
        sig = km1.sign(msg)
        assert not verify_message(km2.public_key_bytes, msg, sig)

    def test_truncated_signature_fails(self):
        km = KeypairManager.generate("orchestrator")
        msg = b"test"
        sig = km.sign(msg)
        assert not verify_message(km.public_key_bytes, msg, sig[:32])

    def test_empty_message(self):
        km = KeypairManager.generate("claims_processor")
        sig = km.sign(b"")
        assert verify_message(km.public_key_bytes, b"", sig)

    def test_signature_is_64_bytes(self):
        km = KeypairManager.generate("settlement_actor")
        sig = km.sign(b"payload")
        assert len(sig) == 64

    def test_stateless_sign_verify(self):
        km = KeypairManager.generate("identity_verifier")
        msg = b"direct function call test"
        sig = sign_message(km._private_key_bytes, msg)
        assert verify_message(km.public_key_bytes, msg, sig)


# ---------------------------------------------------------------------------
# KeypairManager — generation and persistence
# ---------------------------------------------------------------------------


class TestKeypairManager:
    def test_generate_produces_32_byte_keys(self):
        km = KeypairManager.generate("orchestrator")
        assert len(km.public_key_bytes) == 32
        assert len(km._private_key_bytes) == 32

    def test_two_generates_differ(self):
        km1 = KeypairManager.generate("orchestrator")
        km2 = KeypairManager.generate("orchestrator")
        assert km1.public_key_bytes != km2.public_key_bytes

    def test_unknown_agent_id_rejected(self):
        with pytest.raises(ValueError, match="Unknown agent_id"):
            KeypairManager.generate("rogue_agent")

    def test_load_or_generate_creates_files(self, tmp_path: Path):
        km = KeypairManager.load_or_generate("orchestrator", tmp_path)
        assert (tmp_path / "orchestrator.priv").exists()
        assert (tmp_path / "orchestrator.pub").exists()

    def test_private_key_file_permissions(self, tmp_path: Path):
        KeypairManager.load_or_generate("orchestrator", tmp_path)
        priv_path = tmp_path / "orchestrator.priv"
        file_mode = stat.S_IMODE(priv_path.stat().st_mode)
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

    def test_load_or_generate_idempotent(self, tmp_path: Path):
        km1 = KeypairManager.load_or_generate("claims_processor", tmp_path)
        km2 = KeypairManager.load_or_generate("claims_processor", tmp_path)
        assert km1.public_key_bytes == km2.public_key_bytes
        assert km1._private_key_bytes == km2._private_key_bytes

    def test_loaded_keys_produce_valid_signatures(self, tmp_path: Path):
        km = KeypairManager.load_or_generate("settlement_actor", tmp_path)
        msg = b"post-reload signing test"
        sig = km.sign(msg)
        assert verify_message(km.public_key_bytes, msg, sig)

    def test_load_or_generate_unknown_agent_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Unknown agent_id"):
            KeypairManager.load_or_generate("rogue_agent", tmp_path)


# ---------------------------------------------------------------------------
# KeyRegistry — public-key lookup and signature verification
# ---------------------------------------------------------------------------


class TestKeyRegistry:
    def test_register_and_get(self):
        km = KeypairManager.generate("orchestrator")
        registry = KeyRegistry()
        registry.register("orchestrator", km.public_key_bytes)
        assert registry.get_public_key("orchestrator") == km.public_key_bytes

    def test_get_unregistered_raises(self):
        registry = KeyRegistry()
        with pytest.raises(KeyError):
            registry.get_public_key("orchestrator")

    def test_register_unknown_agent_rejected(self):
        registry = KeyRegistry()
        with pytest.raises(ValueError, match="Unknown agent_id"):
            registry.register("rogue_agent", b"\x00" * 32)

    def test_register_same_key_twice_is_idempotent(self):
        km = KeypairManager.generate("orchestrator")
        registry = KeyRegistry()
        registry.register("orchestrator", km.public_key_bytes)
        registry.register("orchestrator", km.public_key_bytes)  # no error

    def test_register_different_key_raises(self):
        km1 = KeypairManager.generate("orchestrator")
        km2 = KeypairManager.generate("orchestrator")
        registry = KeyRegistry()
        registry.register("orchestrator", km1.public_key_bytes)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("orchestrator", km2.public_key_bytes)

    def test_verify_signature_correct_agent(self):
        km = KeypairManager.generate("intake_actor")
        registry = KeyRegistry()
        registry.register("intake_actor", km.public_key_bytes)
        msg = b"message from intake_actor"
        sig = km.sign(msg)
        assert registry.verify_signature("intake_actor", msg, sig)

    def test_verify_signature_wrong_agent(self):
        km1 = KeypairManager.generate("intake_actor")
        km2 = KeypairManager.generate("claims_processor")
        registry = KeyRegistry()
        registry.register("intake_actor", km1.public_key_bytes)
        registry.register("claims_processor", km2.public_key_bytes)
        msg = b"message"
        sig = km1.sign(msg)
        assert not registry.verify_signature("claims_processor", msg, sig)

    def test_verify_signature_unregistered_agent(self):
        registry = KeyRegistry()
        assert not registry.verify_signature("orchestrator", b"msg", b"\x00" * 64)

    def test_save_and_load_registry(self, tmp_path: Path):
        managers = {
            agent_id: KeypairManager.generate(agent_id)
            for agent_id in ["orchestrator", "intake_actor", "claims_processor"]
        }
        registry = KeyRegistry()
        for agent_id, km in managers.items():
            registry.register(agent_id, km.public_key_bytes)

        reg_path = tmp_path / "public_registry.json"
        registry.save(reg_path)

        loaded = KeyRegistry.from_file(reg_path)
        for agent_id, km in managers.items():
            assert loaded.get_public_key(agent_id) == km.public_key_bytes

    def test_registry_file_is_valid_json(self, tmp_path: Path):
        km = KeypairManager.generate("orchestrator")
        registry = KeyRegistry()
        registry.register("orchestrator", km.public_key_bytes)
        reg_path = tmp_path / "registry.json"
        registry.save(reg_path)
        data = json.loads(reg_path.read_text())
        assert "orchestrator" in data
        assert len(data["orchestrator"]) == 64  # 32 bytes hex-encoded

    def test_all_known_agents_can_be_registered(self):
        registry = KeyRegistry()
        for agent_id in KNOWN_AGENTS:
            km = KeypairManager.generate(agent_id)
            registry.register(agent_id, km.public_key_bytes)
        assert len(registry._registry) == len(KNOWN_AGENTS)
