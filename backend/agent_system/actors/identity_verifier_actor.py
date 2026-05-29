"""Identity verifier actor (P1/P3/P4 — task 2.1.4).

Public API:
  run_identity_verifier_actor(
      *, policy_number, dob_hint, ssn_last4,
      pre_issued_tokens, orchestrator_public_key,
      identity_check_fn, client, audit_fn, session_id,
  ) -> IdentityEnvelope

Design:
  - Model: Claude Haiku 4.5; temperature=0.
  - Single tool: request_identity_check(policy_number, dob_hint, ssn_last4) →
    {verified, attempts_remaining}.  Tool is terminal; loop breaks on first call.
  - P3 label: data_label="PERSONAL" for all tool-call audits (TAD §2.3.2).
    The boolean result is the only PII-adjacent data that enters the LLM context.
    Stored vault PII never surfaces.
  - P4 gate: pre_issued_tokens + orchestrator_public_key; actor never holds the
    orchestrator private key.
  - identity_check_fn defaults to a RuntimeError stub — callers MUST wire the real
    verify_identity() wrapper in production; tests inject mocks.
  - Outcome mapped deterministically from VerifyResult.outcome (code, not LLM text):
      SUCCESS   → "identity_verified"
      LOCKOUT   → "identity_locked_out"
      otherwise → "identity_failed"
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol

import anthropic

from agent_system.tools.capability_tokens import CapabilityToken, verify_token

ACTOR_MODEL = "claude-haiku-4-5-20251001"
ACTOR_AGENT_ID = "identity_verifier"
MAX_LOOP_ITERATIONS = 4
_MAX_TOKENS = 512

_TOOL_NAME = "request_identity_check"


# ---------------------------------------------------------------------------
# Output envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IdentityEnvelope:
    """Structured output produced by the identity verifier actor.

    outcome:
      "identity_verified"    — SUCCESS from the vault
      "identity_failed"      — FAIL_MATCH or NOT_FOUND; attempts may remain
      "identity_locked_out"  — LOCKOUT; session exhausted
    """

    outcome: str
    attempts_remaining: int
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
# Tool definition
# ---------------------------------------------------------------------------


_TOOLS: list[dict[str, Any]] = [
    {
        "name": _TOOL_NAME,
        "description": (
            "Submit the customer's identity credentials for server-side verification. "
            "The server compares them to the secure vault — raw vault values are never "
            "returned. Result: {verified, attempts_remaining}. "
            "Call exactly once with the credentials provided in the task."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "policy_number": {
                    "type": "string",
                    "description": "Customer's policy number.",
                },
                "dob_hint": {
                    "type": "string",
                    "description": "Customer's date of birth in ISO format (YYYY-MM-DD).",
                },
                "ssn_last4": {
                    "type": "string",
                    "description": "Last 4 digits of the customer's SSN.",
                },
            },
            "required": ["policy_number", "dob_hint", "ssn_last4"],
        },
    }
]


# ---------------------------------------------------------------------------
# Default identity_check_fn — loud failure if not wired
# ---------------------------------------------------------------------------


def _unwired_identity_check_fn(
    policy_number: str, dob_hint: str, ssn_last4: str
) -> dict[str, Any]:
    raise RuntimeError(
        "identity_check_fn not wired — pass a real verify_identity() wrapper "
        "via the identity_check_fn parameter in production."
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


_SYSTEM_PROMPT = """\
You are the identity verifier for a vehicle insurance claims system.
Your sole task is to call request_identity_check exactly once using the credentials provided.
Do not reason about, echo, or store the raw credentials beyond forwarding them to the tool.
The tool returns only {verified, attempts_remaining} — you never see stored vault data.
You MUST call request_identity_check before finishing.\
"""


# ---------------------------------------------------------------------------
# Actor
# ---------------------------------------------------------------------------


def _build_user_message(policy_number: str, dob_hint: str, ssn_last4: str) -> str:
    return (
        "Verify the customer's identity using the following provided credentials:\n\n"
        + json.dumps(
            {"policy_number": policy_number, "dob_hint": dob_hint, "ssn_last4": ssn_last4},
            indent=2,
        )
    )


def run_identity_verifier_actor(
    *,
    policy_number: str,
    dob_hint: str,
    ssn_last4: str,
    pre_issued_tokens: dict[str, CapabilityToken],
    orchestrator_public_key: bytes,
    identity_check_fn: Callable[[str, str, str], dict[str, Any]] | None = None,
    client: anthropic.Anthropic | None = None,
    audit_fn: AuditFn | None = None,
    session_id: str = "unknown",
) -> IdentityEnvelope:
    """Run the identity verifier actor with P4 capability-token-gated tool.

    identity_check_fn(policy_number, dob_hint, ssn_last4) -> dict with keys:
      verified: bool
      outcome: str  — "SUCCESS" | "FAIL_MATCH" | "LOCKOUT" | "NOT_FOUND"
      attempts_remaining: int

    Defaults to a RuntimeError stub; callers must wire the real vault wrapper.
    Raises anthropic.APIError on API failure (caller handles).
    """
    _client = client or anthropic.Anthropic()
    _audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]
    _check_fn = identity_check_fn if identity_check_fn is not None else _unwired_identity_check_fn

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": _build_user_message(policy_number, dob_hint, ssn_last4)}
    ]
    check_result: dict[str, Any] | None = None

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
                    data_label="PERSONAL",
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
                    data_label="PERSONAL",
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

            if tool_name != _TOOL_NAME:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Error: unknown tool.",
                    "is_error": True,
                })
                continue

            raw = _check_fn(
                tool_input["policy_number"],
                tool_input["dob_hint"],
                tool_input["ssn_last4"],
            )
            check_result = raw

            _audit(
                agent_id=ACTOR_AGENT_ID,
                action="tool_call_ok",
                target=session_id,
                data_label="PERSONAL",
                details={"tool": tool_name, "verified": raw.get("verified")},
                security_event=False,
            )

            # Return only the boolean signal to the LLM — never vault data
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps({
                    "verified": raw.get("verified"),
                    "attempts_remaining": raw.get("attempts_remaining", 0),
                }),
            })
            # Terminal: break inner loop and outer loop
            break

        messages.append({"role": "user", "content": tool_results})

        if check_result is not None:
            break

    # ── Outcome (deterministic; code decides, not LLM text) ──────────────
    if check_result is None:
        outcome = "identity_failed"
        attempts_remaining = 0
    elif check_result.get("outcome") == "SUCCESS":
        outcome = "identity_verified"
        attempts_remaining = check_result.get("attempts_remaining", 0)
    elif check_result.get("outcome") == "LOCKOUT":
        outcome = "identity_locked_out"
        attempts_remaining = 0
    else:
        outcome = "identity_failed"
        attempts_remaining = check_result.get("attempts_remaining", 0)

    _audit(
        agent_id=ACTOR_AGENT_ID,
        action="identity_decision",
        target=session_id,
        data_label="INTERNAL",
        details={"outcome": outcome, "attempts_remaining": attempts_remaining},
        security_event=False,
    )

    return IdentityEnvelope(
        outcome=outcome,
        attempts_remaining=attempts_remaining,
        session_id=session_id,
    )
