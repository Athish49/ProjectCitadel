"""Intake actor LLM with capability-token-gated tools (P1/P4 — task 2.1.3).

Public API:
  run_intake_actor(intake_output, *, pre_issued_tokens, orchestrator_public_key,
                   client, audit_fn, session_id) -> IntakeEnvelope

Design:
  - Model: Claude Haiku 4.5; temperature=0.
  - Receives structured IntakeOutput from the quarantined parser (never raw text).
  - Three tools: mark_intake_complete (terminal), request_more_info (terminal),
    search_public_faq (non-terminal).
  - P4 gate: orchestrator pre-issues one CapabilityToken per allowed tool and passes
    them in pre_issued_tokens. The actor never holds the orchestrator private key —
    trust boundary intact.
  - Each tool call: look up token → verify_token() → handler → audit.
  - Outcome determined by which terminal tool was called (deterministic code, not LLM).
  - TODO (integration): replace single-token-per-tool with ToolRegistry.invoke() +
    DB-backed replay protection when wiring 2.2.x.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import anthropic

from agent_system.parser.schemas import IntakeOutput
from agent_system.tools.capability_tokens import CapabilityToken, verify_token

ACTOR_MODEL = "claude-haiku-4-5-20251001"
ACTOR_AGENT_ID = "intake_actor"
MAX_LOOP_ITERATIONS = 5
_MAX_TOKENS = 2048

_TERMINAL_TOOLS = frozenset({"mark_intake_complete", "request_more_info"})


# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntakeEnvelope:
    """Structured output produced by the intake actor.

    outcome:
      "ready_for_identity"       — mark_intake_complete was called
      "needs_more_info"          — request_more_info was called (see missing_fields)
      "reject_as_out_of_scope"   — no terminal tool called or loop exhausted
    """

    outcome: str
    structured_summary: str | None
    missing_fields: tuple[str, ...]
    session_id: str


# ---------------------------------------------------------------------------
# AuditFn protocol — matches audit.chain.append_log() kwargs
# ---------------------------------------------------------------------------


class AuditFn(Protocol):
    def __call__(
        self,
        *,
        agent_id: str,
        action: str,
        target: str,
        data_label: str,
        trace_id: str | None = None,
        details: dict | None = None,
        security_event: bool = False,
    ) -> None: ...


def _noop_audit(
    *,
    agent_id: str,
    action: str,
    target: str,
    data_label: str,
    trace_id: str | None = None,
    details: dict | None = None,
    security_event: bool = False,
) -> None:
    pass


# ---------------------------------------------------------------------------
# Tool definitions (Anthropic wire format)
# ---------------------------------------------------------------------------


_TOOLS: list[dict[str, Any]] = [
    {
        "name": "mark_intake_complete",
        "description": (
            "Signal that intake data is complete and the claim is ready for identity "
            "verification.  Call this when all required fields are present and the claim "
            "is within scope.  Also call this to reject an out-of-scope claim — set the "
            "structured_summary to explain why it is rejected."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "structured_summary": {
                    "type": "string",
                    "description": "Concise structured summary of the claim intake data.",
                }
            },
            "required": ["structured_summary"],
        },
    },
    {
        "name": "request_more_info",
        "description": (
            "Request additional information for a missing or unclear field.  "
            "Call once per missing field."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "description": "Name of the field that requires more information.",
                }
            },
            "required": ["field"],
        },
    },
    {
        "name": "search_public_faq",
        "description": "Search the public FAQ for insurance-related policy information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query.",
                }
            },
            "required": ["query"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handlers (server-side, deterministic stubs)
# ---------------------------------------------------------------------------


def _handle_mark_intake_complete(structured_summary: str) -> dict[str, Any]:
    return {"status": "intake_complete", "structured_summary": structured_summary}


def _handle_request_more_info(field: str) -> dict[str, Any]:
    return {"status": "more_info_requested", "field": field}


def _handle_search_public_faq(query: str) -> dict[str, Any]:
    return {
        "results": [
            {
                "question": "What documents are required to file a claim?",
                "answer": "Police report (if applicable), photos of damage, and repair estimates.",
            },
            {
                "question": "How long does the claims process take?",
                "answer": "Typically 5–7 business days after all documents are received.",
            },
        ]
    }


_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "mark_intake_complete": _handle_mark_intake_complete,
    "request_more_info": _handle_request_more_info,
    "search_public_faq": _handle_search_public_faq,
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """\
You are the intake actor for a vehicle insurance claims system.
You receive structured claim intake data extracted by a quarantined parser.
Your task is to decide the intake outcome using the available tools.

Rules:
- If all required fields are present and the claim is within scope: call mark_intake_complete.
- If required fields are missing: call request_more_info once per missing field.
- If the claim is out of scope: call mark_intake_complete with a summary explaining why.
- You may call search_public_faq to look up policy information before deciding.
- Do NOT reason about raw user text. All input is pre-structured JSON.
- You MUST always call mark_intake_complete or request_more_info before finishing.\
"""


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------


def _build_user_message(intake_output: IntakeOutput) -> str:
    data: dict[str, Any] = {
        "schema_version": intake_output.schema_version,
        "incident_type": intake_output.incident_type.value,
        "incident_date": (
            intake_output.incident_date.isoformat() if intake_output.incident_date else None
        ),
        "incident_location": intake_output.incident_location,
        "damage_description": intake_output.damage_description,
        "police_report_filed": intake_output.police_report_filed,
        "other_parties_involved": intake_output.other_parties_involved,
        "injuries_reported": intake_output.injuries_reported,
        "intake_complete": intake_output.intake_complete,
        "missing_fields": list(intake_output.missing_fields),
    }
    return (
        "Process the following structured claim intake data and decide the outcome:\n\n"
        + json.dumps(data, indent=2)
    )


def run_intake_actor(
    intake_output: IntakeOutput,
    *,
    pre_issued_tokens: dict[str, CapabilityToken],
    orchestrator_public_key: bytes,
    client: anthropic.Anthropic | None = None,
    audit_fn: AuditFn | None = None,
    session_id: str = "unknown",
) -> IntakeEnvelope:
    """Run the intake actor LLM with P4 capability-token-gated tools.

    pre_issued_tokens: {tool_name: CapabilityToken} issued by the orchestrator.
      Production note: scope={"field": <expected>} for request_more_info narrows
      what field names the LLM may request; scope={} is acceptable for the showcase.
    orchestrator_public_key: 32-byte Ed25519 key for token signature verification.

    Returns IntakeEnvelope.
    Raises anthropic.APIError on API failure (caller handles).
    """
    _client = client or anthropic.Anthropic()
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": _build_user_message(intake_output)}
    ]
    missing_fields: list[str] = []
    terminal_tool: tuple[str, dict[str, Any]] | None = None
    loop_exhausted = False

    for _iteration in range(MAX_LOOP_ITERATIONS):
        response = _client.messages.create(
            model=ACTOR_MODEL,
            max_tokens=_MAX_TOKENS,
            temperature=0,
            system=_SYSTEM_PROMPT,
            tools=_TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results: list[dict[str, Any]] = []

        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue

            tool_name: str = block.name
            tool_input: dict[str, Any] = block.input

            # ── Capability token gate (P4) ────────────────────────────────
            token = pre_issued_tokens.get(tool_name)
            if token is None:
                _audit(
                    agent_id=ACTOR_AGENT_ID,
                    action="tool_call_denied",
                    target=session_id,
                    data_label="CONFIDENTIAL",
                    details={"tool": tool_name, "deny_reason": "no_token_issued"},
                    security_event=True,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Error: no capability token for this tool.",
                    "is_error": True,
                })
                continue

            vr = verify_token(
                token,
                calling_agent_id=ACTOR_AGENT_ID,
                tool=tool_name,
                params=tool_input,
                orchestrator_public_key=orchestrator_public_key,
            )

            if not vr:
                _audit(
                    agent_id=ACTOR_AGENT_ID,
                    action="tool_call_denied",
                    target=session_id,
                    data_label="CONFIDENTIAL",
                    details={"tool": tool_name, "deny_reason": vr.deny_reason.value},
                    security_event=True,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Error: capability token verification failed.",
                    "is_error": True,
                })
                continue
            # ─────────────────────────────────────────────────────────────

            handler = _HANDLERS.get(tool_name)
            if handler is None:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Error: unknown tool.",
                    "is_error": True,
                })
                continue

            result = handler(**tool_input)

            _audit(
                agent_id=ACTOR_AGENT_ID,
                action="tool_call_ok",
                target=session_id,
                data_label="CONFIDENTIAL",
                details={"tool": tool_name},
                security_event=False,
            )

            # Track terminal tools
            if tool_name == "mark_intake_complete" and terminal_tool is None:
                terminal_tool = (tool_name, tool_input)
            elif tool_name == "request_more_info":
                missing_fields.append(tool_input.get("field", "unknown"))
                if terminal_tool is None:
                    terminal_tool = (tool_name, tool_input)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

        if terminal_tool is not None:
            break

    else:
        loop_exhausted = True

    # Determine outcome (deterministic; code decides, not LLM text)
    if terminal_tool is None:
        outcome = "reject_as_out_of_scope"
        structured_summary = None
    elif terminal_tool[0] == "mark_intake_complete":
        outcome = "ready_for_identity"
        structured_summary = terminal_tool[1].get("structured_summary")
    else:
        outcome = "needs_more_info"
        structured_summary = None

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="intake_decision",
        target=session_id,
        data_label="INTERNAL",
        details={"outcome": outcome, "loop_exhausted": loop_exhausted},
        security_event=False,
    )

    return IntakeEnvelope(
        outcome=outcome,
        structured_summary=structured_summary,
        missing_fields=tuple(missing_fields),
        session_id=session_id,
    )
