# SecureClaim AI — Data Model & Schema Document

**Version:** 2.1
**Date:** June 14, 2026
**Status:** Updated v2.1
**Author:** Athish G R
**Classification:** Internal

---

## 1. Conceptual Data Model

The model is intentionally compact. Every entity is sized to what the showcase demands; nothing more.

```
┌────────────┐       1:1       ┌────────────┐       1:N       ┌────────────┐
│  CUSTOMER  │────────────────→│   POLICY   │────────────────→│   CLAIM    │
│ (PERSONAL) │                 │(CONFIDENTIAL)│                │(CONFIDENTIAL)│
└─────┬──────┘                 └────────────┘                 └──┬───┬─────┘
      │ 1:1                                            1:N ┌─────┘   └────┐ 1:1
      ▼                                                    ▼              ▼
┌────────────┐                                      ┌────────────┐ ┌──────────┐
│ PII VAULT  │                                      │  EVIDENCE  │ │SETTLEMENT│
│  (SECRET)  │                                      │(CONFIDENTIAL)│(CONFIDENTIAL)│
└────────────┘                                      └────────────┘ └──────────┘

┌────────────┐      ┌────────────┐      ┌────────────────────┐
│FRAUD_SCORE │      │ FRAUD_RULES│      │ AUDIT_LOG          │
│  (SECRET)  │      │  (SECRET)  │      │ (CONFIDENTIAL,     │
│            │      │            │      │  append-only,      │
│            │      │            │      │  hash-chained)     │
└────────────┘      └────────────┘      └────────────────────┘

┌──────────────────────────────────────┐    ┌─────────────────────┐
│ CAPABILITY_TOKEN_LOG                  │    │ SECURITY_EVENTS     │
│ (CONFIDENTIAL — every issuance/use)   │    │ (CONFIDENTIAL)      │
└──────────────────────────────────────┘    └─────────────────────┘
```

Every table carries an explicit IFC label (see Doc 02 §2.6). The label is enforced at the DB role layer, the RLS policy layer, the tool registry, and the egress filter.

---

## 2. Database Schemas

All schemas use PostgreSQL 16. Every customer-scoped table has a Row-Level Security (RLS) policy keyed off the session's authenticated `customer_id`, which is set on the connection via `SET LOCAL app.current_customer_id = ...` after JWT verification by the API gateway.

### 2.1 customers (Label: PERSONAL)

| Column | Type | Notes |
|--------|------|-------|
| customer_id | UUID PK | |
| policy_number | VARCHAR(20) UNIQUE | |
| first_name | VARCHAR(100) | |
| last_name | VARCHAR(100) | |
| email | VARCHAR(200) | |
| phone | VARCHAR(20) | |
| date_of_birth | DATE | |
| address_line1, city, state, zip_code | (standard) | |
| created_at | TIMESTAMPTZ | |

**RLS policy:**
```sql
CREATE POLICY customers_self_only ON customers
  USING (customer_id = current_setting('app.current_customer_id')::uuid);
```

**Per-agent DB roles:**
- `role_intake_actor`: SELECT on (customer_id, first_name, last_name) only, RLS active.
- `role_settlement_actor`: SELECT on (customer_id, first_name, last_name, address_*) only, RLS active.
- `role_orchestrator`: SELECT on (customer_id) only.
- No role has direct SELECT on DOB or full PII.

### 2.2 pii_vault (Label: SECRET)

| Column | Type | Notes |
|--------|------|-------|
| customer_id | UUID PK FK | |
| ssn_hash | BYTEA | Argon2id(SSN ‖ deployment_pepper) |
| ssn_last4 | VARCHAR(4) | for verification UX only |
| drivers_license_enc | BYTEA | AES-256-GCM with per-field key |
| dl_iv | BYTEA | |
| bank_routing_enc, bank_account_enc, ba_iv, br_iv | BYTEA | AES-256-GCM |
| security_answer_hash | BYTEA | Argon2id |
| created_at | TIMESTAMPTZ | |

**Hashing:** SSN is bound to a deployment-held pepper (held in a local KMS-mock file in dev, KMS in production-shaped deployment). Raw SHA-256 of SSN — a previous-version artefact — is **not** acceptable; the SSN keyspace is brute-forceable at SHA-256 speed.

**Access:** No agent has DB access to this table. The only path is the server-side function `verify_identity(policy_number, ssn_last4, dob_iso) → boolean`, which the identity verifier invokes via a capability token. The function logs every attempt to `identity_attempts` and applies lockout. PII values never enter any LLM context.

Bank details are referenced **only via session-bound payee binding**: at claim creation, the system records the policy's bound payee (set up out-of-band in this demo); the settlement actor can only `request_payout(claim_id)`, which the payout function resolves to the session's bound payee with no parameter for payee selection.

### 2.3 policies (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| policy_id | UUID PK | |
| policy_number | VARCHAR(20) UNIQUE | |
| customer_id | UUID FK | |
| policy_type | VARCHAR(50) | |
| policy_csl | VARCHAR(20) | |
| policy_deductible | INTEGER | |
| coverage_type | VARCHAR(50) | |
| policy_bind_date, policy_expiry_date | DATE | |
| policy_status | VARCHAR(20) | ACTIVE / LAPSED / CANCELLED |
| auto_approve_limit | INTEGER | per-policy auto-approval ceiling |

**RLS:** `customer_id = current_setting('app.current_customer_id')::uuid`.

### 2.4 vehicles (Label: PERSONAL)

| Column | Type | Notes |
|--------|------|-------|
| vehicle_id | UUID PK | |
| customer_id, policy_id | UUID FK | |
| auto_make, auto_model | VARCHAR | |
| auto_year | INTEGER | |
| vin | VARCHAR(17) | synthetic |

### 2.5 claims (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| claim_id | UUID PK | |
| claim_number | VARCHAR(20) | CLM-XXXXXX |
| customer_id, policy_id | UUID FK | |
| incident_date | DATE | |
| incident_type | VARCHAR(50) | |
| incident_description | TEXT | UNTRUSTED-derived; stored escaped |
| total_claim_amount | NUMERIC(10,2) | |
| claim_stage | VARCHAR(30) | enforced enum from state machine |
| created_at, updated_at | TIMESTAMPTZ | |

**RLS:** customer-scoped.

### 2.6 evidence (Label: CONFIDENTIAL; raw bytes UNTRUSTED until sanitised)

| Column | Type | Notes |
|--------|------|-------|
| evidence_id | UUID PK | |
| claim_id | UUID FK | |
| evidence_type | VARCHAR(20) | PHOTO / PDF / OTHER |
| original_filename | VARCHAR(200) | sanitised for display |
| sha256_original | CHAR(64) | content-addressable |
| sanitised_path | VARCHAR(500) | post-sanitisation artefact |
| sha256_sanitised | CHAR(64) | content-addressable |
| sanitisation_status | VARCHAR(20) | CLEAN / FLAGGED / REJECTED |
| sanitisation_flags | JSONB | findings: hidden_text, suspicious_metadata, ocr_text_present, vision_redactions |
| extracted_text_label | VARCHAR(20) | always UNTRUSTED until parser-processed |
| uploaded_at | TIMESTAMPTZ | |

**Important:** raw uploaded bytes are stored only in the sandbox container's ephemeral filesystem during processing. Only the sanitised artefact is persisted. The original SHA-256 is kept for forensic integrity.

### 2.7 fraud_scores (Label: SECRET — never customer-visible)

| Column | Type | Notes |
|--------|------|-------|
| score_id | UUID PK | |
| claim_id | UUID FK | |
| risk_score | INTEGER | 0–100, SECRET |
| risk_factors | JSONB | SECRET — reveals model logic |
| decision | VARCHAR(20) | CLEAR / FLAG / DENY (this is the only field the orchestrator sees) |
| scored_at | TIMESTAMPTZ | |

**Access:** the fraud scoring tool returns the full row to the claims processor's tool runtime but the **IFC label propagation** records `risk_score` and `risk_factors` as SECRET. The egress filter denies any customer-visible response containing them. The orchestrator only ever holds the `decision` field.

Note: previous version tier was "Confidential". Promoted to SECRET because the factors expose model logic that #22 (model inversion) targets directly.

### 2.8 settlements (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| settlement_id | UUID PK | |
| claim_id | UUID FK | |
| offered_amount | NUMERIC(10,2) | computed by deterministic function |
| deductible_applied | NUMERIC(10,2) | |
| approval_status | VARCHAR(20) | PENDING / AUTO_APPROVED / HUMAN_APPROVED / DENIED |
| payout_status | VARCHAR(20) | PENDING / PROCESSED / FAILED |
| payout_reference | VARCHAR(100) | |
| created_at | TIMESTAMPTZ | |

### 2.9 audit_log (Label: CONFIDENTIAL — append-only, hash-chained)

| Column | Type | Notes |
|--------|------|-------|
| log_id | BIGSERIAL PK | |
| trace_id | UUID | |
| prev_hash | CHAR(64) | hash of previous log row |
| row_hash | CHAR(64) | sha256(prev_hash ‖ canonical_json(row\\_hash)) |
| agent_id | VARCHAR(50) | |
| action | VARCHAR(100) | tool_call / state_transition / sanitisation_event / parser_emit / capability_issue / capability_use / security_event |
| target | VARCHAR(200) | |
| details | JSONB | (PII redacted before write) |
| data_label | VARCHAR(20) | label of the data accessed/produced |
| security_event | BOOLEAN | true if this row represents a defense firing |
| ts | TIMESTAMPTZ | |

**Role enforcement (this is the schema mechanism, not just a comment):**
```sql
REVOKE ALL ON audit_log FROM PUBLIC;
GRANT INSERT ON audit_log TO role_audit_writer;
-- No UPDATE, no DELETE granted to any application role.
-- Only role_audit_admin (operator-held, MFA-gated) may purge under retention.
```

**Chain verification:** scheduled job and on-demand Console endpoint recompute the chain and emit `chain_verified` or `chain_broken` event.

### 2.10 capability_token_log (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| token_id | UUID PK | |
| issued_by | VARCHAR(50) | always orchestrator |
| agent_id | VARCHAR(50) | grantee |
| tool | VARCHAR(100) | |
| scope | JSONB | |
| issued_at, expires_at | TIMESTAMPTZ | |
| used_at | TIMESTAMPTZ NULL | |
| use_result | VARCHAR(20) | OK / DENIED_SCOPE / DENIED_EXPIRED / DENIED_SIGNATURE |

Every issuance and every use is logged. The Console surfaces this as one of the visible defense signals.

### 2.11 security_events (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| event_id | UUID PK | |
| trace_id | UUID | |
| event_type | VARCHAR(100) | injection_pattern_hit / semantic_score_high / schema_violation / capability_denied / rls_denied / pii_egress_blocked / url_egress_blocked / token_budget_exceeded / chain_broken / etc. |
| attack_id | INTEGER NULL | mapped to the 79-category taxonomy if applicable |
| severity | VARCHAR(10) | info / warn / critical |
| details | JSONB | |
| ts | TIMESTAMPTZ | |

This table is what feeds the Console's playground "Defense Fired" panel and the live audit stream's "security" filter.

### 2.12 identity_attempts (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| attempt_id | UUID PK | |
| session_id | UUID | |
| customer_id | UUID NULL | populated only on success |
| attempted_policy_number | VARCHAR(20) | |
| outcome | VARCHAR(20) | SUCCESS / FAIL_MATCH / LOCKOUT |
| ts | TIMESTAMPTZ | |

---

### 2.13 complaints (Label: CONFIDENTIAL)

| Column | Type | Notes |
|--------|------|-------|
| complaint_id | UUID PK | |
| session_id | UUID | |
| customer_id | UUID FK | RLS-scoped |
| related_claim_id | UUID FK NULL | optional reference to a claim |
| category | VARCHAR(50) | service / coverage / decision / process / other |
| description | TEXT | UNTRUSTED-derived; stored escaped; never echoed back to other customers |
| status | VARCHAR(20) | OPEN / ESCALATED / RESOLVED |
| created_at, updated_at | TIMESTAMPTZ | |

**RLS:** `customer_id = current_setting('app.current_customer_id')::uuid`.

**Access:** claims processor (RLS read/write — creates new complaint records as part of the customer-inquiry flow, reads only own-customer history). No other agent has direct access. The orchestrator reads only the `status` field to drive the ESCALATED transition.

This table backs FR9.6 (PRD) and the `complaint` intent path in the Customer Inquiry Workflow (TAD §3.3).

### 2.14 Ephemeral Runtime State — `trace_store` (non-persisted)

`backend/app/showcase/trace_store.py` holds an **in-memory TTL cache** (120 s) that bridges the two-phase playground pipeline. It is not a database table and survives only within a single server process.

| Field | Type | Notes |
|-------|------|-------|
| `trace_id` | `str` (UUID) | Key; issued by `POST /showcase/playground/submit` |
| `payload` | `str` | Original user text before sanitisation |
| `detections` | `list[str]` | Injection pattern IDs found by the sanitiser (e.g. `"delimiter_injection"`) |
| `chars_stripped` | `int` | Zero-width / format characters removed by the sanitiser |
| `sanitized` | `str` | `<untrusted>…</untrusted>`-wrapped text ready for the parser LLM |

**Access semantics:** `get()` (not `pop()`), so EventSource reconnects within the TTL window find the same entry. Expired entries are pruned lazily on next access. The `security_events` table (§2.11) captures the persistent defense record for the same submission; this store is purely a coordination mechanism.

---

## 3. Agent-to-Database Access Matrix

| Agent | customers | pii_vault | policies | vehicles | claims | evidence | fraud_scores | settlements | audit_log | RAG-public | RAG-conf | RAG-secret |
|-------|-----------|-----------|----------|----------|--------|----------|--------------|-------------|-----------|-----------|----------|-----------|
| Orchestrator | id only | — | — | — | stage only | — | decision only | status only | INSERT (via writer) | — | — | — |
| Intake parser | — | — | — | — | — | — | — | — | INSERT | — | — | — |
| Intake actor | id+name (RLS) | — | — | — | INSERT new only | — | — | — | INSERT | read | — | — |
| Identity verifier | — | function-only (no SELECT) | — | — | — | — | — | — | INSERT | — | — | — |
| Document parser | — | — | — | — | — | — | — | — | INSERT | — | — | — |
| Claims processor | — | — | RLS read own | RLS read own | RLS read own | RLS read sanitised | function-call only (returns full SECRET-labelled row to runtime; IFC strips downstream) | — | INSERT | — | read | read |
| Settlement actor | id+name+addr (RLS) | session-bound payee ref | — | — | RLS read own / update settlement fields | — | decision only | INSERT/UPDATE | INSERT | — | — | — |
| Adversarial agent (sandbox instance only) | — | — | — | — | — | — | — | — | INSERT (own instance) | — | — | — |

**RLS active on all customer-scoped tables.** Application-level WHERE clauses are still written for clarity and defense-in-depth, but RLS is the authoritative boundary — a missing WHERE does not produce a leak.

---

## 4. Information Flow Control (IFC) Schema

```python
# label hierarchy
PUBLIC < PERSONAL < CONFIDENTIAL < SECRET

# orthogonal taint
UNTRUSTED  # raw user-supplied bytes/text until structured by a parser

# every datum:
Labeled[T] = (value: T, label: Label, taint: set[Taint], provenance: list[str])
```

The IFC runtime:
- Joins labels on transformation: `label(f(x, y)) = max(label(x), label(y))`
- Joins taints similarly.
- Tools declare:
  - `min_label_to_invoke` (e.g. settlement payout requires CONFIDENTIAL-clean evidence)
  - `output_label` (e.g. `score_fraud` returns SECRET)
- The egress filter (P10) refuses any string-typed customer-visible value whose joined label is SECRET, or whose taint contains UNTRUSTED-not-structured.

Every label check writes one `capability_use` row to `audit_log`. The Console exposes a "label trace" view for any session showing how labels flowed.

---

## 5. Dataset Footprint

Drastically reduced from prior version. We need enough data to make the demo coherent and to give attacks something to target; not more.

| Item | Count | Source | Notes |
|------|-------|--------|-------|
| Claims | 30–50 | hand-curated from Kaggle Auto Insurance Claims (D1) | A representative spread across incident_type and severity |
| Customers + linked PII | 30–50 | Faker, deterministic seed | One per claim |
| Policies | 30–50 | synthesised | One per customer |
| Vehicles | 30–50 | synthesised from claim data | |
| Damage images | 20–30 | hand-picked from CarDD | Six damage categories covered |
| PDFs | ~15 | ~7 clean, ~8 adversarial | Hand-crafted attack PDFs are higher value than 200 LLM-generated PDFs |
| RAG public | ~10 docs | hand-written | FAQ, glossary |
| RAG confidential | ~10 docs | hand-written | Policy T&C templates |
| RAG secret | ~5 docs | hand-written | Fraud rules (for #17, #24 demonstrations) |
| Attack payloads | 53 text templates (159 phrasings) + 23 adversarial images + 32 adversarial PDFs | hand-built + adversarial-generated | Covers attack types #1 and #5 in depth; corpus grows as sprints complete |

### 5.1 Data preparation pipeline (one-shot)

```
Step 1: SAMPLE 50 representative claims from D1 (claims/sample.py)
Step 2: GENERATE Faker customers + PII vault (seed=42) (data/generate_customers.py)
Step 3: SYNTHESISE policies from claim policy fields (data/generate_policies.py)
Step 4: ASSIGN 1–3 damage images per claim from CarDD (data/assign_images.py)
Step 5: HAND-CRAFT PDFs (manual; lives in data/seeds/pdfs/)
Step 6: HAND-WRITE RAG corpus (manual; lives in data/seeds/rag/)
Step 7: BUILD attack payload corpus (data/attack_payloads/; see Doc 04 §3)
Step 8: LOAD into Postgres + ChromaDB via make seed
```

**Removed entirely:** Bitext intents (we have no intent classifier), Motor Vehicle Portfolio expansion (we have no policy lifecycle simulator), Vehicle Claim Fraud Detection expansion (we have no XGBoost model), 200 generated police reports (overkill), 200 generated estimates (overkill).

### 5.2 Stub models

| Stub | Replaces | Implementation |
|------|----------|----------------|
| `classify_damage(image_ref)` | CarDD CNN | Deterministic function: returns label from the evidence row's seeded `damage_classification` field. Confidence is hardcoded based on severity. |
| `score_fraud(claim_id)` | XGBoost | Rule-based: returns CLEAR/FLAG/DENY based on amount thresholds, time-since-policy, and a deliberately seeded "test fraud" flag for specific demo claims. Always returns the full record labelled SECRET. |
| `injection_classifier(text)` | Fine-tuned BERT | Off-the-shelf moderation API (e.g. OpenAI moderation) + curated pattern list. Used as a detection signal; not a primary defense. |

The Console is explicit about which paths are stubbed and why ("the fraud model is irrelevant to the resilience demonstration; a deterministic stub makes the architecture's response visible without ML noise").

### 5.3 Quality controls

| Check | Method | Threshold |
|-------|--------|-----------|
| PII uniqueness | seed-deterministic; assert no SSN/email collision | 100% |
| Amount consistency | `total = injury + property + vehicle` | zero violations |
| Date coherence | `incident_date BETWEEN policy_bind AND policy_expiry` | zero violations |
| Attack payload labelling | every payload tagged with attack IDs it exercises | 100% |
| Audit chain integrity (after seed) | `make verify-chain` | passes |

---

## 6. RAG Index Architecture

### 6.1 Three-tier isolation

```
ChromaDB instance
├── collection: public_faq       (PUBLIC, all-MiniLM-L6-v2, ~10 docs)
├── collection: policy_docs      (CONFIDENTIAL, ~10 docs)
└── collection: fraud_rules      (SECRET, ~5 docs, dedicated credential)
```

Each collection is fronted by a separate retriever function. The retriever:
1. Verifies the calling agent has a capability token whose `tool` field matches the collection's retriever name.
2. Tags each returned chunk with its source label.
3. Writes a `rag_retrieval` audit row.

The egress filter (P10) refuses any customer-visible string whose joined source label includes SECRET (defends #17, #24).

### 6.2 RAG corpus signing

Each RAG document is hashed; the hash manifest is signed (Ed25519). At indexing time the indexer verifies the manifest. Runtime queries do not re-verify (cost), but a daily integrity check does. This is the demonstration of P12 / #17 defense.

---

## 7. ER Summary

```
customers ──1:1──→ pii_vault
customers ──1:N──→ policies
customers ──1:N──→ vehicles
policies  ──1:N──→ claims
claims    ──1:N──→ evidence
claims    ──1:1──→ fraud_scores
claims    ──1:1──→ settlements
(all entities) ──N:1──→ audit_log
(all entities) ──N:1──→ security_events
(orchestrator+actors) ──N:1──→ capability_token_log
(identity verifier) ──N:1──→ identity_attempts
```

---

*End of Data Model & Schema Document — Document 3 of 6*
