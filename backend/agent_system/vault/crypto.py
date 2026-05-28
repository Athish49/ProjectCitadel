"""Low-level cryptographic primitives for the PII vault (task 1.2.7).

Two families:
  • Argon2id — for secrets that must be hashed (SSN, security answer).
    Stored format: salt (SALT_LENGTH bytes) || hash (hash_length bytes).
  • AES-256-GCM — for fields that must be decryptable (drivers_licence,
    bank account/routing).

All functions are pure — no I/O.

Argon2id parameters
-------------------
Production:  ARGON_PROD  (memory=64 MB, iterations=3, lanes=4)
Testing:     ARGON_TEST  (memory=8 KiB, iterations=1, lanes=1)

Pass ARGON_TEST to hash_secret / verify_secret in unit tests to keep
the suite fast (~100 ms/call for PROD vs <1 ms for TEST).
"""
from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

SALT_LENGTH = 16   # bytes
HASH_LENGTH = 32   # bytes
IV_LENGTH = 12     # bytes (96-bit nonce for GCM)


@dataclass(frozen=True)
class ArgonParams:
    memory_cost: int  # KiB
    iterations: int
    lanes: int
    hash_length: int = HASH_LENGTH
    salt_length: int = SALT_LENGTH


ARGON_PROD = ArgonParams(memory_cost=65536, iterations=3, lanes=4)
# Deliberately weak — only for unit tests.
ARGON_TEST = ArgonParams(memory_cost=8, iterations=1, lanes=1)


def hash_secret(
    plaintext: str,
    pepper: bytes,
    params: ArgonParams = ARGON_PROD,
) -> bytes:
    """Argon2id-hash *plaintext* with *pepper*.

    Returns salt || hash  (params.salt_length + params.hash_length bytes).
    """
    salt = os.urandom(params.salt_length)
    kdf = Argon2id(
        salt=salt,
        length=params.hash_length,
        iterations=params.iterations,
        lanes=params.lanes,
        memory_cost=params.memory_cost,
        secret=pepper if pepper else None,
    )
    digest = kdf.derive(plaintext.encode("utf-8"))
    return salt + digest


def verify_secret(
    plaintext: str,
    stored: bytes,
    pepper: bytes,
    params: ArgonParams = ARGON_PROD,
) -> bool:
    """Return True iff Argon2id(plaintext, pepper) matches *stored*.

    *stored* must be the output of hash_secret() (salt || hash).
    Constant-time via cryptography.exceptions.InvalidKey.
    """
    if len(stored) != params.salt_length + params.hash_length:
        return False
    salt = stored[: params.salt_length]
    expected = stored[params.salt_length :]
    kdf = Argon2id(
        salt=salt,
        length=params.hash_length,
        iterations=params.iterations,
        lanes=params.lanes,
        memory_cost=params.memory_cost,
        secret=pepper if pepper else None,
    )
    try:
        kdf.verify(plaintext.encode("utf-8"), expected)
        return True
    except InvalidKey:
        return False


def encrypt_field(plaintext: str, key: bytes) -> tuple[bytes, bytes]:
    """AES-256-GCM encrypt *plaintext*.

    Returns (ciphertext_with_tag, iv).  key must be 32 bytes.
    The authentication tag is appended to ciphertext by AESGCM.
    """
    if len(key) != 32:
        raise ValueError(f"AES-256 key must be 32 bytes, got {len(key)}")
    iv = os.urandom(IV_LENGTH)
    ct = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    return ct, iv


def decrypt_field(ciphertext: bytes, iv: bytes, key: bytes) -> str:
    """AES-256-GCM decrypt; raises ValueError on auth failure."""
    if len(key) != 32:
        raise ValueError(f"AES-256 key must be 32 bytes, got {len(key)}")
    try:
        pt = AESGCM(key).decrypt(iv, ciphertext, None)
        return pt.decode("utf-8")
    except Exception as exc:
        raise ValueError("Decryption failed — ciphertext or key is invalid") from exc


def constant_compare(a: str, b: str) -> bool:
    """Constant-time string comparison (timing-attack resistant)."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
