"""Orchestrator — ties state machine, budget enforcement, and audit together (P2, P11 — task 1.3.5).

Public API:
  Orchestrator(session_id, *, initial_stage, budget_config, audit_fn)
  .request_transition(to_stage, ctx) -> ClaimStage
  .record_token_use(n)
  .record_tool_call(agent_id)

All three methods audit their outcomes.  Violation or budget-exceeded events are
emitted as security_event=True before the exception propagates to the caller.
"""
from __future__ import annotations

from typing import Protocol

from agent_system.orchestrator.budgets import (
    BudgetConfig,
    BudgetExceededError,
    SessionBudget,
    consume_tokens,
    consume_tool_call,
)
from agent_system.orchestrator.intent_routing import IntentRoute, dispatch_intent
from agent_system.orchestrator.transitions import (
    ClaimStage,
    TransitionGuardContext,
    TransitionViolationError,
    advance_stage,
)
from agent_system.parser.schemas.intake import ClaimIntent


class AuditFn(Protocol):
    """Matches the kwargs accepted by audit.chain.append_log()."""

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
    """Default audit function — silently discards events (tests / standalone use)."""


class Orchestrator:
    """Single-session deterministic orchestrator.

    Thread-safety: not thread-safe.  One Orchestrator instance per session,
    called from a single async coroutine at a time.
    """

    AGENT_ID = "orchestrator"

    def __init__(
        self,
        session_id: str,
        *,
        initial_stage: ClaimStage = ClaimStage.INTAKE,
        budget_config: BudgetConfig | None = None,
        audit_fn: AuditFn | None = None,
    ) -> None:
        self._session_id = session_id
        self._stage = initial_stage
        self._budget = SessionBudget(session_id=session_id)
        self._budget_config = budget_config or BudgetConfig()
        self._audit: AuditFn = audit_fn if audit_fn is not None else _noop_audit  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def stage(self) -> ClaimStage:
        return self._stage

    @property
    def budget(self) -> SessionBudget:
        return self._budget

    @property
    def session_id(self) -> str:
        return self._session_id

    # ------------------------------------------------------------------
    # Mutating operations
    # ------------------------------------------------------------------

    def request_transition(
        self,
        to_stage: ClaimStage,
        ctx: TransitionGuardContext,
    ) -> ClaimStage:
        """Attempt to advance from the current stage to *to_stage*.

        On success: updates internal stage, emits stage_transition audit event,
        returns the new stage.
        On failure: emits transition_violation security audit event, re-raises
        TransitionViolationError.
        """
        try:
            new_stage = advance_stage(self._stage, to_stage, ctx)
        except TransitionViolationError as exc:
            self._audit(
                agent_id=self.AGENT_ID,
                action="transition_violation",
                target=self._session_id,
                data_label="INTERNAL",
                details={
                    "from_stage": exc.from_stage.value,
                    "to_stage": exc.to_stage.value,
                    "reason": str(exc),
                },
                security_event=True,
            )
            raise

        self._stage = new_stage
        self._audit(
            agent_id=self.AGENT_ID,
            action="stage_transition",
            target=self._session_id,
            data_label="INTERNAL",
            details={"to_stage": new_stage.value},
            security_event=False,
        )
        return new_stage

    def record_token_use(self, n: int) -> None:
        """Charge *n* tokens against the session budget.

        On excess: emits budget_exceeded security audit event, re-raises
        BudgetExceededError.
        """
        try:
            consume_tokens(self._budget, n, self._budget_config)
        except BudgetExceededError as exc:
            self._audit(
                agent_id=self.AGENT_ID,
                action="budget_exceeded",
                target=self._session_id,
                data_label="INTERNAL",
                details={
                    "kind": exc.kind,
                    "tokens_used": self._budget.tokens_used,
                    "max_session_tokens": self._budget_config.max_session_tokens,
                },
                security_event=True,
            )
            raise

    def dispatch_on_intent(self, intent: ClaimIntent) -> IntentRoute:
        """Route *intent* to an IntentRoute and emit an intent_routed audit event."""
        route = dispatch_intent(intent)
        self._audit(
            agent_id=self.AGENT_ID,
            action="intent_routed",
            target=self._session_id,
            data_label="INTERNAL",
            details={"intent": intent.value, "route": route.value},
            security_event=False,
        )
        return route

    def record_tool_call(self, agent_id: str) -> None:
        """Charge one tool call against *agent_id*'s budget.

        On excess: emits budget_exceeded security audit event, re-raises
        BudgetExceededError.
        """
        try:
            consume_tool_call(self._budget, agent_id, self._budget_config)
        except BudgetExceededError as exc:
            self._audit(
                agent_id=self.AGENT_ID,
                action="budget_exceeded",
                target=self._session_id,
                data_label="INTERNAL",
                details={
                    "kind": exc.kind,
                    "agent_id": agent_id,
                    "tool_calls": self._budget.tool_calls.get(agent_id),
                    "max_tool_calls_per_agent": self._budget_config.max_tool_calls_per_agent,
                },
                security_event=True,
            )
            raise
