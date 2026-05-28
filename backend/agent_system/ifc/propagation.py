"""IFC label propagation helpers (P3 — task 1.2.4).

These are pure functions — no DB I/O, no side effects.
"""
from __future__ import annotations

from typing import Iterable

from agent_system.ifc.labels import DataLabel, Label


def join(a: Label, b: Label) -> Label:
    """Least upper bound of two labels.

    Level is the maximum of both levels; untrusted taint is sticky (OR).
    """
    return Label(
        level=max(a.level, b.level),
        untrusted=a.untrusted or b.untrusted,
    )


def join_all(labels: Iterable[Label]) -> Label:
    """Fold join over an iterable; identity element is PUBLIC/trusted."""
    result = Label(level=DataLabel.PUBLIC, untrusted=False)
    for lbl in labels:
        result = join(result, lbl)
    return result


def taint(label: Label) -> Label:
    """Return a copy of *label* with the UNTRUSTED flag set.  Idempotent."""
    return Label(level=label.level, untrusted=True)
