"""Settlement actor (Sprint 4.2).

Task 4.2.3 — run_settlement_actor
  LLM-backed actor using Claude Sonnet 4.6 with three capability-token-gated tools:
    - calculate_settlement(claim_id)  → CONFIDENTIAL amounts + auto-approve limit
    - request_payout(claim_id)        → CONFIDENTIAL payout confirmation (conn required)
    - draft_summary(claim_id, outcome, offered_amount, payout_reference)
                                      → CONFIDENTIAL customer-facing text

  P10 egress filter applied to draft_summary output before it enters
  SettlementEnvelope.summary.  If the filter blocks (PII / URL / SECRET),
  envelope.summary is set to REFUSAL_MESSAGE and payout_status to "escalated".

  Legacy path (conn=None): request_payout is unavailable; the actor always
  produces payout_status="escalated" on this path.

Task 2.1.6 — run_settlement_actor_stub
  Retained for the Sprint 2.1 vertical slice (test_vertical_slice_e2e.py).
  Hardcoded assessment values; no LLM call.

Public API:
  run_settlement_actor(*, claim_id, pre_issued_tokens, orchestrator_public_key,
      client, audit_fn, session_id, conn, trace_id) -> SettlementEnvelope

  run_settlement_actor_stub(*, claim_id, session_id, audit_fn) -> SettlementEnvelope

SettlementEnvelope.settlement_amount maps to TransitionGuardContext.settlement_amount.
"""
from __future__ import annotations

import functools
import json
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
import psycopg

from agent_system.egress.filter import REFUSAL_MESSAGE, filter_output
from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.tools.capability_tokens import CapabilityToken, verify_token
from agent_system.tools.implementations.settlement_tools import (
    calculate_settlement,
    draft_summary,
    request_payout,
)
from agent_system.tools.registry import ToolRegistry

ACTOR_AGENT_ID = "settlement_actor"
ACTOR_MODEL = "claude-sonnet-4-6"
MAX_LOOP_ITERATIONS = 8
_MAX_TOKENS = 1024

_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)

# ---------------------------------------------------------------------------
# Tool definitions for the Anthropic API — task 4.2.3
# ---------------------------------------------------------------------------

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "calculate_settlement",
        "description": (
            "Calculate the settlement amount for a claim. "
            "Returns: {claim_id, raw_claim_amount, deductible_applied, "
            "offered_amount, auto_approve_limit}. "
            "Compare offered_amount with auto_approve_limit to determine "
            "SETTLED (<=) vs ESCALATED (>) path."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID to calculate settlement for.",
                },
            },
            "required": ["claim_id"],
        },
    },
    {
        "name": "request_payout",
        "description": (
            "Initiate a payout for an approved claim. "
            "Call only if offered_amount <= auto_approve_limit (SETTLED path). "
            "Returns: {claim_id, payout_status, payout_reference, offered_amount}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID to pay out.",
                },
            },
            "required": ["claim_id"],
        },
    },
    {
        "name": "draft_summary",
        "description": (
            "Generate a customer-facing settlement summary. "
            "Must be called after the settlement path is determined. "
            "Returns: {claim_id, outcome, offered_amount, payout_reference, summary}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID.",
                },
                "outcome": {
                    "type": "string",
                    "description": "'SETTLED' or 'ESCALATED'.",
                },
                "offered_amount": {
                    "type": "number",
                    "description": "Approved payout amount (0.0 if ESCALATED).",
                },
                "payout_reference": {
                    "type": "string",
                    "description": "UUID from request_payout (empty string if ESCALATED).",
                },
            },
            "required": ["claim_id", "outcome", "offered_amount", "payout_reference"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt — task 4.2.3
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the settlement actor for a vehicle insurance claims system.
Your task is to calculate and process the settlement for the claim.

Follow these steps in order:
  1. Call calculate_settlement(claim_id=<claim_id>) to get offered_amount and auto_approve_limit.
  2. If offered_amount <= auto_approve_limit: call request_payout(claim_id=<claim_id>) — outcome is SETTLED.
     Otherwise: skip request_payout — outcome is ESCALATED.
  3. Call draft_summary(claim_id=<claim_id>, outcome=<"SETTLED" or "ESCALATED">,
     offered_amount=<offered_amount from step 1>,
     payout_reference=<payout_reference from step 2, or "" if ESCALATED>).

After all tool calls complete, output a brief one-sentence rationale.\
"""

# Hardcoded stub values.
_STUB_SETTLEMENT_AMOUNT: float = 4_500.0   # within the 10,000 auto_approve_limit
_STUB_PAYOUT_STATUS = "approved"
_STUB_SUMMARY = (
    "Stub settlement: collision claim approved for $4,500.00 under full coverage. "
    "Payment will be processed to the account on file within 5–7 business days."
)


# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettlementEnvelope:
    """Structured output from the settlement actor.

    settlement_amount : approved payout amount (maps to ctx.settlement_amount)
    payout_status     : "approved" | "pending_payout" | "escalated"
    summary           : customer-facing settlement summary (egress-filtered before display)
    claim_id          : claim identifier scoped to this session
    session_id        : session identifier for audit correlation
    """

    settlement_amount: float
    payout_status: str
    summary: str
    claim_id: str
    session_id: str


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
# Actor — task 4.2.3
# ---------------------------------------------------------------------------


def run_settlement_actor(
    *,
    claim_id: str,
    pre_issued_tokens: dict[str, CapabilityToken],
    orchestrator_public_key: bytes,
    client: anthropic.Anthropic | None = None,
    audit_fn: AuditFn | None = None,
    session_id: str = "unknown",
    conn: psycopg.Connection | None = None,
    trace_id: uuid.UUID | None = None,
) -> SettlementEnvelope:
    """Run the LLM-backed settlement actor with P4 + P10 guards.

    pre_issued_tokens: mapping of tool_name → CapabilityToken, issued by orchestrator.
    conn:              DB connection for ToolRegistry replay-protection + egress filter.
                       Pass None for the legacy path (unit tests without DB).

    Raises anthropic.APIError on API failure (caller handles).
    """
    _client = client or anthropic.Anthropic()
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    if conn is not None:
        _registry = ToolRegistry()
        _registry.register("calculate_settlement", calculate_settlement)
        _registry.register("request_payout", functools.partial(request_payout, conn=conn))
        _registry.register("draft_summary", draft_summary)

    _direct_handlers: dict[str, Any] = {
        "calculate_settlement": calculate_settlement,
        "draft_summary": draft_summary,
        # request_payout omitted: requires conn; not available on legacy path
    }

    _settlement_result: dict | None = None
    _payout_result: dict | None = None
    _summary_result: dict | None = None

    user_message = (
        f"Process the settlement for claim {claim_id!r}. "
        "Call calculate_settlement, then request_payout if within the auto-approve limit, "
        "then draft_summary."
    )
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

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

            # ── P4 capability token gate ──────────────────────────────────────
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
                    trace_id=trace_id,
                )
                conn.commit()
                if not invoke_result.ok:
                    if invoke_result.handler_error is not None:
                        error_msg = str(invoke_result.handler_error)
                    else:
                        error_msg = "capability token verification failed"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error: {error_msg}",
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

                handler = _direct_handlers.get(tool_name)
                if handler is None:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Error: tool not available in this context.",
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
            # ─────────────────────────────────────────────────────────────────

            # Capture structured results for deterministic envelope derivation.
            inner = raw.value if isinstance(raw, Labeled) else raw
            if tool_name == "calculate_settlement":
                _settlement_result = inner
            elif tool_name == "request_payout":
                _payout_result = inner
            elif tool_name == "draft_summary":
                _summary_result = inner

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(inner, default=str),
            })

        messages.append({"role": "user", "content": tool_results})

    # ── Deterministic outcome from captured tool results ──────────────────────
    if _payout_result is not None:
        payout_status = "approved"
        offered_amount = float(_payout_result["offered_amount"])
    elif _settlement_result is not None:
        payout_status = "escalated"
        offered_amount = float(_settlement_result["offered_amount"])
    else:
        payout_status = "escalated"
        offered_amount = 0.0

    raw_summary = (
        _summary_result["summary"]
        if _summary_result is not None
        else "Settlement processing complete."
    )

    # ── P10 egress filter on customer-visible summary ─────────────────────────
    if conn is not None:
        fr = filter_output(
            conn,
            text=raw_summary,
            source_label=_LABEL_CONFIDENTIAL,
            calling_agent_id=ACTOR_AGENT_ID,
            trace_id=trace_id,
        )
        conn.commit()
        final_summary = fr.output
        if not fr.ok:
            payout_status = "escalated"
    else:
        final_summary = raw_summary

    envelope = SettlementEnvelope(
        settlement_amount=offered_amount,
        payout_status=payout_status,
        summary=final_summary,
        claim_id=claim_id,
        session_id=session_id,
    )

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="settlement_issued",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "offered_amount": offered_amount,
            "payout_status": payout_status,
            "stub": False,
        },
        security_event=False,
    )

    return envelope


# ---------------------------------------------------------------------------
# Stub actor — task 2.1.6, retained for vertical slice
# ---------------------------------------------------------------------------


def run_settlement_actor_stub(
    *,
    claim_id: str,
    session_id: str = "unknown",
    audit_fn: AuditFn | None = None,
) -> SettlementEnvelope:
    """Return a hardcoded SettlementEnvelope and emit a settlement_issued audit event.

    Stub placeholder for Sprint 2.1 vertical slice.  Replace with the real
    LLM-backed actor in Sprint 4.1.
    """
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    envelope = SettlementEnvelope(
        settlement_amount=_STUB_SETTLEMENT_AMOUNT,
        payout_status=_STUB_PAYOUT_STATUS,
        summary=_STUB_SUMMARY,
        claim_id=claim_id,
        session_id=session_id,
    )

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="settlement_issued",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "settlement_amount": envelope.settlement_amount,
            "payout_status": envelope.payout_status,
            "stub": True,
        },
        security_event=False,
    )

    return envelope
