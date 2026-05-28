"""Per-session token and tool-call budget enforcement (P11 — task 1.3.5).

Public API:
  consume_tokens(budget, n, config)         — raises BudgetExceededError on overflow
  consume_tool_call(budget, agent_id, config) — raises BudgetExceededError on overflow

Both functions mutate *budget* in place.  Once halted, all further calls raise
immediately regardless of the n/agent_id argument.

BudgetExceededError.kind is "tokens" or "tool_calls" — used by the Orchestrator
to emit a structured security audit event.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_MAX_SESSION_TOKENS: int = 50_000
DEFAULT_MAX_TOOL_CALLS_PER_AGENT: int = 20


@dataclass
class BudgetConfig:
    """Hard caps for a session.  Passed once at Orchestrator construction."""

    max_session_tokens: int = DEFAULT_MAX_SESSION_TOKENS
    max_tool_calls_per_agent: int = DEFAULT_MAX_TOOL_CALLS_PER_AGENT


@dataclass
class SessionBudget:
    """Mutable counters for one claim session.

    All fields are public so callers can inspect current usage, but mutations
    should happen exclusively through consume_tokens() and consume_tool_call().
    """

    session_id: str
    tokens_used: int = 0
    tool_calls: dict[str, int] = field(default_factory=dict)
    halted: bool = False


class BudgetExceededError(Exception):
    """Raised when a budget cap is breached.

    Carries *kind* ("tokens" or "tool_calls") and *agent_id* (None for token
    overflows) for structured audit logging.
    """

    def __init__(self, message: str, kind: str, agent_id: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.agent_id = agent_id


def consume_tokens(
    budget: SessionBudget,
    n: int,
    config: BudgetConfig,
) -> None:
    """Increment token counter by *n*.

    Raises BudgetExceededError (kind="tokens") if the session is already halted
    or if the new total exceeds config.max_session_tokens.  Sets budget.halted
    before raising.
    """
    if budget.halted:
        raise BudgetExceededError(
            f"Session {budget.session_id!r} is halted; rejecting {n} tokens",
            kind="tokens",
        )
    budget.tokens_used += n
    if budget.tokens_used > config.max_session_tokens:
        budget.halted = True
        raise BudgetExceededError(
            f"Session {budget.session_id!r} token budget exceeded: "
            f"{budget.tokens_used} > {config.max_session_tokens}",
            kind="tokens",
        )


def consume_tool_call(
    budget: SessionBudget,
    agent_id: str,
    config: BudgetConfig,
) -> None:
    """Increment the per-agent tool-call counter for *agent_id*.

    Raises BudgetExceededError (kind="tool_calls") if the session is already
    halted or if the agent's count exceeds config.max_tool_calls_per_agent.
    Sets budget.halted before raising.
    """
    if budget.halted:
        raise BudgetExceededError(
            f"Session {budget.session_id!r} is halted; rejecting tool call for {agent_id!r}",
            kind="tool_calls",
            agent_id=agent_id,
        )
    budget.tool_calls[agent_id] = budget.tool_calls.get(agent_id, 0) + 1
    if budget.tool_calls[agent_id] > config.max_tool_calls_per_agent:
        budget.halted = True
        raise BudgetExceededError(
            f"Agent {agent_id!r} tool-call budget exceeded in session {budget.session_id!r}: "
            f"{budget.tool_calls[agent_id]} > {config.max_tool_calls_per_agent}",
            kind="tool_calls",
            agent_id=agent_id,
        )
