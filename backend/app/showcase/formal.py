"""Formal verification endpoint — runs the BFS model checker on demand."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter
from pydantic import BaseModel

from formal.check_spec import check_spec

router = APIRouter(prefix="/formal", tags=["formal"])

_INVARIANT_NAMES = (
    "TypeOK",
    "ClosedIsAbsorbing",
    "ForwardProgress",
    "EventualClosure",
    "MonotonicFlags",
    "FraudDecisionFinal",
    "SettlementAmountFinal",
)


class RunCheckResult(BaseModel):
    visited: int
    violations: list[str]
    stages_seen: list[str]
    elapsed_ms: float
    all_hold: bool
    invariant_results: dict[str, bool]


@router.get("/run-check", response_model=RunCheckResult)
async def run_check() -> RunCheckResult:
    """BFS-enumerate all reachable states and verify all 7 invariants.

    Runs in a thread-pool executor so it does not block the event loop.
    Typical wall-clock time: ~70 ms.
    """
    t0 = time.perf_counter()
    result = await asyncio.to_thread(check_spec)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

    violations: list[str] = result["violations"]
    invariant_results = {
        name: not any(name in v for v in violations)
        for name in _INVARIANT_NAMES
    }

    return RunCheckResult(
        visited=result["visited"],
        violations=violations,
        stages_seen=sorted(result["stages_seen"]),
        elapsed_ms=elapsed_ms,
        all_hold=not violations,
        invariant_results=invariant_results,
    )
