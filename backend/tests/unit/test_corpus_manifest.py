"""Unit tests for corpus_manifest module (Sprint P12, attack #17).

Tests cover:
  - build_manifest: manifest structure, corpus entries, signature validity
  - verify_manifest: happy path, hash mismatch, tampered signature, wrong key,
    missing doc, corpus not found
  - save/load round-trip
  - CI gate: if corpus_manifest.json exists, verify against live in-memory corpus
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agent_system.identity.keys import KeypairManager
from agent_system.tools.implementations.corpus_manifest import (
    _CORPUS_MAP,
    _doc_hash,
    build_manifest,
    load_manifest,
    save_manifest,
    verify_manifest,
)

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Lightweight fixture corpus — avoids coupling most tests to corpus content
# ---------------------------------------------------------------------------

_DOCS_A = [
    {"doc_id": "test-001", "source": "Test.pdf §1", "text": "Test document one."},
    {"doc_id": "test-002", "source": "Test.pdf §2", "text": "Test document two."},
    {"doc_id": "test-003", "source": "Test.pdf §3", "text": "Test document three."},
]
_DOCS_B = [
    {"doc_id": "other-001", "source": "Other.pdf §1", "text": "Other document one."},
]
_TEST_CORPORA: dict[str, list[dict]] = {"alpha": _DOCS_A, "beta": _DOCS_B}


@pytest.fixture()
def km() -> KeypairManager:
    return KeypairManager.generate("orchestrator")


@pytest.fixture()
def manifest(km) -> dict:
    return build_manifest(km, corpora=_TEST_CORPORA)


# ---------------------------------------------------------------------------
# TestDocHash — pure hash function
# ---------------------------------------------------------------------------


class TestDocHash:
    def test_returns_64_hex_chars(self):
        h = _doc_hash(_DOCS_A[0])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        assert _doc_hash(_DOCS_A[0]) == _doc_hash(_DOCS_A[0])

    def test_different_text_gives_different_hash(self):
        doc1 = {"doc_id": "x", "source": "s", "text": "alpha"}
        doc2 = {"doc_id": "x", "source": "s", "text": "beta"}
        assert _doc_hash(doc1) != _doc_hash(doc2)

    def test_different_doc_id_gives_different_hash(self):
        doc1 = {"doc_id": "a", "source": "s", "text": "same"}
        doc2 = {"doc_id": "b", "source": "s", "text": "same"}
        assert _doc_hash(doc1) != _doc_hash(doc2)


# ---------------------------------------------------------------------------
# TestBuildManifest — structure and correctness
# ---------------------------------------------------------------------------


class TestBuildManifest:
    def test_required_keys_present(self, manifest):
        assert {"version", "created_at", "corpora", "public_key", "signature"} <= manifest.keys()

    def test_version_is_one(self, manifest):
        assert manifest["version"] == "1"

    def test_corpora_keys_match_input(self, manifest):
        assert set(manifest["corpora"].keys()) == {"alpha", "beta"}

    def test_document_count_alpha(self, manifest):
        assert len(manifest["corpora"]["alpha"]) == len(_DOCS_A)

    def test_document_count_beta(self, manifest):
        assert len(manifest["corpora"]["beta"]) == len(_DOCS_B)

    def test_each_entry_has_doc_id_and_hash(self, manifest):
        for entries in manifest["corpora"].values():
            for entry in entries:
                assert "doc_id" in entry
                assert "hash" in entry
                assert len(entry["hash"]) == 64

    def test_public_key_matches_signer(self, km, manifest):
        assert manifest["public_key"] == km.public_key_bytes.hex()

    def test_signature_is_128_hex_chars(self, manifest):
        assert len(manifest["signature"]) == 128
        int(manifest["signature"], 16)  # raises if not valid hex

    def test_signature_validates(self, manifest):
        ok, errors = verify_manifest(manifest, corpora=_TEST_CORPORA)
        assert ok
        assert errors == []

    def test_defaults_to_module_corpus_map(self, km):
        full_manifest = build_manifest(km)
        assert set(full_manifest["corpora"].keys()) == set(_CORPUS_MAP.keys())

    def test_full_corpus_document_counts(self, km):
        full_manifest = build_manifest(km)
        for name, docs in _CORPUS_MAP.items():
            assert len(full_manifest["corpora"][name]) == len(docs)


# ---------------------------------------------------------------------------
# TestVerifyManifest — happy path and failure modes
# ---------------------------------------------------------------------------


class TestVerifyManifest:
    def test_valid_manifest_ok(self, manifest):
        ok, errors = verify_manifest(manifest, corpora=_TEST_CORPORA)
        assert ok is True
        assert errors == []

    def test_tampered_corpus_text_detected(self, km, manifest):
        # Simulate live corpus text changing after the manifest was signed.
        tampered = copy.deepcopy(_TEST_CORPORA)
        tampered["alpha"][0]["text"] = "TAMPERED content."
        ok, errors = verify_manifest(manifest, corpora=tampered)
        assert ok is False
        assert any("hash_mismatch" in e and "test-001" in e for e in errors)

    def test_tampered_manifest_hash_detected(self, manifest):
        bad = copy.deepcopy(manifest)
        bad["corpora"]["alpha"][0]["hash"] = "a" * 64
        ok, errors = verify_manifest(bad, corpora=_TEST_CORPORA)
        assert ok is False
        assert any("hash_mismatch" in e for e in errors)

    def test_tampered_signature_invalid(self, manifest):
        bad = copy.deepcopy(manifest)
        sig_bytes = bytearray(bytes.fromhex(bad["signature"]))
        sig_bytes[0] ^= 0xFF
        bad["signature"] = bytes(sig_bytes).hex()
        ok, errors = verify_manifest(bad, corpora=_TEST_CORPORA)
        assert ok is False
        assert "signature_invalid" in errors

    def test_wrong_signing_key_detected(self, manifest):
        other_km = KeypairManager.generate("orchestrator")
        # Build manifest with same content but different key — then verify
        # the original manifest (signed by km) against a corpus signed by other_km.
        # Swap the signature from the wrong-key manifest into the original.
        wrong_manifest = build_manifest(other_km, corpora=_TEST_CORPORA)
        bad = copy.deepcopy(manifest)
        bad["signature"] = wrong_manifest["signature"]
        ok, errors = verify_manifest(bad, corpora=_TEST_CORPORA)
        assert ok is False
        assert "signature_invalid" in errors

    def test_missing_doc_in_live_corpus(self, manifest):
        truncated = {"alpha": _DOCS_A[1:], "beta": _DOCS_B}  # drop test-001
        ok, errors = verify_manifest(manifest, corpora=truncated)
        assert ok is False
        assert any("missing_doc" in e and "test-001" in e for e in errors)

    def test_unknown_corpus_name_in_manifest(self, km):
        extra_corpora = {**_TEST_CORPORA, "gamma": [{"doc_id": "g-001", "source": "G.pdf", "text": "gamma"}]}
        full_manifest = build_manifest(km, corpora=extra_corpora)
        # Verify against corpora that don't include "gamma"
        ok, errors = verify_manifest(full_manifest, corpora=_TEST_CORPORA)
        assert ok is False
        assert any("corpus_not_found:gamma" in e for e in errors)

    def test_multiple_hash_mismatches_all_reported(self, manifest):
        tampered = copy.deepcopy(_TEST_CORPORA)
        tampered["alpha"][0]["text"] = "TAMPERED one."
        tampered["alpha"][1]["text"] = "TAMPERED two."
        ok, errors = verify_manifest(manifest, corpora=tampered)
        assert ok is False
        mismatches = [e for e in errors if "hash_mismatch" in e]
        assert len(mismatches) == 2

    def test_empty_signature_triggers_parse_error(self, manifest):
        bad = copy.deepcopy(manifest)
        bad["signature"] = "not-hex!"
        ok, errors = verify_manifest(bad, corpora=_TEST_CORPORA)
        assert ok is False
        assert any("manifest_parse_error" in e for e in errors)


# ---------------------------------------------------------------------------
# TestManifestIO — save / load round-trip
# ---------------------------------------------------------------------------


class TestManifestIO:
    def test_save_load_round_trip(self, manifest, tmp_path):
        p = tmp_path / "manifest.json"
        save_manifest(manifest, p)
        loaded = load_manifest(p)
        assert loaded == manifest

    def test_saved_file_is_valid_json(self, manifest, tmp_path):
        p = tmp_path / "manifest.json"
        save_manifest(manifest, p)
        json.loads(p.read_text())  # raises on invalid JSON

    def test_loaded_manifest_still_verifies(self, manifest, tmp_path):
        p = tmp_path / "manifest.json"
        save_manifest(manifest, p)
        loaded = load_manifest(p)
        ok, errors = verify_manifest(loaded, corpora=_TEST_CORPORA)
        assert ok is True
        assert errors == []

    def test_file_ends_with_newline(self, manifest, tmp_path):
        p = tmp_path / "manifest.json"
        save_manifest(manifest, p)
        assert p.read_text().endswith("\n")


# ---------------------------------------------------------------------------
# CI gate — only runs when corpus_manifest.json has been committed
# ---------------------------------------------------------------------------


_MANIFEST_FILE = Path(__file__).parent.parent.parent / "corpus_manifest.json"


@pytest.mark.skipif(
    not _MANIFEST_FILE.exists(),
    reason="corpus_manifest.json not present — run `uv run python -m db.sign_corpus` to generate",
)
class TestCorpusManifestCiGate:
    def test_manifest_is_valid_json(self):
        json.loads(_MANIFEST_FILE.read_text())

    def test_manifest_verifies_against_live_corpus(self):
        manifest = load_manifest(_MANIFEST_FILE)
        ok, errors = verify_manifest(manifest)  # uses default _CORPUS_MAP
        assert ok is True, f"Corpus manifest verification failed: {errors}"

    def test_manifest_has_all_three_corpora(self):
        manifest = load_manifest(_MANIFEST_FILE)
        assert set(manifest["corpora"].keys()) >= {"policy", "fraud", "faq"}
