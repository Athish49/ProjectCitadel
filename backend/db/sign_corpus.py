"""CLI: sign the in-memory RAG corpora and write corpus_manifest.json.

Usage:
    uv run python -m db.sign_corpus

The orchestrator keypair is loaded from backend/keys/ (created if absent).
The private key file (keys/orchestrator.priv) is NOT committed to git.
The public key is embedded in corpus_manifest.json, which IS committed.

Re-running is safe: the manifest is re-signed with the same persistent key.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent.parent
_KEYS_DIR = _BACKEND_DIR / "keys"
_MANIFEST_PATH = _BACKEND_DIR / "corpus_manifest.json"


def main() -> None:
    from agent_system.identity.keys import KeypairManager
    from agent_system.tools.implementations.corpus_manifest import (
        build_manifest,
        save_manifest,
    )

    km = KeypairManager.load_or_generate("orchestrator", _KEYS_DIR)
    print(f"db/sign_corpus: orchestrator public key: {km.public_key_bytes.hex()}")

    manifest = build_manifest(km)
    save_manifest(manifest, _MANIFEST_PATH)

    print(f"db/sign_corpus: manifest written to {_MANIFEST_PATH.relative_to(_BACKEND_DIR)}")
    for name, entries in manifest["corpora"].items():
        print(f"  {name:8s}: {len(entries)} documents")


if __name__ == "__main__":
    main()
