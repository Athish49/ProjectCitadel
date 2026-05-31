"""Exhaustive BFS model-checker for workflow.tla — Sprint 5.2.2.

Verifies all reachable states against four invariants derived from the spec:
  TypeOK           — all variables stay in their declared domains
  ClosedIsAbsorbing — stage="CLOSED" never transitions to a different stage
  ForwardProgress  — every stage change strictly increases topological rank
  EventualClosure  — every reachable state can reach stage="CLOSED"

Run standalone:
  python formal/check_spec.py

Import in tests:
  from formal.check_spec import check_spec, INIT, RANK, STAGES, WorkflowState
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace

# ---------------------------------------------------------------------------
# Value domains  (mirrors workflow.tla constants)
# ---------------------------------------------------------------------------

STAGES: frozenset[str] = frozenset({
    "INTAKE",
    "IDENTITY_PENDING",
    "IDENTITY_VERIFIED",
    "PROCESSING",
    "DECIDED",
    "SETTLED",
    "ESCALATED",
    "DENIED",
    "CLOSED",
})

FRAUD_DECISIONS: frozenset[str] = frozenset({"NONE", "CLEAR", "FLAG", "DENY"})
AMOUNT_DOMAIN: frozenset[int] = frozenset({0, 10_000, 15_000})
AUTO_APPROVE_LIMIT: int = 10_000

# Topological rank — co-terminal stages (SETTLED / ESCALATED / DENIED) share rank 5.
RANK: dict[str, int] = {
    "INTAKE": 0,
    "IDENTITY_PENDING": 1,
    "IDENTITY_VERIFIED": 2,
    "PROCESSING": 3,
    "DECIDED": 4,
    "SETTLED": 5,
    "ESCALATED": 5,
    "DENIED": 5,
    "CLOSED": 6,
}

# ---------------------------------------------------------------------------
# State representation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowState:
    stage: str
    intake_complete: bool
    identity_verified: bool
    damage_assessed: bool
    coverage_calculated: bool
    complaint_captured: bool
    fraud_decision: str   # "NONE" | "CLEAR" | "FLAG" | "DENY"
    settlement_amount: int  # 0 = unset; 10_000 | 15_000 = proposed


INIT = WorkflowState(
    stage="INTAKE",
    intake_complete=False,
    identity_verified=False,
    damage_assessed=False,
    coverage_calculated=False,
    complaint_captured=False,
    fraud_decision="NONE",
    settlement_amount=0,
)

# ---------------------------------------------------------------------------
# Transition system  (mirrors Next in workflow.tla)
# ---------------------------------------------------------------------------


def successors(s: WorkflowState) -> list[WorkflowState]:
    """Return every state reachable from *s* in one step."""
    out: list[WorkflowState] = []

    # ── Workflow transitions (11 edges from _VALID_EDGES) ─────────────────

    if s.stage == "INTAKE" and s.intake_complete:
        out.append(replace(s, stage="IDENTITY_PENDING"))

    if s.stage == "IDENTITY_PENDING" and s.identity_verified:
        out.append(replace(s, stage="IDENTITY_VERIFIED"))

    if s.stage == "IDENTITY_VERIFIED":
        out.append(replace(s, stage="PROCESSING"))
        if s.complaint_captured:
            out.append(replace(s, stage="ESCALATED"))

    if (
        s.stage == "PROCESSING"
        and s.damage_assessed
        and s.coverage_calculated
        and s.fraud_decision != "NONE"
    ):
        out.append(replace(s, stage="DECIDED"))

    if s.stage == "DECIDED":
        if (
            s.fraud_decision == "CLEAR"
            and s.settlement_amount > 0
            and s.settlement_amount <= AUTO_APPROVE_LIMIT
        ):
            out.append(replace(s, stage="SETTLED"))
        if s.fraud_decision in {"FLAG", "DENY"} or s.settlement_amount > AUTO_APPROVE_LIMIT:
            out.append(replace(s, stage="ESCALATED"))
        out.append(replace(s, stage="DENIED"))  # admin override — always enabled

    if s.stage == "SETTLED":
        out.append(replace(s, stage="CLOSED"))
    if s.stage == "ESCALATED":
        out.append(replace(s, stage="CLOSED"))
    if s.stage == "DENIED":
        out.append(replace(s, stage="CLOSED"))

    # ── Environment actions (monotonic setters) ───────────────────────────

    if not s.intake_complete:
        out.append(replace(s, intake_complete=True))
    if not s.identity_verified:
        out.append(replace(s, identity_verified=True))
    if not s.damage_assessed:
        out.append(replace(s, damage_assessed=True))
    if not s.coverage_calculated:
        out.append(replace(s, coverage_calculated=True))
    if not s.complaint_captured:
        out.append(replace(s, complaint_captured=True))
    if s.fraud_decision == "NONE":
        for d in ("CLEAR", "FLAG", "DENY"):
            out.append(replace(s, fraud_decision=d))
    if s.settlement_amount == 0:
        for a in (10_000, 15_000):
            out.append(replace(s, settlement_amount=a))

    return out


# ---------------------------------------------------------------------------
# Per-transition invariant checks
# ---------------------------------------------------------------------------


def check_type_ok(s: WorkflowState) -> str | None:
    if s.stage not in STAGES:
        return f"stage {s.stage!r} ∉ STAGES"
    if s.fraud_decision not in FRAUD_DECISIONS:
        return f"fraud_decision {s.fraud_decision!r} ∉ FRAUD_DECISIONS"
    if s.settlement_amount not in AMOUNT_DOMAIN:
        return f"settlement_amount {s.settlement_amount} ∉ AMOUNT_DOMAIN"
    return None


def check_closed_is_absorbing(s: WorkflowState, s2: WorkflowState) -> str | None:
    if s.stage == "CLOSED" and s2.stage != "CLOSED":
        return f"ClosedIsAbsorbing violated: CLOSED → {s2.stage}"
    return None


def check_forward_progress(s: WorkflowState, s2: WorkflowState) -> str | None:
    if s.stage != s2.stage and RANK[s2.stage] <= RANK[s.stage]:
        return (
            f"ForwardProgress violated: {s.stage}(rank {RANK[s.stage]}) "
            f"→ {s2.stage}(rank {RANK[s2.stage]})"
        )
    return None


# ---------------------------------------------------------------------------
# Main BFS checker
# ---------------------------------------------------------------------------


def check_spec() -> dict:
    """BFS over the full reachable state space; returns a result dict.

    Keys:
        visited      (int)           — number of reachable states
        violations   (list[str])     — empty iff all invariants hold
        stages_seen  (frozenset[str])— every stage that appears in the space
    """
    visited: set[WorkflowState] = {INIT}
    queue: deque[WorkflowState] = deque([INIT])
    violations: list[str] = []

    # Reverse graph for EventualClosure backward BFS.
    reverse: dict[WorkflowState, set[WorkflowState]] = defaultdict(set)

    while queue:
        s = queue.popleft()

        if err := check_type_ok(s):
            violations.append(err)

        for s2 in successors(s):
            if err := check_closed_is_absorbing(s, s2):
                violations.append(err)
            if err := check_forward_progress(s, s2):
                violations.append(err)

            reverse[s2].add(s)

            if s2 not in visited:
                visited.add(s2)
                queue.append(s2)

    # EventualClosure: backward BFS from every CLOSED state.
    can_reach_closed: set[WorkflowState] = set()
    bfs: deque[WorkflowState] = deque()
    for s in visited:
        if s.stage == "CLOSED":
            can_reach_closed.add(s)
            bfs.append(s)
    while bfs:
        s = bfs.popleft()
        for pred in reverse[s]:
            if pred not in can_reach_closed:
                can_reach_closed.add(pred)
                bfs.append(pred)

    for s in visited - can_reach_closed:
        violations.append(
            f"EventualClosure violated: {s.stage} "
            f"(fraud={s.fraud_decision}, amt={s.settlement_amount}) "
            "cannot reach CLOSED"
        )

    return {
        "visited": len(visited),
        "violations": violations,
        "stages_seen": frozenset(s.stage for s in visited),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = check_spec()
    print(f"States explored : {result['visited']}")
    print(f"Stages reached  : {sorted(result['stages_seen'])}")
    if result["violations"]:
        print(f"\nVIOLATIONS ({len(result['violations'])}):")
        for v in result["violations"]:
            print(f"  ✗ {v}")
        raise SystemExit(1)
    print("\nAll invariants hold.")
