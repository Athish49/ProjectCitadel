"""Signed system prompt registry (P12 — task 1.3.6).

Public API (runtime — call these at application startup):
  verify_manifest(manifest, registry)               # raises PromptIntegrityError on bad sig
  load_and_verify(prompt_dir, manifest, registry)   # raises PromptIntegrityError on any mismatch

Public API (offline / CI — never called at runtime):
  compute_prompt_hash(text)                         # SHA-256 hex of prompt text
  build_manifest(entries, key_manager)              # sign a dict of {agent_id: sha256_hex}

Serialisation helpers:
  manifest_to_dict(manifest)   # → JSON-serialisable dict
  manifest_from_dict(d)        # ← deserialise

Design:
  - The manifest covers every agent_id in entries; every listed file MUST be present in
    prompt_dir at load time.  Extra files in prompt_dir are rejected (stowaway-prompt defence).
  - The signer is always "orchestrator" (uses KNOWN_AGENTS key; production should split
    this into a separate offline build-time key never deployed to runtime hosts).
  - The signing surface is the canonical JSON of {"signer": ..., "entries": {sorted...}},
    so swapping the signer field invalidates the signature.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from agent_system.identity.keys import KeyRegistry, KeypairManager

MANIFEST_SIGNER_AGENT_ID = "orchestrator"

# Prompt files live in prompt_dir as {agent_id}.txt
_PROMPT_FILE_SUFFIX = ".txt"


class PromptIntegrityError(Exception):
    """Raised when a prompt or manifest fails integrity verification.

    Carries *reason* for structured audit logging.
    """

    def __init__(self, message: str, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class PromptManifest:
    """An Ed25519-signed record of {agent_id: sha256_hex} entries.

    *entries* maps agent_id to the hex-encoded SHA-256 of that agent's system
    prompt text (UTF-8).  *signature* is the 64-byte Ed25519 signature over
    the canonical JSON of {"signer": signer, "entries": entries}.
    """

    entries: dict[str, str]   # agent_id → sha256_hex
    signer: str               # agent_id of the signing key
    signature: bytes          # 64-byte Ed25519 signature


def compute_prompt_hash(text: str) -> str:
    """Return the hex-encoded SHA-256 of *text* (UTF-8 encoded)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _signing_bytes(signer: str, entries: dict[str, str]) -> bytes:
    """Return the canonical bytes that are signed / verified.

    Both sign and verify must use this function to prevent drift.
    Covers both *signer* and *entries* so swapping either field invalidates
    the signature.
    """
    payload = {"signer": signer, "entries": dict(sorted(entries.items()))}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_manifest(
    entries: dict[str, str],
    key_manager: KeypairManager,
) -> PromptManifest:
    """Create a signed PromptManifest.  Offline / CI only — never call at runtime.

    *entries* maps agent_id → sha256_hex (from compute_prompt_hash).
    *key_manager* must be for MANIFEST_SIGNER_AGENT_ID ("orchestrator").
    """
    if key_manager.agent_id != MANIFEST_SIGNER_AGENT_ID:
        raise ValueError(
            f"Manifest must be signed by {MANIFEST_SIGNER_AGENT_ID!r}, "
            f"got {key_manager.agent_id!r}"
        )
    sig = key_manager.sign(_signing_bytes(key_manager.agent_id, entries))
    return PromptManifest(entries=dict(entries), signer=key_manager.agent_id, signature=sig)


def verify_manifest(manifest: PromptManifest, registry: KeyRegistry) -> None:
    """Verify the Ed25519 signature on *manifest*.

    Raises PromptIntegrityError (reason="invalid_signature") if the signature
    is invalid, the signer is not registered, or any other cryptographic error.
    """
    ok = registry.verify_signature(
        manifest.signer,
        _signing_bytes(manifest.signer, manifest.entries),
        manifest.signature,
    )
    if not ok:
        raise PromptIntegrityError(
            f"Manifest signature invalid (signer={manifest.signer!r})",
            reason="invalid_signature",
        )


def load_and_verify(
    prompt_dir: Path,
    manifest: PromptManifest,
    registry: KeyRegistry,
) -> dict[str, str]:
    """Load prompt files from *prompt_dir* and verify their hashes against *manifest*.

    Steps:
      1. Verify the manifest signature.
      2. For every agent_id in manifest.entries, load {agent_id}.txt from prompt_dir
         and verify its SHA-256 matches the manifest entry.
      3. Reject any .txt files in prompt_dir that are NOT in manifest.entries (stowaway
         prompt defence).

    Returns a dict {agent_id: prompt_text} on success.
    Raises PromptIntegrityError on any failure.
    """
    verify_manifest(manifest, registry)

    # Load all .txt files present on disk
    on_disk: dict[str, Path] = {
        p.stem: p
        for p in prompt_dir.glob(f"*{_PROMPT_FILE_SUFFIX}")
        if p.is_file()
    }

    # Stowaway check: every file on disk must appear in the manifest
    stowaway = set(on_disk.keys()) - set(manifest.entries.keys())
    if stowaway:
        raise PromptIntegrityError(
            f"Prompt files not in manifest (stowaway defence): {sorted(stowaway)}",
            reason="stowaway_prompt",
        )

    # Hash check: every manifest entry must exist on disk and match
    result: dict[str, str] = {}
    for agent_id, expected_hash in sorted(manifest.entries.items()):
        if agent_id not in on_disk:
            raise PromptIntegrityError(
                f"Prompt file missing for agent {agent_id!r}",
                reason="missing_prompt_file",
            )
        text = on_disk[agent_id].read_text(encoding="utf-8")
        actual_hash = compute_prompt_hash(text)
        if actual_hash != expected_hash:
            raise PromptIntegrityError(
                f"Hash mismatch for agent {agent_id!r}: "
                f"expected={expected_hash[:16]}… actual={actual_hash[:16]}…",
                reason="hash_mismatch",
            )
        result[agent_id] = text

    return result


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def manifest_to_dict(manifest: PromptManifest) -> dict:
    """Return a JSON-serialisable representation of *manifest*."""
    return {
        "signer": manifest.signer,
        "entries": dict(sorted(manifest.entries.items())),
        "signature": manifest.signature.hex(),
    }


def manifest_from_dict(data: dict) -> PromptManifest:
    """Deserialise a manifest from the dict produced by manifest_to_dict()."""
    try:
        return PromptManifest(
            entries=dict(data["entries"]),
            signer=str(data["signer"]),
            signature=bytes.fromhex(data["signature"]),
        )
    except (KeyError, ValueError) as exc:
        raise PromptIntegrityError(
            f"Malformed manifest dict: {exc}",
            reason="malformed_manifest",
        ) from exc
