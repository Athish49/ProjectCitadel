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
