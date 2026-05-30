"""Claims processor actor (Sprint 4.1).

Task 4.1.6 — run_claims_processor_actor
  LLM-backed actor using Claude Sonnet 4.6 with five capability-token-gated tools:
    - classify_damage(evidence_ref)   → CONFIDENTIAL damage label + confidence
    - lookup_coverage(claim_id)       → CONFIDENTIAL policy/coverage/deductible data
    - score_fraud(claim_id)           → SECRET risk assessment; actor strips SECRET
                                        fields before the result reaches the LLM
    - search_policy_docs(query)       → CONFIDENTIAL RAG retrieval for policy context
    - search_fraud_rules(query)       → SECRET RAG retrieval for fraud rule corpus;
                                        actor strips `text` field from chunks so only
                                        rule references (doc_id, source, score) reach LLM

  P3 / P10 guards for SECRET tools:
    score_fraud: returns SECRET Labeled[dict]; actor sends only {"decision": "CLEAR"|"FLAG"|"DENY"}.
    search_fraud_rules: returns SECRET Labeled[dict]; actor strips chunk `text` fields,
    forwarding only {doc_id, source, score, data_label} per chunk — rule text never
    enters the LLM context or customer output.

  Outcome is deterministic: the ProcessorEnvelope is built from captured tool
  results, not from LLM free text.  The LLM decides which tools to call and in
  what order; the code decides the outcome.

  Termination: loop runs until stop_reason == "end_turn" or MAX_LOOP_ITERATIONS
  is reached.  Fallback: fraud_signal defaults to "FLAG" (fail-closed → ESCALATED)
  if score_fraud was not called.

  Legacy (no-conn) path for unit tests: verify_token() is called directly; tools
  are dispatched without replay-protection.  Pass conn=<psycopg.Connection> for
  the full ToolRegistry path with audit log and replay protection.

Task 2.1.5 — run_claims_processor_stub
  Retained for the Sprint 2.1 vertical slice (test_vertical_slice_e2e.py).
  Hardcoded assessment values; no LLM call.

Public API:
  run_claims_processor_actor(*, claim_id, evidence_ref, pre_issued_tokens,
      orchestrator_public_key, client, audit_fn, session_id, conn)
      -> ProcessorEnvelope

  run_claims_processor_stub(*, claim_id, session_id, audit_fn)
      -> ProcessorEnvelope

ProcessorEnvelope fields map to TransitionGuardContext as follows:
  envelope.damage_assessment    → ctx.damage_assessment
  envelope.coverage_calculation → ctx.coverage_calculation
  envelope.fraud_signal         → ctx.fraud_decision
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

import anthropic
import psycopg

from agent_system.ifc.labels import Labeled
from agent_system.tools.capability_tokens import CapabilityToken, verify_token
from agent_system.tools.implementations.claims_tools import (
    classify_damage,
    lookup_coverage,
    score_fraud,
)
from agent_system.tools.implementations.rag_retrievers import (
    search_fraud_rules,
    search_policy_docs,
)
from agent_system.tools.registry import ToolRegistry

ACTOR_MODEL = "claude-sonnet-4-6"
ACTOR_AGENT_ID = "claims_processor"
MAX_LOOP_ITERATIONS = 8
_MAX_TOKENS = 1024

# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessorEnvelope:
    """Structured assessment output from the claims processor.

    damage_assessment    : damage classification label (maps to ctx.damage_assessment)
    coverage_calculation : coverage determination string (maps to ctx.coverage_calculation)
    fraud_signal         : "CLEAR" | "FLAG" | "DENY" (maps to ctx.fraud_decision)
    claim_id             : claim identifier scoped to this session
    session_id           : session identifier for audit correlation
    """

    damage_assessment: str
    coverage_calculation: str
    fraud_signal: str
    claim_id: str
    session_id: str


# ---------------------------------------------------------------------------
# Stub constants (task 2.1.5 — retained for vertical slice)
# ---------------------------------------------------------------------------

_STUB_DAMAGE_ASSESSMENT = "collision_minor"
_STUB_COVERAGE_CALCULATION = "full_coverage_applicable"
_STUB_FRAUD_SIGNAL = "CLEAR"


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
# Tool definitions for the Anthropic API
# ---------------------------------------------------------------------------

_TOOLS: list[dict[str, Any]] = [
    {
        "name": "classify_damage",
        "description": (
            "Classify vehicle damage from an evidence reference. "
            "Returns: {evidence_ref, damage_label, confidence}."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "evidence_ref": {
                    "type": "string",
                    "description": "Evidence ID (UUID or stable identifier) to classify.",
                },
            },
            "required": ["evidence_ref"],
        },
    },
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
        "name": "score_fraud",
        "description": (
            "Check the fraud risk signal for a claim. "
            "Returns: {decision} where decision is CLEAR, FLAG, or DENY. "
            "No other fields are returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {
                    "type": "string",
                    "description": "Claim ID to score.",
                },
            },
            "required": ["claim_id"],
        },
    },
    {
        "name": "search_policy_docs",
        "description": (
            "Search policy documents for coverage rules and procedures relevant "
            "to this claim. Returns top-n policy excerpts. Use this to retrieve "
            "policy context that informs the coverage determination."
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
    {
        "name": "search_fraud_rules",
        "description": (
            "Search the internal fraud detection rule corpus for rules relevant to "
            "this claim. Returns matched rule references (doc_id, source, score) — "
            "use this to understand which fraud patterns are applicable. "
            "Call this when score_fraud signals FLAG or DENY for additional context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query describing the suspected fraud pattern.",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of rule references to return (default 3).",
                },
            },
            "required": ["query"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the claims processor for a vehicle insurance claims system.
Your task is to produce a structured damage and coverage assessment for the claim.

You MUST call these three tools before finishing:
  1. classify_damage(evidence_ref=<evidence_ref>) — determine the damage category
  2. lookup_coverage(claim_id=<claim_id>)          — determine coverage applicability
  3. score_fraud(claim_id=<claim_id>)              — check the fraud signal

You SHOULD also call:
  4. search_policy_docs(query=<relevant query>)    — retrieve policy context
  5. search_fraud_rules(query=<relevant query>)    — retrieve fraud rule references
     when score_fraud returns FLAG or DENY

After all tool calls complete, output a brief one-sentence rationale.\
"""


# ---------------------------------------------------------------------------
# IFC filter — single chokepoint for SECRET-labelled tool results (P3/P10)
# ---------------------------------------------------------------------------


def _content_for_llm(tool_name: str, raw: Any) -> str:
    """Serialise a tool result to the string sent back to the LLM.

    For score_fraud (SECRET): strip risk_score and risk_factors; send only decision.
    For search_fraud_rules (SECRET): strip chunk `text` fields; send only rule
      references (doc_id, source, score, data_label) — rule text never reaches LLM.
    For all other tools (CONFIDENTIAL): send full inner dict.
    """
    inner = raw.value if isinstance(raw, Labeled) else raw
    if tool_name == "score_fraud":
        return json.dumps({"decision": inner["decision"]})
    if tool_name == "search_fraud_rules":
        safe_chunks = [
            {k: v for k, v in chunk.items() if k != "text"}
            for chunk in inner.get("chunks", [])
        ]
        return json.dumps({"query": inner.get("query"), "n_results": inner.get("n_results"), "chunks": safe_chunks})
    return json.dumps(inner, default=str)


# ---------------------------------------------------------------------------
# Actor — task 4.1.6
# ---------------------------------------------------------------------------


def run_claims_processor_actor(
    *,
    claim_id: str,
    evidence_ref: str,
    pre_issued_tokens: dict[str, CapabilityToken],
    orchestrator_public_key: bytes,
    client: anthropic.Anthropic | None = None,
    audit_fn: AuditFn | None = None,
    session_id: str = "unknown",
    conn: psycopg.Connection | None = None,
) -> ProcessorEnvelope:
    """Run the LLM-backed claims processor actor with P4 capability-token-gated tools.

    pre_issued_tokens: mapping of tool_name → CapabilityToken, issued by the
    orchestrator before calling this function.

    Raises anthropic.APIError on API failure (caller handles).
    """
    _client = client or anthropic.Anthropic()
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    if conn is not None:
        _registry = ToolRegistry()
        _registry.register("classify_damage", classify_damage)
        _registry.register("lookup_coverage", lookup_coverage)
        _registry.register("score_fraud", score_fraud)
        _registry.register("search_policy_docs", search_policy_docs)
        _registry.register("search_fraud_rules", search_fraud_rules)

    _direct_handlers: dict[str, Any] = {
        "classify_damage": classify_damage,
        "lookup_coverage": lookup_coverage,
        "score_fraud": score_fraud,
        "search_policy_docs": search_policy_docs,
        "search_fraud_rules": search_fraud_rules,
    }

    # Collected mandatory tool results (code decides outcome, not LLM text).
    _damage_result: dict | None = None
    _coverage_result: dict | None = None
    _fraud_decision: str | None = None

    user_message = (
        f"Assess claim {claim_id!r} with evidence reference {evidence_ref!r}. "
        f"Call classify_damage, lookup_coverage, and score_fraud, then "
        f"search_policy_docs for relevant policy context."
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
                # Full path: ToolRegistry enforces replay protection and writes
                # tool_call_ok / tool_call_denied to audit_log.
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

                handler = _direct_handlers.get(tool_name)
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

            # Capture structured results for deterministic envelope derivation.
            inner = raw.value if isinstance(raw, Labeled) else raw
            if tool_name == "classify_damage":
                _damage_result = inner
            elif tool_name == "lookup_coverage":
                _coverage_result = inner
            elif tool_name == "score_fraud":
                _fraud_decision = inner["decision"]

            # P3/P10: SECRET filter applied here — single chokepoint.
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": _content_for_llm(tool_name, raw),
            })

        messages.append({"role": "user", "content": tool_results})

    # ── Deterministic outcome from captured tool results ─────────────────
    damage_assessment = (
        _damage_result["damage_label"] if _damage_result is not None else "unknown"
    )

    if _coverage_result is not None:
        pt = _coverage_result["policy_type"].lower()
        applicable = _coverage_result["coverage_applicable"]
        coverage_calculation = f"{pt}_{'applicable' if applicable else 'not_applicable'}"
    else:
        coverage_calculation = "unknown"

    # Fail-closed: default FLAG routes to ESCALATED rather than auto-clearing.
    fraud_signal = _fraud_decision if _fraud_decision is not None else "FLAG"

    envelope = ProcessorEnvelope(
        damage_assessment=damage_assessment,
        coverage_calculation=coverage_calculation,
        fraud_signal=fraud_signal,
        claim_id=claim_id,
        session_id=session_id,
    )

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="processor_assessment",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "damage_assessment": envelope.damage_assessment,
            "fraud_signal": envelope.fraud_signal,
            "stub": False,
        },
        security_event=False,
    )

    return envelope


# ---------------------------------------------------------------------------
# Stub actor — task 2.1.5, retained for vertical slice
# ---------------------------------------------------------------------------


def run_claims_processor_stub(
    *,
    claim_id: str,
    session_id: str = "unknown",
    audit_fn: AuditFn | None = None,
) -> ProcessorEnvelope:
    """Return a hardcoded ProcessorEnvelope and emit a processor_assessment audit event.

    Stub placeholder for Sprint 2.1 vertical slice.  The real LLM-backed actor
    is run_claims_processor_actor (Sprint 4.1, task 4.1.6).
    """
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    envelope = ProcessorEnvelope(
        damage_assessment=_STUB_DAMAGE_ASSESSMENT,
        coverage_calculation=_STUB_COVERAGE_CALCULATION,
        fraud_signal=_STUB_FRAUD_SIGNAL,
        claim_id=claim_id,
        session_id=session_id,
    )

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="processor_assessment",
        target=session_id,
        data_label="CONFIDENTIAL",
        details={
            "claim_id": claim_id,
            "damage_assessment": envelope.damage_assessment,
            "fraud_signal": envelope.fraud_signal,
            "stub": True,
        },
        security_event=False,
    )

    return envelope
