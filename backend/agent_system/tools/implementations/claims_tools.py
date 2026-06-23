"""Tool implementations for the Claims Processor actor (Sprint 4.1).

classify_damage   — reads damage_classification from evidence table (Doc 03 §5.2)
lookup_coverage   — reads policy via claims JOIN policies
score_fraud       — rule-based scorer from claims+policies amount & inception data

All three tools require a DB connection injected by ToolRegistry via ContextVar
(agent_system.tools.tool_context.get_tool_conn).  They return Labeled[dict] so
the registry audit row captures the correct IFC label (P3 + P9).
"""
from __future__ import annotations

from agent_system.ifc.labels import DataLabel, Label, Labeled
from agent_system.tools.tool_context import get_tool_conn

# ---------------------------------------------------------------------------
# Damage label catalogue — mirrors seed.py and Doc 03 §5.2
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

# Hardcoded confidence per label (Doc 03 §5.2: CarDD severity → confidence).
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
# Coverage catalogue — mirrors seed.py / Doc 03 §2.3 (used by lookup_coverage)
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
# Fraud risk-factor catalogue — per decision tier (Doc 03 §2.7)
# ---------------------------------------------------------------------------

_FACTORS_CLEAR: list[str] = [
    "policy_active",
    "amount_within_limit",
    "claim_history_clean",
]

_FACTORS_FLAG: list[str] = [
    "amount_above_average",
    "claim_frequency_elevated",
    "policy_age_under_90d",
    "incident_type_mismatch",
]

_FACTORS_DENY: list[str] = [
    "amount_threshold_exceeded",
    "cross_claim_pattern",
    "policy_creation_proximity",
    "claim_frequency_high",
    "evidence_hash_anomaly",
]


# ---------------------------------------------------------------------------
# Tool: classify_damage
# ---------------------------------------------------------------------------


def classify_damage(evidence_ref: str) -> Labeled[dict]:
    """Return the damage classification stored on the evidence row.

    Args:
        evidence_ref: evidence_id (UUID string) for the submitted evidence.

    Returns:
        Labeled[dict] (CONFIDENTIAL) with evidence_ref, damage_label, confidence.

    Raises:
        ValueError: when no row exists for evidence_ref or damage_classification is NULL.
    """
    conn = get_tool_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT damage_classification FROM evidence WHERE evidence_id = %s",
            (evidence_ref,),
        )
        row = cur.fetchone()

    if row is None or row[0] is None:
        raise ValueError(
            f"No damage_classification found for evidence_ref={evidence_ref!r}"
        )

    damage_label = row[0]
    confidence = _CONFIDENCE.get(damage_label, 0.80)

    return Labeled(
        value={
            "evidence_ref": evidence_ref,
            "damage_label": damage_label,
            "confidence":   confidence,
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Tool: lookup_coverage
# ---------------------------------------------------------------------------


def lookup_coverage(claim_id: str) -> Labeled[dict]:
    """Return policy/coverage data for the given claim.

    Args:
        claim_id: claim_id (UUID string) to look up.

    Returns:
        Labeled[dict] (CONFIDENTIAL) with claim_id, policy_type, coverage_type,
        deductible, auto_approve_limit, policy_status, coverage_applicable.

    Raises:
        ValueError: when no matching claim/policy exists.
    """
    conn = get_tool_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.policy_type, p.coverage_type, p.policy_deductible,
                   p.auto_approve_limit, p.policy_status
            FROM claims c
            JOIN policies p ON p.policy_id = c.policy_id
            WHERE c.claim_id = %s
            """,
            (claim_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise ValueError(f"No policy found for claim_id={claim_id!r}")

    policy_type, coverage_type, deductible, auto_approve_limit, policy_status = row

    return Labeled(
        value={
            "claim_id":            claim_id,
            "policy_type":         policy_type,
            "coverage_type":       coverage_type,
            "deductible":          int(deductible),
            "auto_approve_limit":  int(auto_approve_limit),
            "policy_status":       policy_status,
            "coverage_applicable": policy_status == "ACTIVE",
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Tool: score_fraud
# ---------------------------------------------------------------------------


def score_fraud(claim_id: str) -> Labeled[dict]:
    """Rule-based fraud scorer — Doc 03 §5 / seed.py _fraud_decision().

    Reads total_claim_amount, incident_date, and policy_bind_date from
    claims JOIN policies (role_claims_processor has SELECT on both tables).
    Computes decision and risk_score in Python; never reads fraud_scores.

    Thresholds (mirrors seed._fraud_decision):
        amount > $40 000 → DENY
        amount > $20 000 → FLAG  (or fast-inception claim escalated from CLEAR)
        otherwise        → CLEAR

    Returns:
        Labeled[dict] (SECRET) with claim_id, risk_score, risk_factors, decision.

    Raises:
        ValueError: when no matching claim exists.
    """
    conn = get_tool_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.total_claim_amount, c.incident_date, p.policy_bind_date
            FROM claims c
            JOIN policies p ON p.policy_id = c.policy_id
            WHERE c.claim_id = %s
            """,
            (claim_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise ValueError(f"No claim found for claim_id={claim_id!r}")

    total_claim_amount, incident_date, policy_bind_date = row
    amount = float(total_claim_amount)
    days_since_bind = (incident_date - policy_bind_date).days
    fast_claim = days_since_bind < 30

    # Amount-based decision (matches seed._fraud_decision).
    if amount > 40_000:
        decision = "DENY"
    elif amount > 20_000:
        decision = "FLAG"
    else:
        decision = "CLEAR"

    # Fast inception escalates CLEAR → FLAG.
    if fast_claim and decision == "CLEAR":
        decision = "FLAG"

    # Risk score: monotonic within each tier (0-29 CLEAR, 30-59 FLAG, 60-100 DENY).
    if decision == "DENY":
        base = 60 + min(40, int((amount - 40_000) / 500))
        risk_score = min(100, base + (15 if fast_claim else 0))
    elif decision == "FLAG":
        if amount > 20_000:
            base = 30 + min(29, int((amount - 20_000) / 690))
        else:
            # CLEAR escalated to FLAG due to fast inception
            base = 30
        risk_score = min(59, base + (10 if fast_claim else 0))
    else:  # CLEAR
        risk_score = min(29, int(amount / 690))

    risk_score = max(0, risk_score)

    # Risk factors (no duplicates by construction).
    if decision == "DENY":
        risk_factors = ["amount_threshold_exceeded", "cross_claim_pattern"]
        if fast_claim:
            risk_factors.append("policy_creation_proximity")
    elif decision == "FLAG":
        risk_factors = ["amount_above_average"]
        if fast_claim:
            risk_factors.append("policy_age_under_90d")
        risk_factors.append("claim_frequency_elevated")
    else:
        risk_factors = list(_FACTORS_CLEAR)

    return Labeled(
        value={
            "claim_id":     claim_id,
            "risk_score":   risk_score,
            "risk_factors": risk_factors,
            "decision":     decision,
        },
        label=_LABEL_SECRET,
    )
