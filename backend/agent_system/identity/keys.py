"""Ed25519 keypair manager and public-key registry (P8 — task 1.2.1).

Design notes:
- Each agent has one keypair.  Private key is agent-local; public key is
  registered so other agents can verify signatures.
- `KeypairManager` owns a single agent's keypair (generate in-memory or
  persist to / load from disk).
- `KeyRegistry` is the shared public-key lookup used for verification.
- Agent IDs are validated against KNOWN_AGENTS (static registry, matches
  Doc 04 #45 — no runtime agent registration allowed).

Production wiring TODO: resolve `keys_dir` from env / Docker named volume
at FastAPI startup (compose time) and call `load_or_generate` for the
current agent; register the resulting public key into the shared registry
before accepting traffic.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent_system.identity.signing import (
    private_key_to_bytes,
    public_key_to_bytes,
    sign_message,
    verify_message,
)

KNOWN_AGENTS: frozenset[str] = frozenset(
    [
        "orchestrator",
        "intake_parser",
        "intake_actor",
        "identity_verifier",
        "document_parser",
        "claims_processor",
        "settlement_actor",
    ]
)


class KeypairManager:
    """Holds an Ed25519 keypair for a single agent.

    Use `generate()` for ephemeral keys (tests, adversarial agent sandbox).
    Use `load_or_generate(agent_id, keys_dir)` for persistent keys (production).
    """

    def __init__(
        self,
        agent_id: str,
        private_key_bytes: bytes,
        public_key_bytes: bytes,
    ) -> None:
        if agent_id not in KNOWN_AGENTS:
            raise ValueError(
                f"Unknown agent_id '{agent_id}'. "
                f"Valid agents: {sorted(KNOWN_AGENTS)}"
            )
        self.agent_id = agent_id
        self._private_key_bytes = private_key_bytes
        self.public_key_bytes = public_key_bytes

    @classmethod
    def generate(cls, agent_id: str) -> "KeypairManager":
        """Generate a fresh ephemeral keypair (not persisted to disk)."""
        private_key = Ed25519PrivateKey.generate()
        priv_bytes = private_key_to_bytes(private_key)
        pub_bytes = public_key_to_bytes(private_key.public_key())
        return cls(agent_id, priv_bytes, pub_bytes)

    @classmethod
    def load_or_generate(cls, agent_id: str, keys_dir: Path) -> "KeypairManager":
        """Load keypair from *keys_dir* if present, otherwise generate and persist.

        Private key file is written with mode 0o600 (owner read/write only).
        Public key file is written with mode 0o644.
        """
        if agent_id not in KNOWN_AGENTS:
            raise ValueError(
                f"Unknown agent_id '{agent_id}'. "
                f"Valid agents: {sorted(KNOWN_AGENTS)}"
            )

        priv_path = keys_dir / f"{agent_id}.priv"
        pub_path = keys_dir / f"{agent_id}.pub"

        if priv_path.exists() and pub_path.exists():
            private_bytes = priv_path.read_bytes()
            public_bytes = pub_path.read_bytes()
            return cls(agent_id, private_bytes, public_bytes)

        manager = cls.generate(agent_id)
        keys_dir.mkdir(parents=True, exist_ok=True)

        # Private key: owner read/write only (0o600).
        fd = os.open(priv_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, manager._private_key_bytes)
        finally:
            os.close(fd)

        pub_path.write_bytes(manager.public_key_bytes)
        pub_path.chmod(0o644)

        return manager

    def sign(self, message: bytes) -> bytes:
        """Return the 64-byte Ed25519 signature over *message*."""
        return sign_message(self._private_key_bytes, message)


class KeyRegistry:
    """Maps agent_id → public_key_bytes.  Used to verify inter-agent signatures.

    The registry is intentionally read-only after construction so callers
    cannot swap keys at runtime (mirrors the static-agent-registry invariant).
    Registration is done at startup via `register()`, then the registry is
    used read-only for the lifetime of the process.
    """

    def __init__(self) -> None:
        self._registry: dict[str, bytes] = {}

    def register(self, agent_id: str, public_key_bytes: bytes) -> None:
        """Register the public key for *agent_id*.

        Raises ValueError if the agent_id is not in KNOWN_AGENTS, or if a
        different key is already registered (prevents silent key rotation).
        """
        if agent_id not in KNOWN_AGENTS:
            raise ValueError(
                f"Unknown agent_id '{agent_id}'. "
                f"Valid agents: {sorted(KNOWN_AGENTS)}"
            )
        if agent_id in self._registry and self._registry[agent_id] != public_key_bytes:
            raise ValueError(
                f"Public key for '{agent_id}' already registered with a different value. "
                "Key rotation is not allowed at runtime."
            )
        self._registry[agent_id] = public_key_bytes

    def get_public_key(self, agent_id: str) -> bytes:
        """Return the 32-byte public key for *agent_id*.

        Raises KeyError if not registered.
        """
        if agent_id not in self._registry:
            raise KeyError(f"No public key registered for agent '{agent_id}'")
        return self._registry[agent_id]

    def verify_signature(
        self, agent_id: str, message: bytes, signature: bytes
    ) -> bool:
        """Verify that *message* was signed by *agent_id*.

        Returns False (not raises) for unknown agents, bad signatures, or
        any other error — fail-closed but non-exceptional for callers.
        """
        try:
            pub_key = self.get_public_key(agent_id)
        except KeyError:
            return False
        return verify_message(pub_key, message, signature)

    @classmethod
    def from_file(cls, registry_path: Path) -> "KeyRegistry":
        """Load a JSON registry file (agent_id → hex-encoded public key)."""
        data: dict[str, str] = json.loads(registry_path.read_text())
        registry = cls()
        for agent_id, hex_key in data.items():
            registry.register(agent_id, bytes.fromhex(hex_key))
        return registry

    def save(self, registry_path: Path) -> None:
        """Persist the registry to *registry_path* as JSON."""
        data = {
            agent_id: pub_key.hex() for agent_id, pub_key in self._registry.items()
        }
        registry_path.write_text(json.dumps(data, indent=2, sort_keys=True))
