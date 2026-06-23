"""RAG corpus integrity manifest — P12 (signed RAG manifest, attack #17).

build_manifest  — build and sign a manifest over the in-memory corpus constants.
verify_manifest — verify signature and re-hash each document against current corpus.
save_manifest / load_manifest — JSON serialization helpers.

The manifest signs the in-memory corpora (_POLICY_CORPUS, _FRAUD_CORPUS,
_FAQ_CORPUS).  Qdrant is treated as an untrusted downstream cache; the
manifest is the authoritative integrity anchor.

Corpus constants are injected via the `corpora` parameter so tests can
substitute lightweight fixtures without monkeypatching globals.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from agent_system.identity.signing import verify_message
from agent_system.tools.implementations.rag_retrievers import (
    _FAQ_CORPUS,
    _FRAUD_CORPUS,
    _POLICY_CORPUS,
)

if TYPE_CHECKING:
    from agent_system.identity.keys import KeypairManager

_CORPUS_MAP: dict[str, list[dict]] = {
    "policy": _POLICY_CORPUS,
    "fraud":  _FRAUD_CORPUS,
    "faq":    _FAQ_CORPUS,
}


def _doc_hash(doc: dict) -> str:
    """Return SHA-256 hex digest of the canonical string representation of *doc*."""
    canonical = f"doc_id:{doc['doc_id']}\nsource:{doc['source']}\ntext:{doc['text']}"
    return hashlib.sha256(canonical.encode()).hexdigest()


def _payload_bytes(manifest_without_sig: dict) -> bytes:
    """Deterministic JSON encoding used for both signing and verification."""
    return json.dumps(manifest_without_sig, sort_keys=True, separators=(",", ":")).encode()


def build_manifest(
    signer: "KeypairManager",
    corpora: dict[str, list[dict]] | None = None,
) -> dict:
    """Build and sign an integrity manifest over *corpora*.

    Args:
        signer:  KeypairManager holding the orchestrator signing keypair.
        corpora: Corpus map to sign.  Defaults to _CORPUS_MAP (all three
                 in-memory corpora).  Pass a custom dict in tests.

    Returns:
        A JSON-serializable dict with keys: version, created_at, corpora
        (per-doc hashes), public_key (hex), and signature (hex).
    """
    if corpora is None:
        corpora = _CORPUS_MAP

    corpus_entries: dict[str, list[dict]] = {
        name: [{"doc_id": doc["doc_id"], "hash": _doc_hash(doc)} for doc in docs]
        for name, docs in corpora.items()
    }

    unsigned: dict = {
        "version":    "1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpora":    corpus_entries,
        "public_key": signer.public_key_bytes.hex(),
    }
    signature = signer.sign(_payload_bytes(unsigned))
    return {**unsigned, "signature": signature.hex()}


def verify_manifest(
    manifest: dict,
    corpora: dict[str, list[dict]] | None = None,
) -> tuple[bool, list[str]]:
    """Verify the manifest signature and re-hash each document against *corpora*.

    Args:
        manifest: The manifest dict (from build_manifest or load_manifest).
        corpora:  Corpus map to verify against.  Defaults to _CORPUS_MAP.

    Returns:
        (ok, errors) — ok is True only when the signature is valid and all
        document hashes match current corpus contents.
    """
    if corpora is None:
        corpora = _CORPUS_MAP

    errors: list[str] = []

    try:
        public_key_bytes = bytes.fromhex(manifest["public_key"])
        signature_bytes  = bytes.fromhex(manifest["signature"])
    except (KeyError, ValueError) as exc:
        errors.append(f"manifest_parse_error:{exc}")
        return False, errors

    unsigned = {k: v for k, v in manifest.items() if k != "signature"}
    if not verify_message(public_key_bytes, _payload_bytes(unsigned), signature_bytes):
        errors.append("signature_invalid")

    manifest_corpora: dict = manifest.get("corpora", {})
    for name, entries in manifest_corpora.items():
        live_docs = corpora.get(name)
        if live_docs is None:
            errors.append(f"corpus_not_found:{name}")
            continue
        live_by_id = {doc["doc_id"]: doc for doc in live_docs}
        for entry in entries:
            doc_id = entry["doc_id"]
            live_doc = live_by_id.get(doc_id)
            if live_doc is None:
                errors.append(f"corpus:{name}:missing_doc:{doc_id}")
            elif _doc_hash(live_doc) != entry["hash"]:
                errors.append(f"corpus:{name}:hash_mismatch:{doc_id}")

    return len(errors) == 0, errors


def save_manifest(manifest: dict, path: Path) -> None:
    """Write *manifest* to *path* as pretty-printed JSON."""
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def load_manifest(path: Path) -> dict:
    """Load a manifest dict from *path*."""
    return json.loads(path.read_text())
