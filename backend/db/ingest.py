"""Vector ingestion for Qdrant collections (run with: uv run python -m db.ingest).

Embeds the 10 policy-doc chunks, 8 fraud-rule chunks, and 10 public-FAQ chunks
using BAAI/bge-small-en-v1.5 via fastembed and upserts them into:
  - ProjectCitadel-policy_docs  (CONFIDENTIAL)
  - ProjectCitadel-fraud_rules  (SECRET)
  - ProjectCitadel-public_faq   (PUBLIC)

NOTE: The Qdrant API key (QDRANT_API_KEY) must be re-issued with rw scope for
ProjectCitadel-public_faq before FAQ ingestion will succeed. The existing scoped
JWT only covers ProjectCitadel-policy_docs and ProjectCitadel-fraud_rules.

Safe to re-run: upsert is idempotent (point IDs are stable hash-based UUIDs).
"""
from __future__ import annotations

import os
import sys
import uuid

# Load .env if running as a script (conftest.py is not in scope here).
def _load_env() -> None:
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

_load_env()

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from fastembed import TextEmbedding

from agent_system.tools.implementations.rag_retrievers import (
    _EMBED_MODEL,
    _FAQ_CORPUS,
    _FRAUD_CORPUS,
    _POLICY_CORPUS,
)


def _stable_id(doc_id: str) -> str:
    """Deterministic UUID from doc_id so re-runs upsert rather than append."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"secureclaim:{doc_id}"))


def _build_points(corpus: list[dict], data_label: str, vectors: list) -> list[PointStruct]:
    return [
        PointStruct(
            id=_stable_id(doc["doc_id"]),
            vector=vec.tolist(),
            payload={
                "doc_id":     doc["doc_id"],
                "source":     doc["source"],
                "text":       doc["text"],
                "data_label": data_label,
            },
        )
        for doc, vec in zip(corpus, vectors)
    ]


def main() -> None:
    qdrant_url = os.environ.get("QDRANT_URL")
    if not qdrant_url:
        print("db/ingest: QDRANT_URL not set — nothing to ingest", file=sys.stderr)
        sys.exit(1)

    policy_collection = os.environ.get("QDRANT_POLICY_COLLECTION", "ProjectCitadel-policy_docs")
    fraud_collection  = os.environ.get("QDRANT_FRAUD_COLLECTION",  "ProjectCitadel-fraud_rules")
    faq_collection    = os.environ.get("QDRANT_FAQ_COLLECTION",    "ProjectCitadel-public_faq")

    print(f"db/ingest: connecting to {qdrant_url.split('@')[-1]}")
    client = QdrantClient(
        url=qdrant_url,
        api_key=os.environ.get("QDRANT_API_KEY"),
    )

    print(f"db/ingest: loading embedding model {_EMBED_MODEL!r} (first run downloads ~130 MB)")
    embedder = TextEmbedding(_EMBED_MODEL)

    # ── policy_docs ───────────────────────────────────────────────────────────
    print(f"  embedding {len(_POLICY_CORPUS)} policy-doc chunks …")
    policy_vecs = list(embedder.embed([d["text"] for d in _POLICY_CORPUS]))
    policy_points = _build_points(_POLICY_CORPUS, "CONFIDENTIAL", policy_vecs)
    client.upsert(collection_name=policy_collection, points=policy_points)
    print(f"  {policy_collection:<40} : {len(policy_points)} points upserted")

    # ── fraud_rules ───────────────────────────────────────────────────────────
    print(f"  embedding {len(_FRAUD_CORPUS)} fraud-rule chunks …")
    fraud_vecs = list(embedder.embed([d["text"] for d in _FRAUD_CORPUS]))
    fraud_points = _build_points(_FRAUD_CORPUS, "SECRET", fraud_vecs)
    client.upsert(collection_name=fraud_collection, points=fraud_points)
    print(f"  {fraud_collection:<40} : {len(fraud_points)} points upserted")

    # ── public_faq ────────────────────────────────────────────────────────────
    # NOTE: QDRANT_API_KEY must be re-issued with rw scope for this collection.
    print(f"  embedding {len(_FAQ_CORPUS)} public-FAQ chunks …")
    faq_vecs = list(embedder.embed([d["text"] for d in _FAQ_CORPUS]))
    faq_points = _build_points(_FAQ_CORPUS, "PUBLIC", faq_vecs)
    client.upsert(collection_name=faq_collection, points=faq_points)
    print(f"  {faq_collection:<40} : {len(faq_points)} points upserted")

    print("db/ingest: done")


if __name__ == "__main__":
    main()
