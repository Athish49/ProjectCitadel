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

Task 4.1.3 — score_fraud
  Rule-based stub fraud scorer returning a SECRET-labelled full record.
  Derives risk_score (0-100), risk_factors, and decision (CLEAR/FLAG/DENY)
  from a SHA-256 hash of claim_id.  Thresholds: score<30→CLEAR, <60→FLAG,
  ≥60→DENY.  risk_factors subset selected from a per-tier catalogue; mirrors
  the fraud_scores table schema (Doc 03 §2.7).

  The ToolRegistry audit row data_label is now dynamic (registry.py step 5):
  it reads value.label.level.value when the handler returns a Labeled object,
  so the audit row correctly records "SECRET" for this tool.
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
_LABEL_SECRET       = Label(level=DataLabel.SECRET,       untrusted=False)

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
DEDUCTIBLES: list[int] = [250, 500, 1000, 1500, 2500]

# Auto-approve ceilings (dollars) — span seed range 5000-25000.
AUTO_APPROVE_LIMITS: list[int] = [5_000, 10_000, 15_000, 20_000, 25_000]


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
            "deductible":         DEDUCTIBLES[(h >> 16) % len(DEDUCTIBLES)],
            "auto_approve_limit": AUTO_APPROVE_LIMITS[(h >> 24) % len(AUTO_APPROVE_LIMITS)],
            "policy_status":      "ACTIVE",
            "coverage_applicable": (h >> 32) % 6 != 0,
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Fraud risk-factor catalogue — per decision tier (Doc 03 §2.7)
# risk_factors is JSONB in production; stub returns a deterministic subset.
# ---------------------------------------------------------------------------

_FACTORS_CLEAR: list[str] = [
    "policy_active",
    "amount_within_limit",
    "claim_history_clean",
]

_FACTORS_FLAG: list[str] = [
    "amount_above_average",
    "policy_age_under_90d",
    "claim_frequency_elevated",
    "incident_type_mismatch",
]

_FACTORS_DENY: list[str] = [
    "amount_threshold_exceeded",
    "policy_creation_proximity",
    "claim_frequency_high",
    "cross_claim_pattern",
    "evidence_hash_anomaly",
]


# ---------------------------------------------------------------------------
# Tool: score_fraud — task 4.1.3
# ---------------------------------------------------------------------------


def score_fraud(claim_id: str) -> Labeled[dict]:
    """Deterministic rule-based fraud scorer (P3 + P9 via ToolRegistry).

    Args:
        claim_id: claim_id string (UUID or any stable identifier).

    Returns:
        Labeled[dict] with data_label=SECRET containing:
            claim_id      — echoed back for traceability
            risk_score    — integer 0-100; SECRET (reveals model signal)
            risk_factors  — list[str]; SECRET (reveals model logic)
            decision      — CLEAR / FLAG / DENY (derived from risk_score)

    Thresholds: score<30 → CLEAR, score<60 → FLAG, score≥60 → DENY.
    The orchestrator must only propagate `decision`; risk_score and
    risk_factors must not leave the claims processor runtime (egress P10).

    The ToolRegistry writes the tool_call_ok audit row with data_label=SECRET
    (fixed in 4.1.3: registry step 5 reads value.label.level.value when the
    handler returns a Labeled object).
    """
    h = int(hashlib.sha256(claim_id.encode()).hexdigest(), 16)
    risk_score = h % 101  # 0-100 inclusive

    if risk_score < 30:
        decision = "CLEAR"
        catalogue = _FACTORS_CLEAR
        n_factors = 1 + (h >> 8) % len(_FACTORS_CLEAR)
    elif risk_score < 60:
        decision = "FLAG"
        catalogue = _FACTORS_FLAG
        n_factors = 1 + (h >> 8) % len(_FACTORS_FLAG)
    else:
        decision = "DENY"
        catalogue = _FACTORS_DENY
        n_factors = 2 + (h >> 8) % (len(_FACTORS_DENY) - 1)

    # Select a deterministic, ordered subset of factors.
    risk_factors = [catalogue[(i + (h >> 16)) % len(catalogue)] for i in range(n_factors)]
    # Deduplicate while preserving order.
    seen: set[str] = set()
    risk_factors = [f for f in risk_factors if not (f in seen or seen.add(f))]  # type: ignore[func-returns-value]

    return Labeled(
        value={
            "claim_id":     claim_id,
            "risk_score":   risk_score,
            "risk_factors": risk_factors,
            "decision":     decision,
        },
        label=_LABEL_SECRET,
    )
