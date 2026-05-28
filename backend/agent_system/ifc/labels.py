"""IFC label types (P3 — task 1.2.4).

Trust labels form an ordered lattice:  PUBLIC < PERSONAL < CONFIDENTIAL < SECRET.
UNTRUSTED is orthogonal — a taint flag that propagates independently of the trust
level (an UNTRUSTED datum may be PUBLIC- or SECRET-labelled).

`DataLabel` values are intentionally equal to the VARCHAR strings stored in the
DB (audit_log.data_label, capability_token_log.scope, etc.).  Do not change them
without a matching schema migration.

No psycopg or audit-log imports here — ifc/ is pure logic.  The caller
(registry, egress filter, orchestrator) owns audit row writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")

# Map used for ordering.  Do not reorder without updating the lattice comment above.
_LABEL_ORDER: dict[str, int] = {
    "PUBLIC": 0,
    "PERSONAL": 1,
    "CONFIDENTIAL": 2,
    "SECRET": 3,
}


class DataLabel(str, Enum):
    """Sensitivity level in the information-flow lattice.

    String values match the DB CHECK constraint on data_label columns.
    """

    PUBLIC = "PUBLIC"
    PERSONAL = "PERSONAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"

    # total_ordering cannot be used here: str already supplies __gt__/__le__/__ge__
    # so the decorator leaves those inherited methods in place (they do string
    # ordering, not lattice ordering).  Define all four explicitly instead.

    def __lt__(self, other: "DataLabel") -> bool:
        if not isinstance(other, DataLabel):
            return NotImplemented
        return _LABEL_ORDER[self.value] < _LABEL_ORDER[other.value]

    def __le__(self, other: "DataLabel") -> bool:
        if not isinstance(other, DataLabel):
            return NotImplemented
        return _LABEL_ORDER[self.value] <= _LABEL_ORDER[other.value]

    def __gt__(self, other: "DataLabel") -> bool:
        if not isinstance(other, DataLabel):
            return NotImplemented
        return _LABEL_ORDER[self.value] > _LABEL_ORDER[other.value]

    def __ge__(self, other: "DataLabel") -> bool:
        if not isinstance(other, DataLabel):
            return NotImplemented
        return _LABEL_ORDER[self.value] >= _LABEL_ORDER[other.value]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DataLabel):
            return self.value == other.value
        # Support comparison with raw DB strings ("CONFIDENTIAL" == DataLabel.CONFIDENTIAL).
        if isinstance(other, str):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(frozen=True)
class Label:
    """A trust level combined with an optional UNTRUSTED taint.

    Immutable so labels cannot be silently widened after construction.
    """

    level: DataLabel
    untrusted: bool = False

    def __str__(self) -> str:
        base = self.level.value
        return f"{base}+UNTRUSTED" if self.untrusted else base


@dataclass(frozen=True)
class Labeled(Generic[T]):
    """A typed value paired with its IFC label.

    Access via `.value` and `.label`.  Frozen — reassignment raises.
    """

    value: T
    label: Label


class LabelViolationError(Exception):
    """Raised when a label check fails (e.g. label below minimum required)."""
