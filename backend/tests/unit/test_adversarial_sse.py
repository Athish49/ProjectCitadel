"""Unit tests for the adversarial SSE endpoint (Sprint 4.3.4).

Note: the in-process event-bus tests (TestEventBus) that previously lived
here were removed along with app/showcase/events.py, which was dead code —
superseded by DB polling (see app/showcase/adversarial_sse.py) and never
imported by any production module. Only this test file imported it.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


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
