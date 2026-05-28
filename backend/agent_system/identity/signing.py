"""Ed25519 signing helpers (P8 — task 1.2.1).

Stateless functions only. Callers are responsible for audit logging.
"""
from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def sign_message(private_key_bytes: bytes, message: bytes) -> bytes:
    """Sign *message* with the 32-byte Ed25519 private-key seed.

    Returns a 64-byte signature.
    """
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return private_key.sign(message)


def verify_message(public_key_bytes: bytes, message: bytes, signature: bytes) -> bool:
    """Verify *signature* over *message* using the 32-byte Ed25519 public key.

    Returns False on any mismatch; never raises.
    """
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, message)
        return True
    except (InvalidSignature, ValueError):
        return False


def private_key_to_bytes(private_key: Ed25519PrivateKey) -> bytes:
    """Export a cryptography private-key object to its raw 32-byte seed."""
    return private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())


def public_key_to_bytes(public_key: Ed25519PublicKey) -> bytes:
    """Export a cryptography public-key object to its raw 32-byte form."""
    return public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
