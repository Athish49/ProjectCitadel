"""RAG retriever tools for the Claims Processor actor (Sprint 4.1).

Task 4.1.4 — search_policy_docs
  Confidential RAG retriever for policy documents.  Returns a CONFIDENTIAL-
  labelled result containing the top-n ranked chunks from an inline stub corpus.

  The stub selects chunks deterministically from an inline corpus using a
  SHA-256 hash of the query so the same query always returns the same chunks
  without any ChromaDB I/O.  When ChromaDB is available and the `policy_docs`
  collection is seeded (Step 6 of the seed process), this function body will
  be replaced by a real embedding query against the collection.

  Each returned chunk is individually tagged with data_label="CONFIDENTIAL"
  (Doc 03 §6.1 item 2: "Tags each returned chunk with its source label").

  Doc 03 §6.1 specifies a `rag_retrieval` audit action; the registry uses
  `tool_call_ok` uniformly. The action name is a cosmetic concern; the
  data_label, agent, tool target, and details are the load-bearing fields
  and all correct.

Task 4.1.5 — search_fraud_rules
  Secret RAG retriever for fraud-rule documents.  Identical architecture to
  search_policy_docs but the returned label is SECRET.  See task 4.1.5.

IFC + audit:
  Both retrievers return Labeled[dict]; the ToolRegistry step-5 dynamic-label
  fix (registry.py, task 4.1.3) ensures audit rows record the correct label.
"""
from __future__ import annotations

import hashlib

from agent_system.ifc.labels import DataLabel, Label, Labeled

_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)
_LABEL_SECRET       = Label(level=DataLabel.SECRET,       untrusted=False)

# ---------------------------------------------------------------------------
# Inline policy-document corpus (stub; ~10 docs; mirrors policy_docs collection)
# ---------------------------------------------------------------------------

_POLICY_CORPUS: list[dict] = [
    {
        "doc_id": "policy-001",
        "source": "StandardAutoPolicy.pdf §2.1",
        "text": (
            "COMPREHENSIVE COVERAGE: Subject to the deductible shown in the Declarations, "
            "we will pay for direct and accidental loss to your covered auto, including its "
            "equipment, minus any applicable deductible, when the loss is caused by: contact "
            "with a bird or animal; falling objects; fire; theft or larceny; explosion or "
            "earthquake; windstorm; hail, water or flood; malicious mischief or vandalism; "
            "riot or civil commotion; contact with a bird or animal; or breakage of glass."
        ),
    },
    {
        "doc_id": "policy-002",
        "source": "StandardAutoPolicy.pdf §2.2",
        "text": (
            "COLLISION COVERAGE: We will pay for direct and accidental loss to your covered "
            "auto caused by collision with another vehicle or object, subject to the deductible "
            "shown in the Declarations. The deductible applies per occurrence. Collision with a "
            "bird or animal is covered under Comprehensive, not Collision. If both parties are "
            "insured, the not-at-fault party's deductible may be waived upon subrogation recovery."
        ),
    },
    {
        "doc_id": "policy-003",
        "source": "StandardAutoPolicy.pdf §3.1",
        "text": (
            "TOTAL LOSS DETERMINATION: A covered auto is considered a total loss when the cost "
            "of repair plus the salvage value equals or exceeds the actual cash value (ACV) at "
            "the time of loss. ACV is determined by the vehicle's pre-loss market value, "
            "accounting for age, mileage, condition, and comparable sales in the local market. "
            "For total loss settlements, we pay ACV minus any applicable deductible. The insured "
            "retains the option to keep the salvage at reduced settlement."
        ),
    },
    {
        "doc_id": "policy-004",
        "source": "StandardAutoPolicy.pdf §4.2",
        "text": (
            "WEATHER AND NATURAL DISASTER COVERAGE: Damage caused by hail, windstorm, flood, "
            "earthquake, or other Acts of God is covered under Comprehensive coverage. "
            "Documentation requirements: photographs of the damage, a weather service report "
            "for the date and location of the incident, and a repair estimate from an approved "
            "body shop. Flood damage is covered regardless of whether the vehicle was parked "
            "or in motion at the time of the loss."
        ),
    },
    {
        "doc_id": "policy-005",
        "source": "StandardAutoPolicy.pdf §4.3",
        "text": (
            "FIRE DAMAGE COVERAGE: Loss caused by fire, whether the fire originates in the "
            "vehicle or externally, is covered under Comprehensive. This includes damage from "
            "fire-fighting efforts (e.g., water or chemical suppressant damage). Arson or "
            "intentional fire is excluded (see Exclusions §7). A fire marshal or police report "
            "is required for claims where the origin of fire cannot be independently established."
        ),
    },
    {
        "doc_id": "policy-006",
        "source": "StandardAutoPolicy.pdf §4.4",
        "text": (
            "VANDALISM AND MALICIOUS MISCHIEF: Damage deliberately caused by another party "
            "is covered under Comprehensive. The insured must file a police report within "
            "72 hours of discovering the damage. Coverage includes keying, broken windows, "
            "slashed tires, graffiti removal, and tampered mechanical components. There is no "
            "deductible waiver for vandalism unless a police report identifies the responsible party."
        ),
    },
    {
        "doc_id": "policy-007",
        "source": "StandardAutoPolicy.pdf §4.5",
        "text": (
            "ANIMAL STRIKE COVERAGE: Collision with or strike by a bird or animal, including "
            "deer, is covered under Comprehensive, not Collision. A single Comprehensive "
            "deductible applies. No police report is required for animal strikes, though a "
            "contemporaneous photograph of the animal or carcass, or a wildlife incident report, "
            "strengthens the claim. Damage from a subsequent collision caused by swerving to "
            "avoid an animal is treated as a Collision loss."
        ),
    },
    {
        "doc_id": "policy-008",
        "source": "StandardAutoPolicy.pdf §5.1",
        "text": (
            "DEDUCTIBLE WAIVER: The applicable deductible may be waived in full when: (a) the "
            "responsible third party is identified and admits liability; (b) subrogation recovery "
            "is complete; or (c) the loss arises solely from a manufacturer defect subject to an "
            "active recall. Partial deductible reduction (50%) applies when our subrogation "
            "recovery is between 50% and 99% of the claim amount. Waiver is not automatic — "
            "the insured must request it during the claims process."
        ),
    },
    {
        "doc_id": "policy-009",
        "source": "ClaimsHandlingProcedures.pdf §1.2",
        "text": (
            "CLAIMS FILING DEADLINE: Physical damage claims must be reported to us within "
            "30 days of the date of loss. Claims reported after 30 days may be denied unless "
            "the insured demonstrates that the delay was caused by circumstances beyond their "
            "control. Estimates must be obtained within 60 days. Supplemental damage discovered "
            "during repair may be reported up to 10 days after the original repair completion "
            "date without triggering a late-filing denial."
        ),
    },
    {
        "doc_id": "policy-010",
        "source": "ClaimsHandlingProcedures.pdf §2.3",
        "text": (
            "MINOR COLLISION REPAIR: For collision claims below the auto-approve threshold "
            "shown in the Declarations, repair may proceed at any licensed body shop without "
            "pre-authorization. For claims at or above that threshold, prior written approval "
            "is required. Approved repair facilities are listed on the insurer portal. "
            "Non-approved shops are permitted but may result in a cost-difference payment "
            "rather than direct-to-shop settlement."
        ),
    },
]

# Stub relevance scores assigned in descending order to the selected window.
_STUB_SCORES: list[float] = [0.93, 0.88, 0.84, 0.79, 0.74]

_N_CORPUS = len(_POLICY_CORPUS)

# ---------------------------------------------------------------------------
# Inline fraud-rule corpus (stub; ~8 docs; mirrors fraud_rules collection)
# ---------------------------------------------------------------------------

_FRAUD_CORPUS: list[dict] = [
    {
        "doc_id": "fraud-001",
        "source": "FraudDetectionRules.pdf §1.1",
        "text": (
            "CLAIM VELOCITY RULE: Flag any insured who submits more than two physical-damage "
            "claims within a rolling 12-month window. A third claim triggers an automatic "
            "review hold and routes the file to the Special Investigations Unit (SIU). "
            "Velocity is measured per named insured across all policies. Severity weighting: "
            "total-loss and fire claims count double toward the velocity threshold."
        ),
    },
    {
        "doc_id": "fraud-002",
        "source": "FraudDetectionRules.pdf §1.2",
        "text": (
            "POLICY INCEPTION PROXIMITY RULE: Claims filed within 90 days of policy inception "
            "or reinstatement receive an automatic risk uplift of +15 points. Claims filed "
            "within 30 days receive a +25-point uplift. When combined with a high claim amount "
            "(above the 75th percentile for the coverage type), the file must be referred to "
            "SIU regardless of the composite score. Premium payment history is also reviewed: "
            "a single payment followed by a large claim is a primary indicator."
        ),
    },
    {
        "doc_id": "fraud-003",
        "source": "FraudDetectionRules.pdf §2.1",
        "text": (
            "EVIDENCE ANOMALY DETECTION: Inconsistencies between the reported loss mechanism "
            "and photographic evidence add +20 points to the risk score. Key anomaly patterns: "
            "(a) rust or pre-existing damage visible in claimed-new-damage areas; "
            "(b) damage geometry inconsistent with the reported impact direction; "
            "(c) odometer reading or VIN sticker absent or altered in submitted photos; "
            "(d) metadata timestamps on submitted photos predating the reported loss date. "
            "Any single pattern (b)-(d) is sufficient to trigger SIU referral."
        ),
    },
    {
        "doc_id": "fraud-004",
        "source": "FraudDetectionRules.pdf §2.2",
        "text": (
            "CROSS-CLAIM IDENTITY PATTERN: When the same individual appears as claimant, "
            "witness, or repair-shop contact on three or more unrelated claims within 24 months "
            "— across any combination of insureds — the association network is flagged. "
            "Social Security Number, driver's license, phone number, address, and email are "
            "all cross-referenced. A network of two connected claims scores +10; three or more "
            "connected claims scores +30 and mandates SIU referral."
        ),
    },
    {
        "doc_id": "fraud-005",
        "source": "FraudDetectionRules.pdf §3.1",
        "text": (
            "REPAIR SHOP COLLUSION INDICATORS: Body shops that appear on more than 5% of "
            "SIU-referred claims in a given calendar quarter are placed on the Enhanced Review "
            "List. Claims routed to a listed shop receive a +10-point uplift. Additional "
            "indicators: estimate line items that exactly match prior unrelated claims from the "
            "same shop; labor hours exceeding published labor-guide maximums by more than 20%; "
            "and supplement frequency above two per repair order. All three present simultaneously "
            "mandates SIU referral regardless of composite score."
        ),
    },
    {
        "doc_id": "fraud-006",
        "source": "FraudDetectionRules.pdf §3.2",
        "text": (
            "STAGED ACCIDENT INDICATORS: Specific collision patterns associated with staged "
            "events: (a) rear-end impact in low-speed zone with no skid marks; "
            "(b) at-fault driver leaves scene before police arrival; "
            "(c) multiple unrelated passengers claim soft-tissue injury in the same event; "
            "(d) loss occurs within 72 hours of policy inception or a significant coverage "
            "increase. Patterns (c) and (d) together add +35 points. Any event matching two "
            "or more staged-accident indicators is automatically held for SIU review."
        ),
    },
    {
        "doc_id": "fraud-007",
        "source": "FraudDetectionRules.pdf §4.1",
        "text": (
            "GHOST VEHICLE INDICATORS: A vehicle is flagged as potentially non-existent when: "
            "(a) no prior insurer history is found in CARFAX or ISO ClaimSearch; "
            "(b) the VIN decodes to a model year or trim inconsistent with the policy "
            "declarations; (c) registration records are absent or expired more than 180 days "
            "before the loss date; or (d) the vehicle was added to the policy fewer than "
            "14 days before the loss. Any single indicator adds +20 points; two or more "
            "mandate VIN verification before payment."
        ),
    },
    {
        "doc_id": "fraud-008",
        "source": "FraudDetectionRules.pdf §4.2",
        "text": (
            "INFLATED ESTIMATE DETECTION: Estimates are flagged when the total repair cost "
            "exceeds 130% of the Mitchell/CCC benchmark for the same damage code and vehicle "
            "class. Part prices more than 25% above OEM list price trigger a line-item audit. "
            "When flagged, a desk review appraiser must approve the delta before payment is "
            "authorized. Repeated over-estimates from the same shop across multiple claims "
            "contribute to the shop's collusion score (see §3.1). Inflated estimates alone "
            "add +10 points to the composite risk score."
        ),
    },
]

_N_FRAUD_CORPUS = len(_FRAUD_CORPUS)


# ---------------------------------------------------------------------------
# Tool: search_policy_docs — task 4.1.4
# ---------------------------------------------------------------------------


def search_policy_docs(query: str, n_results: int = 3) -> Labeled[dict]:
    """Confidential RAG retriever for policy documents (P3 + P9 via ToolRegistry).

    Args:
        query:     Natural-language search query.
        n_results: Number of chunks to return (clamped to [1, corpus size]).

    Returns:
        Labeled[dict] with data_label=CONFIDENTIAL containing:
            query      — echoed back for traceability
            n_results  — effective count returned
            chunks     — list of dicts, each with:
                           doc_id      — stable chunk identifier
                           source      — document/section reference
                           text        — policy excerpt
                           score       — stub relevance float [0.74, 0.93]
                           data_label  — "CONFIDENTIAL" (per-chunk tag)

    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    this function writes nothing to the database.
    """
    n = max(1, min(n_results, _N_CORPUS))
    h = int(hashlib.sha256(query.encode()).hexdigest(), 16)
    start = h % _N_CORPUS

    chunks = []
    for i in range(n):
        doc = _POLICY_CORPUS[(start + i) % _N_CORPUS]
        chunks.append({
            "doc_id":     doc["doc_id"],
            "source":     doc["source"],
            "text":       doc["text"],
            "score":      _STUB_SCORES[i % len(_STUB_SCORES)],
            "data_label": "CONFIDENTIAL",
        })

    return Labeled(
        value={
            "query":     query,
            "n_results": n,
            "chunks":    chunks,
        },
        label=_LABEL_CONFIDENTIAL,
    )


# ---------------------------------------------------------------------------
# Tool: search_fraud_rules — task 4.1.5
# ---------------------------------------------------------------------------


def search_fraud_rules(query: str, n_results: int = 3) -> Labeled[dict]:
    """Secret RAG retriever for fraud-rule documents (P3 + P9 via ToolRegistry).

    Args:
        query:     Natural-language search query.
        n_results: Number of chunks to return (clamped to [1, corpus size]).

    Returns:
        Labeled[dict] with data_label=SECRET containing:
            query      — echoed back for traceability
            n_results  — effective count returned
            chunks     — list of dicts, each with:
                           doc_id      — stable chunk identifier
                           source      — document/section reference
                           text        — fraud-rule excerpt
                           score       — stub relevance float [0.74, 0.93]
                           data_label  — "SECRET" (per-chunk tag)

    The ToolRegistry writes the tool_call_ok / tool_call_denied audit row;
    the step-5 dynamic-label fix (registry.py, task 4.1.3) ensures the row
    records data_label=SECRET.  This function writes nothing to the database.
    """
    n = max(1, min(n_results, _N_FRAUD_CORPUS))
    h = int(hashlib.sha256(query.encode()).hexdigest(), 16)
    start = h % _N_FRAUD_CORPUS

    chunks = []
    for i in range(n):
        doc = _FRAUD_CORPUS[(start + i) % _N_FRAUD_CORPUS]
        chunks.append({
            "doc_id":     doc["doc_id"],
            "source":     doc["source"],
            "text":       doc["text"],
            "score":      _STUB_SCORES[i % len(_STUB_SCORES)],
            "data_label": "SECRET",
        })

    return Labeled(
        value={
            "query":     query,
            "n_results": n,
            "chunks":    chunks,
        },
        label=_LABEL_SECRET,
    )
