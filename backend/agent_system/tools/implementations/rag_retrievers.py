"""RAG retriever tools for the Claims Processor and Intake actors (Sprint 4.1).

Task 4.1.4 — search_policy_docs
  Confidential RAG retriever for policy documents. When QDRANT_URL is set,
  queries the live Qdrant `ProjectCitadel-policy_docs` collection using
  BAAI/bge-small-en-v1.5 embeddings via fastembed. Falls back to the inline
  corpus stub when Qdrant is not configured (unit tests without credentials).

Task 4.1.5 — search_fraud_rules
  Secret RAG retriever for fraud-rule documents. Same architecture, queries
  `ProjectCitadel-fraud_rules`.

Task 4.2.2 — search_public_faq
  Public RAG retriever for customer-facing FAQ documents. Queries
  `ProjectCitadel-public_faq`. NOTE: Qdrant API key must be re-issued with
  rw scope for ProjectCitadel-public_faq before live ingestion will succeed.

IFC + audit:
  All retrievers return Labeled[dict]; the ToolRegistry step-5 dynamic-label
  fix (registry.py, task 4.1.3) ensures audit rows record the correct label.
"""
from __future__ import annotations

import hashlib
import os
from typing import TYPE_CHECKING

from agent_system.ifc.labels import DataLabel, Label, Labeled

if TYPE_CHECKING:
    from fastembed import TextEmbedding
    from qdrant_client import QdrantClient

_LABEL_PUBLIC       = Label(level=DataLabel.PUBLIC,       untrusted=False)
_LABEL_CONFIDENTIAL = Label(level=DataLabel.CONFIDENTIAL, untrusted=False)
_LABEL_SECRET       = Label(level=DataLabel.SECRET,       untrusted=False)

_EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# ---------------------------------------------------------------------------
# Inline policy-document corpus
# Kept as module-level constants: used for ingestion (db/ingest.py) and
# imported directly by unit tests for corpus size / doc_id assertions.
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

_N_CORPUS = len(_POLICY_CORPUS)

# Stub relevance scores (used only when Qdrant is not configured).
_STUB_SCORES: list[float] = [0.93, 0.88, 0.84, 0.79, 0.74]

# ---------------------------------------------------------------------------
# Inline fraud-rule corpus
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
# Inline public FAQ corpus (PUBLIC)
# ---------------------------------------------------------------------------

_FAQ_CORPUS: list[dict] = [
    {
        "doc_id": "faq-001",
        "source": "CustomerFAQ.pdf §1.1",
        "text": (
            "HOW LONG DOES THE CLAIMS PROCESS TAKE? Standard physical-damage claims are "
            "typically processed within 5–7 business days after all required documents are "
            "received. Complex or disputed claims, or those requiring Special Investigations "
            "Unit review, may take 2–4 weeks. You will receive status updates by email and "
            "through the customer portal throughout the process."
        ),
    },
    {
        "doc_id": "faq-002",
        "source": "CustomerFAQ.pdf §1.2",
        "text": (
            "WHAT DOCUMENTS ARE REQUIRED TO FILE A CLAIM? You will need: a completed claim "
            "form, photographs of all damage, a police report (if applicable — required for "
            "theft, vandalism, or collision with another vehicle), repair estimates from a "
            "licensed body shop, and your policy number and vehicle identification number (VIN). "
            "Additional documents may be requested during the review process."
        ),
    },
    {
        "doc_id": "faq-003",
        "source": "CustomerFAQ.pdf §1.3",
        "text": (
            "HOW DO I CONTACT MY CLAIMS ADJUSTER? After filing a claim online or by phone, "
            "you will be assigned a claims adjuster within one business day. Their contact "
            "information is included in your claim confirmation email. You can also log in "
            "to the customer portal to message your adjuster directly or schedule a call. "
            "Adjusters are available Monday–Friday, 8 AM–6 PM local time."
        ),
    },
    {
        "doc_id": "faq-004",
        "source": "CustomerFAQ.pdf §2.1",
        "text": (
            "IS A RENTAL CAR COVERED WHILE MY VEHICLE IS BEING REPAIRED? Rental reimbursement "
            "coverage is available if you purchased it as an endorsement on your policy. "
            "Coverage is typically $30–$50 per day up to a maximum of 30 days. Your specific "
            "daily limit and maximum are shown on your Declarations page. Rental coverage "
            "begins on the date your vehicle is dropped off for repairs and ends when repairs "
            "are complete or the maximum is reached, whichever comes first."
        ),
    },
    {
        "doc_id": "faq-005",
        "source": "CustomerFAQ.pdf §2.2",
        "text": (
            "WHAT IS A DEDUCTIBLE AND HOW DOES IT WORK? A deductible is the amount you pay "
            "out-of-pocket before insurance coverage applies to a claim. For example, if your "
            "deductible is $500 and your repair costs $3,000, you pay $500 and we pay the "
            "remaining $2,500. Separate deductibles may apply for Collision and Comprehensive "
            "coverage. Your deductible amounts are shown on your Declarations page. Deductibles "
            "may be waived in certain circumstances — see your policy for details."
        ),
    },
    {
        "doc_id": "faq-006",
        "source": "CustomerFAQ.pdf §2.3",
        "text": (
            "CAN I CHOOSE MY OWN REPAIR SHOP? Yes. You may take your vehicle to any licensed "
            "repair shop of your choice. Using a shop in our approved network may result in "
            "faster processing, a direct-payment arrangement between us and the shop, and a "
            "repair warranty. Non-network shops are permitted but may require you to pay "
            "upfront and submit receipts for reimbursement, and a cost-difference payment "
            "rather than full reimbursement may apply."
        ),
    },
    {
        "doc_id": "faq-007",
        "source": "CustomerFAQ.pdf §3.1",
        "text": (
            "WHAT HAPPENS IF MY CAR IS DECLARED A TOTAL LOSS? If the cost of repairs plus "
            "the salvage value equals or exceeds your vehicle's actual cash value (ACV) at "
            "the time of loss, it may be declared a total loss. We will offer you the ACV "
            "minus your deductible. You may retain the salvage vehicle at a reduced settlement "
            "amount. A title transfer to us will be required if you do not retain the salvage."
        ),
    },
    {
        "doc_id": "faq-008",
        "source": "CustomerFAQ.pdf §3.2",
        "text": (
            "HOW IS MY VEHICLE'S VALUE DETERMINED FOR A TOTAL LOSS? Actual cash value (ACV) "
            "is based on comparable vehicles sold in your local market, accounting for your "
            "vehicle's year, make, model, trim level, mileage, and condition. We use "
            "third-party valuation tools and regional market data to establish a fair value. "
            "You may provide documentation of recent comparable sales if you believe the "
            "valuation is inaccurate, and we will review it."
        ),
    },
    {
        "doc_id": "faq-009",
        "source": "CustomerFAQ.pdf §4.1",
        "text": (
            "HOW DO I CHECK THE STATUS OF MY CLAIM? You can check your claim status 24/7 "
            "through the customer portal at your insurer's website, by calling the claims "
            "hotline, or by emailing your adjuster. Status milestones include: documents "
            "received, adjuster assigned, inspection scheduled, estimate approved, payment "
            "authorized, and claim closed. Text and email notifications are available — "
            "opt in through the portal."
        ),
    },
    {
        "doc_id": "faq-010",
        "source": "CustomerFAQ.pdf §4.2",
        "text": (
            "WHAT SHOULD I DO IMMEDIATELY AFTER AN ACCIDENT? Call emergency services if "
            "anyone is injured. Move vehicles to a safe location if it is safe to do so. "
            "Exchange insurance information, driver's license numbers, and contact details "
            "with all parties involved. Take photographs of all vehicles, visible damage, "
            "and the scene. Obtain witness contact information if possible. Notify us as "
            "soon as possible — claims must be filed within 30 days of the date of loss."
        ),
    },
]

_N_FAQ_CORPUS = len(_FAQ_CORPUS)

# ---------------------------------------------------------------------------
# Qdrant lazy singletons
# ---------------------------------------------------------------------------

_qdrant_client: "QdrantClient | None" = None
_text_embedder: "TextEmbedding | None" = None


def _use_qdrant() -> bool:
    return bool(os.environ.get("QDRANT_URL"))


def _get_client() -> "QdrantClient":
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        _qdrant_client = QdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ.get("QDRANT_API_KEY"),
        )
    return _qdrant_client


def _get_embedder() -> "TextEmbedding":
    global _text_embedder
    if _text_embedder is None:
        from fastembed import TextEmbedding
        _text_embedder = TextEmbedding(_EMBED_MODEL)
    return _text_embedder


def _qdrant_search(collection: str, data_label: str, query: str, n: int) -> list[dict]:
    embedder = _get_embedder()
    client = _get_client()

    query_vector = list(embedder.embed([query]))[0].tolist()
    # query_points() is the v1.12+ replacement for the removed search()
    response = client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=n,
        with_payload=True,
    )
    return [
        {
            "doc_id":     hit.payload["doc_id"],
            "source":     hit.payload["source"],
            "text":       hit.payload["text"],
            "score":      round(float(hit.score), 4),
            "data_label": data_label,
        }
        for hit in response.points
    ]


# ---------------------------------------------------------------------------
# Stub fallback (used when QDRANT_URL is not set — keeps unit tests fast)
# ---------------------------------------------------------------------------

def _stub_search(corpus: list[dict], data_label: str, query: str, n: int) -> list[dict]:
    size = len(corpus)
    n = max(1, min(n, size))
    h = int(hashlib.sha256(query.encode()).hexdigest(), 16)
    start = h % size
    chunks = []
    for i in range(n):
        doc = corpus[(start + i) % size]
        chunks.append({
            "doc_id":     doc["doc_id"],
            "source":     doc["source"],
            "text":       doc["text"],
            "score":      _STUB_SCORES[i % len(_STUB_SCORES)],
            "data_label": data_label,
        })
    return chunks


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
            chunks     — list of dicts: doc_id, source, text, score, data_label
    """
    if _use_qdrant():
        collection = os.environ.get("QDRANT_POLICY_COLLECTION", "ProjectCitadel-policy_docs")
        n = max(1, min(n_results, _N_CORPUS))
        chunks = _qdrant_search(collection, "CONFIDENTIAL", query, n)
    else:
        n = max(1, min(n_results, _N_CORPUS))
        chunks = _stub_search(_POLICY_CORPUS, "CONFIDENTIAL", query, n)

    return Labeled(
        value={"query": query, "n_results": len(chunks), "chunks": chunks},
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
            chunks     — list of dicts: doc_id, source, text, score, data_label
    """
    if _use_qdrant():
        collection = os.environ.get("QDRANT_FRAUD_COLLECTION", "ProjectCitadel-fraud_rules")
        n = max(1, min(n_results, _N_FRAUD_CORPUS))
        chunks = _qdrant_search(collection, "SECRET", query, n)
    else:
        n = max(1, min(n_results, _N_FRAUD_CORPUS))
        chunks = _stub_search(_FRAUD_CORPUS, "SECRET", query, n)

    return Labeled(
        value={"query": query, "n_results": len(chunks), "chunks": chunks},
        label=_LABEL_SECRET,
    )


# ---------------------------------------------------------------------------
# Tool: search_public_faq — task 4.2.2
# ---------------------------------------------------------------------------


def search_public_faq(query: str, n_results: int = 3) -> Labeled[dict]:
    """Public RAG retriever for customer-facing FAQ documents.

    Args:
        query:     Natural-language search query.
        n_results: Number of chunks to return (clamped to [1, corpus size]).

    Returns:
        Labeled[dict] with data_label=PUBLIC containing:
            query      — echoed back for traceability
            n_results  — effective count returned
            chunks     — list of dicts: doc_id, source, text, score, data_label

    NOTE: Live Qdrant path requires the API key to have rw scope for the
    ProjectCitadel-public_faq collection (QDRANT_FAQ_COLLECTION env var).
    """
    if _use_qdrant():
        collection = os.environ.get("QDRANT_FAQ_COLLECTION", "ProjectCitadel-public_faq")
        n = max(1, min(n_results, _N_FAQ_CORPUS))
        chunks = _qdrant_search(collection, "PUBLIC", query, n)
    else:
        n = max(1, min(n_results, _N_FAQ_CORPUS))
        chunks = _stub_search(_FAQ_CORPUS, "PUBLIC", query, n)

    return Labeled(
        value={"query": query, "n_results": len(chunks), "chunks": chunks},
        label=_LABEL_PUBLIC,
    )
