"""Unit tests for the adversarial SSE event bus and endpoint (Sprint 4.3.4)."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Event bus tests
# ---------------------------------------------------------------------------


def _fresh_events():
    """Import events module with a clean global state."""
    import importlib
    import sys
    if "app.showcase.events" in sys.modules:
        del sys.modules["app.showcase.events"]
    import app.showcase.events as ev
    ev._subscribers.clear()
    ev._breach_count = 0
    ev._last_breach_at = None
    return ev


class TestEventBus:
    def test_subscribe_adds_queue(self):
        ev = _fresh_events()
        assert len(ev._subscribers) == 0
        q = ev.subscribe()
        assert q in ev._subscribers

    def test_unsubscribe_removes_queue(self):
        ev = _fresh_events()
        q = ev.subscribe()
        ev.unsubscribe(q)
        assert q not in ev._subscribers

    def test_unsubscribe_unknown_queue_is_safe(self):
        ev = _fresh_events()
        q: asyncio.Queue = asyncio.Queue()
        ev.unsubscribe(q)  # must not raise

    def test_publish_non_breach_does_not_increment_count(self):
        ev = _fresh_events()
        event = ev.AdversarialEvent(
            trace_id="t1", session_id="s1", attack_id=1,
            verdict="BLOCKED_INGRESS",
        )
        ev.publish(event)
        assert ev._breach_count == 0
        assert ev._last_breach_at is None

    def test_publish_breach_increments_count(self):
        ev = _fresh_events()
        event = ev.AdversarialEvent(
            trace_id="t1", session_id="s1", attack_id=1,
            verdict="EVADED_INGRESS",
        )
        ev.publish(event)
        assert ev._breach_count == 1
        assert ev._last_breach_at is not None

    def test_publish_multiple_breaches_accumulate(self):
        ev = _fresh_events()
        for _ in range(3):
            ev.publish(ev.AdversarialEvent(
                trace_id="t", session_id="s", attack_id=1, verdict="EVADED_INGRESS",
            ))
        assert ev._breach_count == 3

    def test_publish_delivers_to_subscriber(self):
        ev = _fresh_events()
        q = ev.subscribe()
        ev.publish(ev.AdversarialEvent(
            trace_id="t1", session_id="s1", attack_id=7, verdict="BLOCKED_INGRESS",
            sanitizer_detections=["dan_mode"], chars_stripped=5,
        ))
        assert not q.empty()
        payload = q.get_nowait()
        assert payload["trace_id"] == "t1"
        assert payload["attack_id"] == 7
        assert payload["verdict"] == "BLOCKED_INGRESS"
        assert payload["sanitizer_detections"] == ["dan_mode"]
        assert payload["chars_stripped"] == 5
        assert payload["is_breach"] is False
        assert payload["breach_count"] == 0

    def test_publish_breach_payload_has_is_breach_true(self):
        ev = _fresh_events()
        q = ev.subscribe()
        ev.publish(ev.AdversarialEvent(
            trace_id="t2", session_id="s2", attack_id=3, verdict="EVADED_INGRESS",
        ))
        payload = q.get_nowait()
        assert payload["is_breach"] is True
        assert payload["breach_count"] == 1

    def test_get_breach_stats_initial(self):
        ev = _fresh_events()
        stats = ev.get_breach_stats()
        assert stats["breach_count"] == 0
        assert stats["last_breach_at"] is None

    def test_get_breach_stats_after_breach(self):
        ev = _fresh_events()
        ev.publish(ev.AdversarialEvent(
            trace_id="t", session_id="s", attack_id=1, verdict="EVADED_INGRESS",
        ))
        stats = ev.get_breach_stats()
        assert stats["breach_count"] == 1
        assert stats["last_breach_at"] is not None

    def test_full_queue_drops_and_unsubscribes(self):
        ev = _fresh_events()
        q = ev.subscribe()
        # Fill queue to maxsize
        for i in range(q.maxsize):
            q.put_nowait({"i": i})
        # Next publish should drop this subscriber
        ev.publish(ev.AdversarialEvent(
            trace_id="t", session_id="s", attack_id=1, verdict="BLOCKED_INGRESS",
        ))
        assert q not in ev._subscribers


# ---------------------------------------------------------------------------
# GitHub issue creation tests
# ---------------------------------------------------------------------------


class TestGitHubIssue:
    @pytest.mark.asyncio
    async def test_skips_when_no_token(self, caplog):
        import logging
        from app.showcase.playground import _open_github_issue
        with patch.dict("os.environ", {"GITHUB_TOKEN": "", "GITHUB_REPO": "owner/repo"}):
            with caplog.at_level(logging.WARNING):
                await _open_github_issue("trace-abc", "sess-1", 7)
        assert any("GITHUB_TOKEN" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_skips_when_no_repo(self, caplog):
        import logging
        from app.showcase.playground import _open_github_issue
        with patch.dict("os.environ", {"GITHUB_TOKEN": "tok", "GITHUB_REPO": ""}):
            with caplog.at_level(logging.WARNING):
                await _open_github_issue("trace-abc", "sess-1", 7)
        assert any("GITHUB_REPO" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_posts_to_github_when_configured(self):
        from app.showcase.playground import _open_github_issue
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.dict("os.environ", {"GITHUB_TOKEN": "tok", "GITHUB_REPO": "owner/repo"}):
            with patch("app.showcase.playground.httpx.AsyncClient", return_value=mock_client):
                await _open_github_issue("trace-abc", "sess-1", 7)

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert "repos/owner/repo/issues" in call_kwargs[0][0]
        body = call_kwargs[1]["json"]
        assert "adversarial" in body.get("labels", [])
        assert "attack_id=7" in body["title"]

    @pytest.mark.asyncio
    async def test_logs_warning_on_http_error(self, caplog):
        import logging
        import httpx
        from app.showcase.playground import _open_github_issue

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("down"))

        with patch.dict("os.environ", {"GITHUB_TOKEN": "tok", "GITHUB_REPO": "owner/repo"}):
            with patch("app.showcase.playground.httpx.AsyncClient", return_value=mock_client):
                with caplog.at_level(logging.WARNING):
                    await _open_github_issue("trace-abc", "sess-1", 7)

        assert any("github_issue_open_failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# SSE endpoint smoke test
# ---------------------------------------------------------------------------


class TestAdversarialSSEEndpoint:
    def test_sse_router_is_registered(self):
        from app.showcase.adversarial_sse import router
        route_paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/showcase/sse/adversarial" in route_paths

    @pytest.mark.asyncio
    async def test_sse_response_headers(self):
        """Verify content-type and cache headers by calling the async endpoint directly."""
        from app.showcase.adversarial_sse import adversarial_stream
        from fastapi.responses import StreamingResponse

        response = await adversarial_stream()
        assert isinstance(response, StreamingResponse)
        assert response.media_type == "text/event-stream"
        assert response.headers.get("cache-control", "").startswith("no-cache")
        assert response.headers.get("x-accel-buffering") == "no"
