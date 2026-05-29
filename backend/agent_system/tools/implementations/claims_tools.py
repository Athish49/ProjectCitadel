"""Tool implementations for the Claims Processor actor (Sprint 4.1).

Task 4.1.1 — classify_damage
  Deterministic stub damage classifier returning a CONFIDENTIAL-labelled result.
  Derives the label from a SHA-256 hash of evidence_ref so the same evidence
  always maps to the same damage category without DB I/O.

  NOTE: Doc 03 §5.2 specifies the production implementation should query
  evidence.damage_classification (a column not yet added to the schema).
  That column and the DB read are deferred to a later sprint; the stub is
  sufficient for the claims processor actor build in 4.1.6.

Task 4.1.2 — lookup_coverage
  Deterministic stub coverage lookup returning a CONFIDENTIAL-labelled result.
  Derives policy_type, coverage_type, deductible, auto_approve_limit, and
  coverage_applicable from a SHA-256 hash of claim_id.  Mirrors the policies
  table schema (Doc 03 §2.3): POLICY_TYPES, COVERAGE_TYPES, and numeric ranges
  match seed.py values so the stub is coherent with the DB fixture.

  NOTE: Production implementation should SELECT from policies JOIN claims on
  claim_id.  Deferred to the sprint that adds the real DB read path.

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
# Coverage catalogue — mirrors seed.py / Doc 03 §2.3
# ---------------------------------------------------------------------------

_POLICY_TYPES: list[str] = [
    "COMPREHENSIVE",
    "COLLISION",
    "LIABILITY",
    "FULL_COVERAGE",
]

_COVERAGE_TYPES: list[str] = ["BASIC", "STANDARD", "PREMIUM"]

# Deductible tiers (dollars) — span seed range 250-2500.
_DEDUCTIBLES: list[int] = [250, 500, 1000, 1500, 2500]

# Auto-approve ceilings (dollars) — span seed range 5000-25000.
_AUTO_APPROVE_LIMITS: list[int] = [5_000, 10_000, 15_000, 20_000, 25_000]


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


# ---------------------------------------------------------------------------
# Tool: lookup_coverage — task 4.1.2
# ---------------------------------------------------------------------------


def lookup_coverage(claim_id: str) -> Labeled[dict]:
    """Deterministic stub coverage lookup (P3 + P9 via ToolRegistry).

    Args:
        claim_id: claim_id string (UUID or any stable identifier).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            claim_id            — echoed back for traceability
            policy_type         — one of 4 policy types (from hash)
            coverage_type       — BASIC / STANDARD / PREMIUM (from hash)
            deductible          — integer dollars, one of 5 tiers (from hash)
            auto_approve_limit  — integer dollars, one of 5 tiers (from hash)
            policy_status       — always "ACTIVE" in stub
            coverage_applicable — bool; False for ~1-in-6 claims (from hash)

    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    this function writes nothing to the database.
    """
    h = int(hashlib.sha256(claim_id.encode()).hexdigest(), 16)
    return Labeled(
        value={
            "claim_id":           claim_id,
            "policy_type":        _POLICY_TYPES[h % len(_POLICY_TYPES)],
            "coverage_type":      _COVERAGE_TYPES[(h >> 8) % len(_COVERAGE_TYPES)],
            "deductible":         _DEDUCTIBLES[(h >> 16) % len(_DEDUCTIBLES)],
            "auto_approve_limit": _AUTO_APPROVE_LIMITS[(h >> 24) % len(_AUTO_APPROVE_LIMITS)],
            "policy_status":      "ACTIVE",
            "coverage_applicable": (h >> 32) % 6 != 0,
        },
        label=_LABEL_CONFIDENTIAL,
    )
