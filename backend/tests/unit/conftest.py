"""Unit-test environment isolation."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_qdrant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent unit tests from hitting the live Qdrant service.

    rag_retrievers._use_qdrant() gates on QDRANT_URL. When backend/.env is
    loaded at import time, QDRANT_URL is set and the stub fallback is bypassed,
    causing every RAG unit test to hit a live server that returns 404. The
    production stub fallback is correct; unit tests just need QDRANT_URL unset.
    """
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
