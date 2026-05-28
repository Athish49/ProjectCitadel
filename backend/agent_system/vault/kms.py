"""KMS-mock key provider for the PII vault (task 1.2.7).

In production, replace these env-var reads with calls to a real KMS
(AWS KMS, GCP Cloud KMS, etc.).  For development and CI the env vars
fall back to deterministic dev-only values — never use dev defaults in
production.

Environment variables
---------------------
SECURECLAIM_PII_PEPPER       — hex-encoded 32-byte pepper for Argon2id
SECURECLAIM_FIELD_KEY_<NAME> — hex-encoded 32-byte AES-256 key, where
                               <NAME> is DRIVERS_LICENSE, BANK_ROUTING,
                               or BANK_ACCOUNT (upper-cased field name)
SECURECLAIM_ARGON2_FAST      — set to "1" to use ARGON_TEST params
                               (unit-test speed; not for production)
"""
from __future__ import annotations

import os

from agent_system.vault.crypto import ARGON_PROD, ARGON_TEST, ArgonParams

# ── Dev-only sentinel values ─────────────────────────────────────────────────
# 32 zero bytes — obviously weak; caught by any secrets scanner in CI.
_DEV_PEPPER: bytes = bytes(32)
_DEV_FIELD_KEY: bytes = bytes(32)

_SUPPORTED_FIELDS = frozenset(
    {"drivers_license", "bank_routing", "bank_account"}
)


def get_pepper() -> bytes:
    """Return the deployment pepper for Argon2id SSN hashing."""
    raw = os.environ.get("SECURECLAIM_PII_PEPPER")
    if raw:
        return bytes.fromhex(raw)
    return _DEV_PEPPER


def get_field_key(field_name: str) -> bytes:
    """Return the AES-256 key for *field_name*."""
    if field_name not in _SUPPORTED_FIELDS:
        raise ValueError(f"Unknown vault field: {field_name!r}")
    env_var = f"SECURECLAIM_FIELD_KEY_{field_name.upper()}"
    raw = os.environ.get(env_var)
    if raw:
        return bytes.fromhex(raw)
    return _DEV_FIELD_KEY


def get_argon_params() -> ArgonParams:
    """Return Argon2id parameter profile for this environment."""
    if os.environ.get("SECURECLAIM_ARGON2_FAST") == "1":
        return ARGON_TEST
    return ARGON_PROD
