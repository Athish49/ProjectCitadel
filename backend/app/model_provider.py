"""Model provider priority detection and unified Anthropic-compatible client.

Priority order (highest to lowest):
  1. Ollama  — always preferred when running locally (free, no API spend)
  2. Google  — if GOOGLE_API_KEY is set
  3. Groq    — if GROQ_API_KEY is set
  4. Anthropic — last resort; requires ANTHROPIC_API_KEY

Detection runs once on first call and is cached for the process lifetime.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import anthropic
import httpx

from app.config import cfg

log = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────

_OLLAMA_DEFAULT_HOST = "http://localhost:11434"
_OLLAMA_DEFAULT_MODEL = "gemma4:12b"
_GOOGLE_DEFAULT_MODEL = "gemini-2.0-flash-lite"
_GROQ_DEFAULT_MODEL = "llama-3.1-8b-instant"


class Provider(str, Enum):
    OLLAMA = "ollama"
    GOOGLE = "google"
    GROQ = "groq"
    ANTHROPIC = "anthropic"


# ── Fake Anthropic response objects ──────────────────────────────────────────


@dataclass
class _TextBlock:
    text: str
    type: str = "text"


@dataclass
class _ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class _FakeMessage:
    content: list[_TextBlock | _ToolUseBlock]
    stop_reason: str  # "end_turn" or "tool_use"


# ── Message/tool conversion helpers ──────────────────────────────────────────


def _to_oai_messages(
    messages: list[dict[str, Any]],
    system_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """Convert Anthropic-format message list to OpenAI format.

    Handles:
    - Simple string user/assistant messages
    - Assistant messages containing mixed _TextBlock/_ToolUseBlock content
      (accumulated from prior loop iterations via response.content)
    - User messages that are lists of tool_result dicts → individual "tool" messages
    """
    oai: list[dict[str, Any]] = []
    if system_prompt:
        oai.append({"role": "system", "content": system_prompt})

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            if isinstance(content, str):
                oai.append({"role": "user", "content": content})
            elif isinstance(content, list):
                # Anthropic tool results arrive as a list of tool_result dicts;
                # OpenAI expects each one as a separate "tool" message.
                if content and isinstance(content[0], dict) and content[0].get("type") == "tool_result":
                    for tr in content:
                        oai.append({
                            "role": "tool",
                            "tool_call_id": tr["tool_use_id"],
                            "content": str(tr.get("content", "")),
                        })
                else:
                    # Generic list — join any text parts
                    parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
                        elif isinstance(part, str):
                            parts.append(part)
                    oai.append({"role": "user", "content": " ".join(parts)})

        elif role == "assistant":
            if isinstance(content, str):
                oai.append({"role": "assistant", "content": content})
            elif isinstance(content, list):
                # Content is a list of _TextBlock / _ToolUseBlock (or real Anthropic SDK objects);
                # use duck typing so both work interchangeably.
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []

                for block in content:
                    btype = getattr(block, "type", None)
                    if btype is None and isinstance(block, dict):
                        btype = block.get("type")

                    if btype == "text":
                        text = getattr(block, "text", None)
                        if text is None and isinstance(block, dict):
                            text = block.get("text", "")
                        if text:
                            text_parts.append(text)

                    elif btype == "tool_use":
                        bid = getattr(block, "id", None) or (block.get("id", "") if isinstance(block, dict) else "")
                        bname = getattr(block, "name", None) or (block.get("name", "") if isinstance(block, dict) else "")
                        binput = getattr(block, "input", None) or (block.get("input", {}) if isinstance(block, dict) else {})
                        tool_calls.append({
                            "id": bid,
                            "type": "function",
                            "function": {
                                "name": bname,
                                "arguments": json.dumps(binput),
                            },
                        })

                oai_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": " ".join(text_parts) if text_parts else "",
                }
                if tool_calls:
                    oai_msg["tool_calls"] = tool_calls
                oai.append(oai_msg)

    return oai


def _to_oai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic tool definitions (input_schema) to OpenAI function format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
        if t
    ]


def _from_oai_response(response: Any) -> _FakeMessage:
    """Convert an OpenAI chat completion response to a fake Anthropic-compatible message."""
    choice = response.choices[0]
    msg = choice.message
    finish_reason = choice.finish_reason

    content: list[_TextBlock | _ToolUseBlock] = []

    if msg.content:
        content.append(_TextBlock(text=msg.content))

    if msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                input_data: dict[str, Any] = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, AttributeError):
                input_data = {}
            content.append(_ToolUseBlock(
                id=tc.id,
                name=tc.function.name,
                input=input_data,
            ))

    stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"
    return _FakeMessage(content=content, stop_reason=stop_reason)


# ── Provider detection ────────────────────────────────────────────────────────


def _check_ollama() -> tuple[bool, str]:
    """Return (is_available, model_name). Logs a warning if model not found in /api/tags."""
    host = cfg.ollama_host.rstrip("/")
    model = cfg.ollama_model

    try:
        resp = httpx.get(f"{host}/api/tags", timeout=2.0)
        if resp.status_code != 200:
            return False, model

        data = resp.json()
        loaded_names = [m.get("name", "") for m in data.get("models", [])]
        model_base = model.split(":")[0]
        found = any(
            n == model or n == model_base or n.startswith(model_base + ":")
            for n in loaded_names
        )
        if not found:
            log.warning(
                "model_provider: Ollama is running but model %r not found in loaded models %s. "
                "Run: ollama pull %s",
                model, loaded_names, model,
            )
        return True, model

    except Exception:
        return False, model


def detect_provider() -> tuple[Provider, str, str | None]:
    """Detect the highest-priority available provider.

    Returns (Provider, model_name, api_key_or_base_url).
    Raises RuntimeError when no provider can be configured.
    """
    # Priority 1: Ollama — always preferred; free and local
    ollama_ok, ollama_model = _check_ollama()
    if ollama_ok:
        return Provider.OLLAMA, ollama_model, cfg.ollama_host.rstrip("/")

    # Priority 2: Google
    google_key = cfg.google_api_key.strip()
    if google_key:
        return Provider.GOOGLE, cfg.google_model, google_key

    # Priority 3: Groq
    groq_key = cfg.groq_api_key.strip()
    if groq_key:
        return Provider.GROQ, cfg.groq_model, groq_key

    # Priority 4: Anthropic
    anthropic_key = cfg.anthropic_api_key.strip()
    if not anthropic_key:
        raise RuntimeError(
            "No LLM provider available. Set one of: OLLAMA_HOST (run Ollama locally), "
            "GOOGLE_API_KEY, GROQ_API_KEY, or ANTHROPIC_API_KEY."
        )
    return Provider.ANTHROPIC, "claude-haiku-4-5-20251001", anthropic_key


# ── Unified sync client (Anthropic interface over OpenAI-compatible backends) ─


def _build_oai_client(provider: Provider, key: str | None) -> Any:
    from openai import OpenAI
    host = cfg.ollama_host.rstrip("/")

    if provider == Provider.OLLAMA:
        return OpenAI(base_url=f"{host}/v1", api_key="ollama")
    if provider == Provider.GOOGLE:
        return OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=key or "",
        )
    if provider == Provider.GROQ:
        return OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=key or "",
        )
    raise ValueError(f"Cannot build OAI client for provider {provider}")


class _UnifiedMessages:
    """Sync .messages.create() that speaks Anthropic's call signature."""

    def __init__(self, model: str, oai_client: Any) -> None:
        self._model = model
        self._oai = oai_client

    def create(
        self,
        *,
        model: str,  # provider-determined; call-site model= is accepted but ignored
        max_tokens: int,
        messages: list[dict[str, Any]],
        temperature: float = 0,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **_kwargs: Any,
    ) -> _FakeMessage:
        # Models with built-in chain-of-thought (e.g. Gemma 4) consume tokens for
        # internal reasoning before producing visible output. A low cap (e.g. 64 for
        # the semantic classifier) is exhausted before any text appears.
        effective_max_tokens = max(max_tokens, 512)
        oai_messages = _to_oai_messages(messages, system_prompt=system)

        call_kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": effective_max_tokens,
            "temperature": temperature,
            "messages": oai_messages,
        }

        if tools:
            oai_tools = _to_oai_tools(tools)
            if oai_tools:
                call_kwargs["tools"] = oai_tools
                call_kwargs["tool_choice"] = "auto"

        response = self._oai.chat.completions.create(**call_kwargs)
        return _from_oai_response(response)


class UnifiedAnthropicCompatibleClient:
    """Sync client with .messages attribute — drop-in for anthropic.Anthropic()."""

    def __init__(self, model: str, oai_client: Any) -> None:
        self.messages = _UnifiedMessages(model, oai_client)


class _AsyncUnifiedMessages:
    """Async .messages.create() that wraps the sync OAI call in asyncio.to_thread."""

    def __init__(self, sync_messages: _UnifiedMessages) -> None:
        self._sync = sync_messages

    async def create(self, **kwargs: Any) -> _FakeMessage:
        return await asyncio.to_thread(self._sync.create, **kwargs)


class AsyncUnifiedAnthropicCompatibleClient:
    """Async client with .messages attribute — drop-in for anthropic.AsyncAnthropic()."""

    def __init__(self, sync_client: UnifiedAnthropicCompatibleClient) -> None:
        self.messages = _AsyncUnifiedMessages(sync_client.messages)


# ── Cached factory functions ───────────────────────────────────────────────────

_cached_provider: tuple[Provider, str, str | None] | None = None
_cached_sync: anthropic.Anthropic | UnifiedAnthropicCompatibleClient | None = None
_cached_async: anthropic.AsyncAnthropic | AsyncUnifiedAnthropicCompatibleClient | None = None


def _provider() -> tuple[Provider, str, str | None]:
    global _cached_provider
    if _cached_provider is None:
        _cached_provider = detect_provider()
        log.info("model_provider: active=%s model=%s", _cached_provider[0].value, _cached_provider[1])
    return _cached_provider


def get_sync_client() -> anthropic.Anthropic | UnifiedAnthropicCompatibleClient:
    """Return a cached sync client for the detected provider."""
    global _cached_sync
    if _cached_sync is None:
        prov, model, key = _provider()
        if prov == Provider.ANTHROPIC:
            _cached_sync = anthropic.Anthropic()
        else:
            _cached_sync = UnifiedAnthropicCompatibleClient(model, _build_oai_client(prov, key))
    return _cached_sync


def get_async_client() -> anthropic.AsyncAnthropic | AsyncUnifiedAnthropicCompatibleClient:
    """Return a cached async client for the detected provider."""
    global _cached_async
    if _cached_async is None:
        prov, model, key = _provider()
        if prov == Provider.ANTHROPIC:
            _cached_async = anthropic.AsyncAnthropic()
        else:
            sync = get_sync_client()
            assert isinstance(sync, UnifiedAnthropicCompatibleClient)
            _cached_async = AsyncUnifiedAnthropicCompatibleClient(sync)
    return _cached_async
