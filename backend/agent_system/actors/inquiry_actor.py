"""Inquiry actor for claim_status, policy_question, and complaint intents (tasks 4.1.8–4.1.9).

Public API:
  run_inquiry_actor(*, claim_id, intent, pre_issued_tokens,
                    orchestrator_public_key, client, audit_fn,
                    session_id, conn, user_text) -> InquiryEnvelope

Design:
  - Model: Claude Haiku 4.5; temperature=0.
  - Intent branching:
      claim_status     → lookup_claim_status tool
      policy_question  → lookup_coverage + search_policy_docs tools
      complaint        → capture_complaint tool
  - P4 gate: orchestrator pre-issues one CapabilityToken per allowed tool.
    Actor never holds the orchestrator private key — trust boundary intact.
  - Loop runs until stop_reason == "end_turn" or MAX_LOOP_ITERATIONS.
    LLM-generated text after tool results is the customer-visible response.
  - P10 egress filter: when conn is not None, response_text passes through
    filter_output(); when conn is None (unit tests), filter is skipped and
    filter_ok defaults to True.
  - Outcome is deterministic: InquiryEnvelope.filter_ok is set by code,
    not inferred from LLM text.  complaint_captured is set by code when
    capture_complaint tool executes successfully.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
import psycopg

from agent_system.egress.filter import filter_output
from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.parser.schemas.intake import ClaimIntent
from agent_system.tools.capability_tokens import CapabilityToken, verify_token
from agent_system.tools.implementations.claims_tools import lookup_coverage
from agent_system.tools.implementations.inquiry_tools import (
    capture_complaint,
    lookup_claim_status,
)
from agent_system.tools.implementations.rag_retrievers import search_policy_docs
from agent_system.tools.registry import ToolRegistry

ACTOR_MODEL = "claude-haiku-4-5-20251001"
ACTOR_AGENT_ID = "claims_processor"
MAX_LOOP_ITERATIONS = 6
_MAX_TOKENS = 1024

_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)

# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InquiryEnvelope:
    """Structured output from the inquiry actor.

    response_text      : customer-visible text (already passed through egress filter).
    claim_id           : claim identifier for this inquiry.
    intent             : ClaimIntent that drove this actor invocation.
    session_id         : session identifier for audit correlation.
    filter_ok          : True if the egress filter passed the response through unchanged
                         (or if conn was None and filter was not applied); False if the
                         filter blocked or modified the output.
    complaint_captured : True if capture_complaint tool executed successfully (complaint
                         intent only); False for all other intents or if tool failed.
                         Signals the orchestrator to trigger IDENTITY_VERIFIED→ESCALATED.
    """

    response_text: str
    claim_id: str
    intent: ClaimIntent
    session_id: str
    filter_ok: bool
    complaint_captured: bool = False


# ---------------------------------------------------------------------------
# AuditFn protocol
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
# Tool definitions per intent
# ---------------------------------------------------------------------------

_TOOLS_CLAIM_STATUS: list[dict[str, Any]] = [
    {
        "name": "lookup_claim_status",
        "description": (
            "Look up the current status of an insurance claim. "
            "Returns: {claim_id, claim_number, claim_stage, incident_type, "
            "incident_date, total_claim_amount}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID to look up.",
                },
            },
            "required": ["claim_id"],
        },
    },
]

_TOOLS_POLICY_QUESTION: list[dict[str, Any]] = [
    {
        "name": "lookup_coverage",
        "description": (
            "Look up policy coverage details for a claim. "
            "Returns: {claim_id, policy_type, coverage_type, deductible, "
            "auto_approve_limit, policy_status, coverage_applicable}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID to look up coverage for.",
                },
            },
            "required": ["claim_id"],
        },
    },
    {
        "name": "search_policy_docs",
        "description": (
            "Search policy documents for coverage rules and procedures. "
            "Use this to find specific policy language to answer the customer's question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query.",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 3).",
                },
            },
            "required": ["query"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompts per intent
# ---------------------------------------------------------------------------

_SYSTEM_CLAIM_STATUS = """\
You are a customer-service agent for a vehicle insurance claims system.
The customer is asking about the current status of their claim.

Call lookup_claim_status with the provided claim_id, then produce a clear,
concise response explaining the claim stage and relevant details.
Do NOT include raw claim_id or internal identifiers in your response.
Keep the response factual and under 200 words.\
"""

_SYSTEM_POLICY_QUESTION = """\
You are a customer-service agent for a vehicle insurance claims system.
The customer has a question about their policy or coverage.

Call lookup_coverage to retrieve the policy details for this claim, and
optionally call search_policy_docs to find relevant policy language.
Produce a clear, concise answer to the customer's policy question.
Do NOT reveal deductible amounts or internal approval limits unless directly
asked. Keep the response factual and under 200 words.\
"""

# ---------------------------------------------------------------------------
# Tool handlers and registries (per intent)
# ---------------------------------------------------------------------------

_TOOLS_COMPLAINT: list[dict[str, Any]] = [
    {
        "name": "capture_complaint",
        "description": (
            "Record a customer complaint and escalate the claim. "
            "Returns: {complaint_id, session_id, category, status: 'ESCALATED'}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier for this complaint.",
                },
                "category": {
                    "type": "string",
                    "enum": ["service", "coverage", "decision", "process", "other"],
                    "description": "Complaint category.",
                },
                "description": {
                    "type": "string",
                    "description": "Customer's complaint description.",
                },
            },
            "required": ["session_id", "category", "description"],
        },
    },
]

_SYSTEM_COMPLAINT = """\
You are a customer-service agent for a vehicle insurance claims system.
The customer wishes to file a complaint.

Call capture_complaint with:
  - session_id: the provided session identifier
  - category: one of service/coverage/decision/process/other (infer from context)
  - description: a concise summary of the customer's complaint

After recording the complaint, provide a clear, empathetic response confirming
the complaint has been escalated and that the customer will be contacted.
Keep the response under 200 words.\
"""

_HANDLERS_CLAIM_STATUS: dict[str, Any] = {
    "lookup_claim_status": lookup_claim_status,
}

_HANDLERS_POLICY_QUESTION: dict[str, Any] = {
    "lookup_coverage": lookup_coverage,
    "search_policy_docs": search_policy_docs,
}

_HANDLERS_COMPLAINT: dict[str, Any] = {
    "capture_complaint": capture_complaint,
}


def _make_registry(handlers: dict[str, Any]) -> ToolRegistry:
    r = ToolRegistry()
    for name, fn in handlers.items():
        r.register(name, fn)
    return r


def _content_for_llm(raw: Any) -> str:
    """Serialise a tool result to the string fed back to the LLM.

    Unwraps Labeled[dict] to its inner dict value before serialisation.
    All inquiry tool results are CONFIDENTIAL — none are SECRET — so no
    field stripping is required (cf. claims_processor _content_for_llm).
    """
    inner = raw.value if isinstance(raw, Labeled) else raw
    return json.dumps(inner, default=str)


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------


def run_inquiry_actor(
    *,
    claim_id: str,
    intent: ClaimIntent,
    pre_issued_tokens: dict[str, CapabilityToken],
    orchestrator_public_key: bytes,
    client: anthropic.Anthropic | None = None,
    audit_fn: AuditFn | None = None,
    session_id: str = "unknown",
    conn: psycopg.Connection | None = None,
    user_text: str | None = None,
) -> InquiryEnvelope:
    """Run the inquiry actor LLM with P4 capability-token-gated tools.

    Handles ClaimIntent.claim_status, ClaimIntent.policy_question, and
    ClaimIntent.complaint.  Raises ValueError for any other intent (new_claim
    and faq are handled elsewhere in the orchestration pipeline).

    pre_issued_tokens: {tool_name: CapabilityToken} issued by the orchestrator.
    orchestrator_public_key: 32-byte Ed25519 key for token signature verification.
    user_text: optional original customer text forwarded by the orchestrator;
               included in the user_message for complaint intent.

    Returns InquiryEnvelope with egress-filtered response_text.
    Raises anthropic.APIError on API failure (caller handles).
    """
    if intent == ClaimIntent.claim_status:
        _tools = _TOOLS_CLAIM_STATUS
        _system = _SYSTEM_CLAIM_STATUS
        _handlers = _HANDLERS_CLAIM_STATUS
    elif intent == ClaimIntent.policy_question:
        _tools = _TOOLS_POLICY_QUESTION
        _system = _SYSTEM_POLICY_QUESTION
        _handlers = _HANDLERS_POLICY_QUESTION
    elif intent == ClaimIntent.complaint:
        _tools = _TOOLS_COMPLAINT
        _system = _SYSTEM_COMPLAINT
        _handlers = _HANDLERS_COMPLAINT
    else:
        raise ValueError(
            f"run_inquiry_actor does not handle intent={intent!r}. "
            "Handled intents: claim_status, policy_question, complaint."
        )

    _client = client or anthropic.Anthropic()
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    if conn is not None:
        _registry = _make_registry(_handlers)

    if intent == ClaimIntent.complaint:
        _complaint_context = f" Customer message: {user_text!r}" if user_text else ""
        user_message = (
            f"The customer wants to file a complaint for session {session_id!r}."
            f"{_complaint_context} "
            f"Call capture_complaint with the appropriate category and description, "
            f"then provide a clear, empathetic confirmation response."
        )
    else:
        user_message = (
            f"The customer is enquiring about claim {claim_id!r}. "
            f"Use the available tool(s) to look up the relevant information, "
            f"then provide a clear, helpful response."
        )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

    last_response: anthropic.types.Message | None = None
    complaint_captured = False

    for _iteration in range(MAX_LOOP_ITERATIONS):
        response = _client.messages.create(
            model=ACTOR_MODEL,
            max_tokens=_MAX_TOKENS,
            temperature=0,
            system=_system,
            tools=_tools,
            messages=messages,
        )
        last_response = response

        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results: list[dict[str, Any]] = []

        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue

            tool_name: str = block.name
            tool_input: dict[str, Any] = block.input

            # ── P4 capability token gate ─────────────────────────────────
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

            if conn is not None:
                invoke_result = _registry.invoke(
                    conn,
                    token=token,
                    calling_agent_id=ACTOR_AGENT_ID,
                    tool_name=tool_name,
                    params=tool_input,
                    orchestrator_public_key=orchestrator_public_key,
                )
                conn.commit()
                if not invoke_result.ok:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Error: capability token verification failed.",
                        "is_error": True,
                    })
                    continue
                raw = invoke_result.value
            else:
                # Legacy path (unit tests; no DB connection).
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

                handler = _handlers.get(tool_name)
                if handler is None:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Error: unknown tool.",
                        "is_error": True,
                    })
                    continue

                raw = handler(**tool_input)
                _audit(
                    agent_id=ACTOR_AGENT_ID,
                    action="tool_call_ok",
                    target=session_id,
                    data_label="CONFIDENTIAL",
                    details={"tool": tool_name},
                    security_event=False,
                )
            # ─────────────────────────────────────────────────────────────

            if tool_name == "capture_complaint":
                complaint_captured = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": _content_for_llm(raw),
            })

        messages.append({"role": "user", "content": tool_results})

    # ── Extract LLM-generated response text ─────────────────────────────────
    response_text = ""
    if last_response is not None:
        for block in last_response.content:
            if getattr(block, "type", None) == "text":
                response_text += block.text

    if not response_text:
        response_text = "Unable to retrieve the requested information at this time."

    # ── P10 egress filter ────────────────────────────────────────────────────
    filter_ok = True
    if conn is not None:
        fr = filter_output(
            conn,
            text=response_text,
            source_label=_LABEL_CONFIDENTIAL,
            calling_agent_id=ACTOR_AGENT_ID,
        )
        conn.commit()
        filter_ok = fr.ok
        response_text = fr.output

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="inquiry_response",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "intent": intent.value,
            "filter_ok": filter_ok,
            "response_length": len(response_text),
        },
        security_event=False,
    )

    return InquiryEnvelope(
        response_text=response_text,
        claim_id=claim_id,
        intent=intent,
        session_id=session_id,
        filter_ok=filter_ok,
        complaint_captured=complaint_captured,
    )
