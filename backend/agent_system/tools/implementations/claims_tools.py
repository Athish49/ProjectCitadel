"""Tool implementations for the Claims Processor actor (Sprint 4.1).

Task 4.1.1 — classify_damage
  Deterministic stub damage classifier returning a CONFIDENTIAL-labelled result.
  Derives the label from a SHA-256 hash of evidence_ref so the same evidence
  always maps to the same damage category without DB I/O.

  NOTE: Doc 03 §5.2 specifies the production implementation should query
  evidence.damage_classification (a column not yet added to the schema).
  That column and the DB read are deferred to a later sprint; the stub is
  sufficient for the claims processor actor build in 4.1.6.

IFC convention change vs. sample_tools.py:
  These tools return Labeled[dict] rather than plain dicts.  The ToolRegistry
  passes the value through unchanged (registry.py:235), so the claims processor
  actor receives the full Labeled object and can propagate the label downstream.
  Tasks 4.1.2 onward follow the same convention.

Known follow-up (4.1.3): the ToolRegistry hardcodes data_label="CONFIDENTIAL"
  in its own audit rows (registry.py:230).  That will need updating when
  score_fraud returns a SECRET-labelled result.
"""
from __future__ import annotations

import hashlib

from agent_system.ifc.labels import DataLabel, Label, Labeled

# ---------------------------------------------------------------------------
# Damage label catalogue
# Maps CarDD damage categories to SeeureClaim AI internal labels.
# ---------------------------------------------------------------------------

_DAMAGE_LABELS: list[str] = [
    "collision_minor",
    "collision_moderate",
    "collision_severe",
    "total_loss",
    "weather_damage",
    "fire_damage",
    "vandalism_damage",
    "animal_strike",
]

# Hardcoded confidence per label (seeded, per Doc 03 §5.2).
_CONFIDENCE: dict[str, float] = {
    "collision_minor":    0.94,
    "collision_moderate": 0.91,
    "collision_severe":   0.89,
    "total_loss":         0.97,
    "weather_damage":     0.88,
    "fire_damage":        0.95,
    "vandalism_damage":   0.87,
    "animal_strike":      0.82,
}

_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)


# ---------------------------------------------------------------------------
# Tool: classify_damage — task 4.1.1
# ---------------------------------------------------------------------------


def classify_damage(evidence_ref: str) -> Labeled[dict]:
    """Deterministic stub damage classifier (P3 + P9 via ToolRegistry).

    Args:
        evidence_ref: evidence_id string (UUID or any stable identifier).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            evidence_ref  — echoed back for traceability
            damage_label  — one of 8 categories (deterministic from hash)
            confidence    — hardcoded per label (stub; not ML-derived)

    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    this function writes nothing to the database.
    """
    h = int(hashlib.sha256(evidence_ref.encode()).hexdigest(), 16)
    damage_label = _DAMAGE_LABELS[h % len(_DAMAGE_LABELS)]
    return Labeled(
        value={
            "evidence_ref": evidence_ref,
            "damage_label": damage_label,
            "confidence":   _CONFIDENCE[damage_label],
        },
        label=_LABEL_CONFIDENTIAL,
    )
