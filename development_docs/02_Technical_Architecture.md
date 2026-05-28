# SecureClaim AI — Technical Architecture Document (TAD)

**Version:** 2.0
**Date:** May 27, 2026
**Status:** Final v2.0
**Author:** Athish G R
**Classification:** Internal

---

## 1. Architecture Overview

SecureClaim AI is organised around a small set of **named architectural defense patterns**, each defending a defined slice of the 79-category attack taxonomy. The goal of the architecture is not to maximise feature surface but to make each defense visible, traceable, and demonstrable.

### 1.1 Architecture Principles

| Principle | Rationale |
|-----------|-----------|
| **Patterns over heuristics** | A regex filter is a tactic; the dual-LLM pattern is an architecture. We invest in patterns first, regexes second. |
| **Deterministic where possible** | LLMs are not used for routing, state transitions, math, or authorisation. They are used for parsing and for prose generation. Everywhere else is plain code. |
| **Untrusted data never reaches a privileged actor** | All untrusted content (chat, OCR, PDF text) is parsed by a quarantined LLM into a strict schema. Privileged actors see only the schema. |
| **Information flow is labelled and enforced** | Every datum carries a trust label. Tools refuse insufficient labels. Output filter denies customer-visible SECRET-labelled data. |
| **Capabilities, not conversation** | Tools require capability tokens signed for a specific agent and scope. The LLM never authorises itself; the registry does. |
| **Fail closed, log loudly** | When uncertain, deny and emit a security event. Every denial is publicly auditable in the Console. |
| **Observable by construction** | Every action writes an audit row. Audit rows are hash-chained. OpenTelemetry traces are emitted by default. |

### 1.2 Defense Pattern Catalog

This catalog is the architectural backbone. Every defense in the threat model (Doc 04) maps to one or more of these patterns.

| Pattern | What it does | Attack IDs primarily defended |
|---------|--------------|-------------------------------|
| **P1 — Dual-LLM Separation** | Quarantined parser LLM converts untrusted input into a strict JSON schema; privileged actor LLMs operate only on the schema and never see raw user content. | #1, #2, #3, #6, #7, #8 |
| **P2 — Deterministic Orchestration** | Workflow transitions are computed by plain code from database state; LLM may suggest, code decides. | #9, #11, #13, #46, #43, #61–64 |
| **P3 — Information Flow Control (IFC) Labels** | Every datum carries a trust label propagated through transformations and enforced at action sites. | #20, #21, #24, #26, #27, #28 |
| **P4 — Capability-Scoped Tools** | Tools require capability tokens signed for a specific agent, action, and parameter scope. LLM cannot "convince" the registry. | #29, #32, #33, #38, #39 |
| **P5 — Sandboxed File Processing** | All file parsing runs in network-isolated containers with restricted syscalls and ephemeral filesystems. | #2, #6, #8, #30, #35, #68 |
| **P6 — Vision Pre-Redaction** | Images are OCR-pre-processed; detected text regions are pixel-redacted before the image reaches the vision model. | #6 (multimodal injection) |
| **P7 — DB-Enforced Tenancy (RLS)** | PostgreSQL row-level security policies enforce per-customer scope at the database layer, independent of application code. | #20, #28, #37 |
| **P8 — Per-Agent Asymmetric Identity** | Each agent has its own Ed25519 keypair; messages are signed; verification uses public keys. Compromise of one agent does not reveal others. | #40, #44, #47 |
| **P9 — Append-Only Hash-Chained Audit** | Every action writes one row; each row's hash includes the previous row's hash; tampering breaks the chain. | #18, plus forensic recovery for all categories |
| **P10 — Egress Output Filter** | All customer-visible output passes through a filter that strips PII patterns, denies non-allowlisted URLs, and refuses to surface SECRET-labelled values. | #21, #25, #26, #66, #78 |
| **P11 — Token & Cost Budgets** | Per-session token budget, per-agent tool budget, monthly spend caps, circuit breakers. | #31, #34, #69, #70 |
| **P12 — Signed System Prompts** | Prompt registry; runtime verifies prompt hash against signed manifest; prompt change requires reviewed PR. | #9, #14, #57 |

### 1.3 High-Level Architecture

```
                ┌──────────────────────────────────────────────────────────────┐
                │                  RESILIENCE CONSOLE (web)                     │
                │   playground · architecture explorer · matrix · audit feed    │
                └──────┬─────────────────────────────────────────────┬─────────┘
                       │                                              │
                       │ public API                       telemetry / SSE
                       ▼                                              ▲
                ┌─────────────────────────────────────────────────────────────┐
                │                    APPLICATION API (FastAPI)                 │
                └──────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │              INGRESS SANITISATION PIPELINE                    │
                │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
                │  │ Encoding │ │ Pattern  │ │ Semantic │ │ Vision OCR   │    │
                │  │ Normalise│ │ Detect   │ │ Classify │ │ Redact (P6)  │    │
                │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
                │  ┌──────────────┐ ┌──────────────────────────────────────┐  │
                │  │ PDF Sandbox  │ │ Untrusted-Label Tagging              │  │
                │  │ (P5)         │ │ (every output labelled UNTRUSTED)    │  │
                │  └──────────────┘ └──────────────────────────────────────┘  │
                └──────┬──────────────────────────────────────────────────────┘
                       │ schema-validated, label-tagged inputs
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │      QUARANTINED PARSER LLMs (no tool access) — P1           │
                │  emit only strict JSON per schema; raw text never forwarded  │
                └──────┬──────────────────────────────────────────────────────┘
                       │ structured JSON only
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │      DETERMINISTIC ORCHESTRATOR (plain code) — P2            │
                │  state machine · pre-condition gates · token budget          │
                └──┬──────┬───────┬───────┬──────────────────────────────────┘
                   │      │       │       │ structured task envelopes
                   ▼      ▼       ▼       ▼
              ┌─────────┐ ┌───────────┐ ┌──────────────┐ ┌──────────────┐
              │ Intake  │ │ Identity  │ │ Claims       │ │ Settlement   │
              │ Parser  │ │ Verifier  │ │ Processor    │ │ Actor        │
              │ (LLM)   │ │ (LLM thin)│ │ (LLM + tools)│ │ (LLM + tools)│
              └────┬────┘ └─────┬─────┘ └───────┬──────┘ └──────┬───────┘
                   │            │               │               │
                   └────────────┴───────────────┴───────────────┘
                       │ tool invocations via capability-token gate (P4)
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │              TOOL REGISTRY (server-side enforcement)         │
                │  every call: agent_id × tool × params × capability_token     │
                └──────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │   DATA ACCESS LAYER (per-agent DB roles + Postgres RLS — P7) │
                │  customers · pii_vault · policies · claims · evidence ·      │
                │  fraud_scores · settlements · audit_log (P9)                 │
                └──────┬──────────────────────────────────────────────────────┘
                       │
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │              EGRESS OUTPUT FILTER (P10)                      │
                │  PII regex · URL allowlist · label-aware redaction           │
                └──────┬──────────────────────────────────────────────────────┘
                       │ filtered, customer-safe response
                       ▼
                ┌─────────────────────────────────────────────────────────────┐
                │            OBSERVABILITY (OpenTelemetry + Audit DB)          │
                │  spans · structured logs · security events · live SSE feed   │
                └─────────────────────────────────────────────────────────────┘

         ┌───────────────────────────────────────────────────────────────┐
         │   ADVERSARIAL AGENT (separate process, isolated network egress)│
         │   continuously attacks a sandboxed instance; results → Console │
         └───────────────────────────────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Deterministic Orchestrator (P2)

| Property | Value |
|----------|-------|
| **Implementation** | Plain Python (or Go) state machine. No LLM. |
| **Responsibilities** | Hold claim state, validate transitions, dispatch task envelopes to agents, enforce token and tool budgets per session, emit audit rows for every step. |
| **Inputs** | Structured task results from agents. Database state. |
| **Outputs** | Task envelopes to specific agents with capability tokens scoped to expected work. |
| **State machine** | INTAKE → IDENTITY_PENDING → IDENTITY_VERIFIED → PROCESSING → DECIDED → (SETTLED \| ESCALATED \| DENIED) → CLOSED |
| **Pre-conditions** | Each transition is gated by structured DB checks. e.g. `PROCESSING → DECIDED` requires `damage_assessment IS NOT NULL AND coverage_calculation IS NOT NULL`. |
| **Token & budget enforcement** | Per-session token counter; per-tool call counter; hard caps configurable. Exceedance halts the session and emits a security event. |
| **Formal spec** | Workflow specified in TLA+ (or PlusCal); conformance test re-derives reachable states from code and compares to spec. |

**This component never calls an LLM.** When an agent suggests a next step that violates the state machine, the orchestrator rejects it and writes a `transition_violation` audit row. Attack #46 (orchestration layer exploitation) is architecturally not applicable: there is no LLM here to compromise.

### 2.2 Quarantined Parser LLMs (P1)

| Property | Value |
|----------|-------|
| **Role** | Parse untrusted content into strict JSON. Nothing else. |
| **Model** | Claude Haiku 4.5 (cost-efficient; fast) |
| **Tool access** | **None**. The parser has zero tool calls available. |
| **Output contract** | Strict JSON conforming to a registered schema. Any deviation triggers `parser_schema_violation` audit and quarantines the input. |
| **Context contents** | Only the untrusted content (wrapped in `<untrusted>` delimiters) and the schema. No DB data, no other claim history, no policy details. |
| **What gets parsed** | Chat narrative → intake schema; OCR text → text-event schema; PDF text → document-fields schema; vision output → damage-observation schema. |

The parser is the system's untrusted-content membrane. Its compromise is bounded: it produces only JSON, has no tools, and sees no data worth stealing. Privileged actors downstream never see the original text.

### 2.3 Specialist Actor Agents

Each actor receives only structured envelopes from the orchestrator. None reads raw user input.

#### 2.3.1 Intake Actor (post-parser)

| Property | Value |
|----------|-------|
| **Role** | Decide intake outcome: ready_for_identity / needs_more_info / reject_as_out_of_scope, based on the parser's structured output. |
| **Model** | Claude Haiku 4.5 |
| **Tools** | `request_more_info(field)`, `mark_intake_complete(structured_summary)`, `search_public_faq(query)` |
| **Data label access** | PUBLIC, PERSONAL (own-claim-scope only via RLS), UNTRUSTED-derived structured fields. |

#### 2.3.2 Identity Verifier

| Property | Value |
|----------|-------|
| **Role** | Coordinate identity verification. PII never touches its context. |
| **Model** | Claude Haiku 4.5 |
| **Tools** | `request_identity_check(policy_number, dob_hint, ssn_last4)` → server-side compares to PII vault, returns `{verified, attempts_remaining}`. |
| **Data label access** | PERSONAL (the boolean result only). The agent literally cannot fetch raw PII via any tool. |
| **Lockout** | 3 attempts per session; lockout written to audit. |

#### 2.3.3 Claims Processor

| Property | Value |
|----------|-------|
| **Role** | Compose the structured assessment: damage classification, coverage applicability, fraud signal. Each is fetched via a deterministic tool, not reasoned about. |
| **Model** | Claude Sonnet 4.6 (the most reasoning-heavy actor) |
| **Tools** | `classify_damage(evidence_ref)` (returns stub-deterministic label), `lookup_coverage(claim_id)`, `score_fraud(claim_id)` (returns CLEAR/FLAG/DENY only — never the score), `search_policy_docs(query)` (CONFIDENTIAL RAG) |
| **Data label access** | CONFIDENTIAL within own claim scope. Cannot read SECRET. |
| **Output** | Structured assessment envelope to the orchestrator. Free-text rationale is generated separately and runs through the egress filter. |

#### 2.3.4 Settlement Actor

| Property | Value |
|----------|-------|
| **Role** | Apply policy math (via deterministic tool), draft customer-facing settlement summary. |
| **Model** | Claude Sonnet 4.6 |
| **Tools** | `calculate_settlement(claim_id)` (pure function, deterministic), `request_payout(claim_id)` (server-side; resolves session-bound payee), `draft_summary(structured_decision)` |
| **Data label access** | CONFIDENTIAL within own claim scope. Bank details are session-bound and never enter context. |
| **Payout guard** | `request_payout` server-side verifies: orchestrator state is `DECIDED`, fraud signal is `CLEAR`, amount is within configured limit, payee is the session-bound payee. Any failure denies and audits. |

### 2.4 Tool Registry & Capability Tokens (P4)

Every tool call carries a capability token:

```json
{
  "token_id": "uuid",
  "agent_id": "claims_processor",
  "tool": "score_fraud",
  "scope": { "claim_id": "CLM-000123" },
  "expires_at": "2026-05-27T14:35:00Z",
  "signature": "ed25519(...)"
}
```

The registry verifies:
1. Token signature against the orchestrator's public key.
2. `agent_id` matches the calling process's authenticated identity.
3. `tool` matches the requested tool.
4. `scope` matches the requested parameters (e.g. `claim_id` in the call equals `scope.claim_id`).
5. `expires_at` is in the future.

The LLM cannot mint tokens. The LLM cannot widen scope. Even a perfectly jailbroken LLM is bounded by what the orchestrator issued capability for.

### 2.5 Ingress Sanitisation Pipeline

#### 2.5.1 Text input

1. Unicode NFKC normalisation; strip zero-width characters and RTL overrides.
2. Static-pattern detection (curated list of known injection templates).
3. Semantic classifier (fine-tuned BERT or off-the-shelf moderation API) — used as a **detection signal** (logged, surfaced in the Console), not as the primary defense. The primary defense remains structural (P1 dual-LLM).
4. UNTRUSTED label attached, wrapping in `<untrusted>` delimiters.

#### 2.5.2 Image input

1. EXIF / XMP / IPTC metadata stripped; image re-encoded.
2. **Vision pre-redaction (P6):** OCR pass identifies text regions; detected text bounding boxes are pixel-blurred to opaque blocks. The vision model receives the redacted image. The OCR text goes through the text sanitisation pipeline as a separate UNTRUSTED stream.
3. Lightweight steganography heuristics (LSB chi-square); flagged images quarantine and audit but do not block (heuristic only).

#### 2.5.3 PDF input

1. Parse in sandboxed container (P5): no network egress, ephemeral filesystem, restricted syscalls. Reject PDFs with JavaScript, embedded executables, or active forms.
2. Hidden-content detection: white-on-white, microscopic font, off-page content. All extracted text passes through the text sanitisation pipeline.
3. Extracted text labelled UNTRUSTED and emitted as text-event to the parser LLM.

### 2.6 Information Flow Control (P3)

Trust labels: `PUBLIC < PERSONAL < CONFIDENTIAL < SECRET`, plus orthogonal `UNTRUSTED` taint.

Implementation:
- Every DB column has a static label in the schema.
- Every tool declares minimum required label for each parameter and the label of its return value.
- Every message field carries a label.
- The **egress filter (P10)** denies any customer-visible response containing SECRET-labelled values, and redacts UNTRUSTED-derived text that escapes the parser without being structured.

The IFC system is a runtime library, not a static type system — but the runtime checks are mandatory and bypass would require code modification. Every label check writes an audit row.

### 2.7 Per-Agent Asymmetric Identity (P8)

- Each agent process boots with its own Ed25519 keypair (generated at deployment, stored in the deployment's secret store; in the local demo, generated at compose time and held in named volumes).
- Inter-agent messages are signed; the recipient verifies against a published public-key registry.
- The orchestrator signs capability tokens with its own key.
- **Honest scoping:** in the single-host demo this is pattern demonstration, not a real network boundary. The architecture document and Console both label this as such. The pattern is built so that promoting to a real network deployment requires only swapping transports, not redesign.

### 2.8 Append-Only Hash-Chained Audit Log (P9)

```
audit_log:
  log_id BIGSERIAL,
  trace_id UUID,
  prev_hash CHAR(64),
  row_hash CHAR(64),
  agent_id, action, target, details JSONB,
  data_label VARCHAR(20),
  security_event BOOLEAN,
  ts TIMESTAMP
```

- `row_hash = sha256(prev_hash || canonical_json(row_minus_hash))`
- Postgres role: `audit_writer` has `INSERT` only. No `UPDATE` or `DELETE` is granted to any role except a separate, manually-invoked `audit_admin` used only for retention-policy pruning that itself writes a `chain_rebase` event.
- The Console can verify chain integrity on demand; a public "audit integrity" badge shows last verification time.

### 2.9 Egress Output Filter (P10)

Every customer-visible string passes through:
1. PII regex (SSN, common card formats, phone patterns) → block + audit.
2. URL allowlist (only docs.secureclaim.example, status.secureclaim.example) → strip + audit on violation.
3. Label-aware redaction: if any source label of the response is SECRET, the response is replaced with a generic message and the original is logged for forensic review (but not shown to the customer).
4. Output length cap to limit slow-extraction attacks.

### 2.10 Adversarial Agent

A separate process running Claude Haiku 4.5 with a system prompt instructing it to attempt attacks from the taxonomy against a sandboxed instance of SecureClaim AI. Its results stream live to the Console.

| Property | Value |
|----------|-------|
| **Isolation** | Runs in a separate container; can only reach a dedicated adversarial-test instance of the API (not the showcase instance) |
| **Budget** | Hard cap of $50/month via per-call cost accounting |
| **Strategies** | Rotates through attack categories from the taxonomy; uses generated payloads, mutates them with feedback from blocked vs. partially-leaked outcomes |
| **Output** | Every attempt → log entry → Console live feed; successful breaches → loud Console banner + open GitHub issue |

---

## 3. Inter-Agent Communication

### 3.1 Message Schema

```json
{
  "message_id": "uuid",
  "trace_id": "uuid",
  "source_agent": "orchestrator|intake|identity|processor|settlement|parser_*",
  "target_agent": "...",
  "message_type": "task | task_result | event",
  "claim_id": "CLM-XXXXXX",
  "payload": {
    "schema": "registered_schema_name@version",
    "data": { ... }
  },
  "labels": { "data": "PERSONAL", "elements": { "field1": "SECRET" } },
  "capability_token": { ... },
  "signature": "ed25519(...)",
  "timestamp": "ISO-8601"
}
```

Validation order (every hop): schema validation → signature verification → label propagation rules → orchestrator-permitted-edge check → audit row write.

### 3.2 Claim Filing Workflow

```
                ┌─────────┐
                │ INTAKE  │
                └────┬────┘
                     │ intake_complete (structured)
                     ▼
              ┌──────────────────┐
              │ IDENTITY_PENDING │◄──┐
              └────┬─────────────┘   │ retry (≤3)
                   │ verified=true   │
                   ▼                 │ verified=false
            ┌──────────────────┐     │
            │ IDENTITY_VERIFIED│─────┘
            └────┬─────────────┘
                 │
                 ▼
            ┌────────────┐
            │ PROCESSING │
            └────┬───────┘
                 │ assessment_complete (damage + coverage + fraud)
                 ▼
            ┌──────────┐
            │ DECIDED  │
            └─┬───┬──┬─┘
              │   │  │
   auto-approve   │  │ deny
   & fraud_clear  │  │
              ▼   │  ▼
        ┌───────┐ │ ┌────────┐
        │SETTLED│ │ │ DENIED │
        └───┬───┘ │ └────────┘
            │     │ above threshold OR fraud_flag
            │     ▼
            │  ┌───────────┐
            │  │ ESCALATED │
            │  └───────────┘
            ▼
        ┌────────┐
        │ CLOSED │
        └────────┘
```

Transition guards (enforced in code):
- `INTAKE → IDENTITY_PENDING`: requires `claim_drafts.intake_complete = true`
- `IDENTITY_PENDING → IDENTITY_VERIFIED`: requires `identity_log.verified = true` for current session
- `IDENTITY_VERIFIED → PROCESSING`: orchestrator-initiated only
- `PROCESSING → DECIDED`: requires non-null `damage_assessment`, `coverage_calculation`, `fraud_score.decision`
- `DECIDED → SETTLED`: requires `fraud_score.decision = 'CLEAR'` AND `settlement.amount ≤ auto_approve_limit`
- `DECIDED → ESCALATED`: requires `fraud_score.decision IN ('FLAG','DENY')` OR `settlement.amount > auto_approve_limit`
- No backward transitions. No stage-skipping. Any attempted violation → `transition_violation` event.

### 3.3 Customer Inquiry Workflow

In addition to new-claim filing, the system handles customer service interactions as a first-class flow. No new agents and no new infrastructure are introduced — the same four actors, the parser pair, the orchestrator, the tools, the RAG indices, and every security primitive serve both flows. The intake parser classifies inbound chat into one of five intents and the orchestrator dispatches accordingly.

```
                        ┌──────────────────────┐
                        │    SESSION_OPEN      │
                        │ (intake parser       │
                        │  classifies intent)  │
                        └──────────┬───────────┘
                                   │
        ┌──────────┬───────────────┼───────────────┬──────────────┐
        ▼          ▼               ▼               ▼              ▼
   new_claim     faq         claim_status   policy_question   complaint
        │          │               │               │              │
        │          │               └───────┬───────┴──────────────┘
        │          │                       │
        │          │                       ▼
        │          │             ┌──────────────────┐
        │          │             │ IDENTITY_PENDING │ (required)
        │          │             └────────┬─────────┘
        │          │                      │ verified
        │          │                      ▼
        │          │             ┌──────────────────┐
        │          │             │IDENTITY_VERIFIED │
        │          │             └────────┬─────────┘
        │          ▼                      ▼
        │  ┌──────────────┐    ┌──────────────────────────┐
        │  │ FAQ_ANSWERED │    │ INQUIRY_HANDLED          │
        │  │ (intake actor│    │ (claims processor:        │
        │  │ + PUBLIC RAG)│    │  RLS lookup ± RAG ±       │
        │  │              │    │  complaint capture →      │
        │  │              │    │  ESCALATED if complaint)  │
        │  └──────┬───────┘    └────────────┬─────────────┘
        │         │                         │
        ▼         └────────────┬────────────┘
   (enters claim               │
    filing flow §3.2)          ▼
                        ┌──────────────┐
                        │SESSION_CLOSED│
                        └──────────────┘
```

**Intent routing rules** (deterministic; enforced by the orchestrator, not by the LLM):

- `new_claim` → enters the claim filing state machine (§3.2)
- `faq` → handled by intake actor with PUBLIC RAG retrieval only; no identity required; egress filter still applies
- `claim_status`, `policy_question`, `complaint` → require IDENTITY_VERIFIED before any customer-scoped data fetch
- `claim_status` → claims processor performs RLS-scoped lookup on the claimant's own claims; returns stage + offered_amount via egress filter
- `policy_question` → claims processor combines RLS-scoped policy fetch with CONFIDENTIAL RAG retrieval; answer drafted by actor; label-aware egress filtering
- `complaint` → claims processor captures a structured row in the `complaints` table (see Doc 03 §2.13), transitions the session to ESCALATED, returns an acknowledgment

**Why this matters for the showcase.** Many real attacker behaviours target customer service surfaces rather than claim intake — social engineering, cross-customer status snooping, RAG-based policy-detail extraction, complaint-form-based injection. Including this path makes the demonstrations representative of production attacker behaviour and gives the Playground a second, distinct attack surface against which #1, #21, #27, #28, #65, #66, and #78 are tested with surface-specific payloads.

### 3.4 Formal Specification

The workflow state machine is specified in TLA+ (file `formal/workflow.tla`). The spec defines:
- State variables: claim stage, identity state, decision result.
- Actions: each transition with its guards.
- Invariants:
  - `SettlementImpliesClearance`: `stage = SETTLED ⇒ fraud_decision = CLEAR ∧ identity_verified`
  - `NoSkipping`: every reachable state is preceded by exactly the legal predecessor set
  - `NoUnbounded`: every session has bounded transitions
- A test (`test_workflow_conformance.py`) enumerates reachable states in the implementation and verifies they match the spec.

---

## 4. Resilience Console — Architecture Snapshot

(Full spec in Doc 06.)

The Console is a Next.js application hosted independently of the agent system. It consumes:

- **REST API** for static reads (matrix data, defense pattern docs, recent attacks).
- **Server-Sent Events** for live audit stream and adversarial agent feed.
- **WebSocket** for the playground's bidirectional attack/defense session.

The agent system exposes a dedicated `/showcase` API surface, read-only for everything except the playground submission endpoint. The Console never holds privileged credentials.

---

## 5. Technology Stack

### 5.1 Core

| Component | Technology | Rationale |
|-----------|------------|-----------|
| LLM provider | Anthropic Claude API | Best instruction-following; Haiku for cost-sensitive paths, Sonnet for reasoning |
| Agent runtime | Plain Python with explicit async; no agent framework | Frameworks hide control flow; we want every decision visible |
| State machine | Pure Python module + TLA+ spec | Determinism is a feature |
| Primary DB | PostgreSQL 16 with RLS | Architecture-level tenancy |
| PII vault | Postgres with field-level encryption + KMS-style local key file | Demonstrates the pattern |
| RAG store | ChromaDB (local) | Adequate for ≤25 docs across 3 tiers |
| Sandbox | Docker containers with `--network=none`, read-only rootfs, drop-all capabilities | Reproducible isolation |
| API layer | FastAPI | Async, native JSON schema |
| Observability | OpenTelemetry → local Tempo/Jaeger + structured JSON logs | Industry standard, demonstrable |
| Local orchestration | Docker Compose | One-command boot |

### 5.2 Security

| Component | Technology | Purpose |
|-----------|------------|---------|
| Inter-agent signing | Ed25519 via libsodium / cryptography library | Asymmetric per-agent identity |
| Secret hashing | Argon2id + per-deployment pepper | PII vault (SSN, security answer) |
| At-rest encryption | AES-256-GCM with per-field keys | bank_account, drivers_license |
| Schema validation | Pydantic v2 | Strict input contracts |
| Output filter | Custom + Microsoft Presidio (PII detection) | Defense in depth |
| Rate limiting | Token bucket per agent/session/tool | DoW prevention |
| Adversarial agent | Claude Haiku 4.5 + isolated container + spend cap | Continuous adversarial testing |

### 5.3 Showcase Platform

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Framework | Next.js 15 (App Router) | SSR + RSC; serious framework |
| Styling | Tailwind + shadcn/ui | Professional baseline, full customisation |
| State | TanStack Query for server state | Cache-aware, observable |
| Live data | Server-Sent Events for streams; native WebSocket for playground | Standard primitives |
| Diagrams | React Flow for architecture explorer | Interactive, accessible |
| Charts | Visx (D3 wrapper) | Production-grade, accessible |
| Code rendering | Shiki | Terminal-style accurate highlighting |
| Hosting | Vercel | Frictionless deploy; edge logs |
| Auth (for adversarial-instance admin only) | Magic-link via Resend | Lightweight |

---

## 6. Deployment Architecture

### 6.1 Local Development

```
┌────────────────────────────────────────────────────────────────┐
│                      docker-compose stack                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ api          │  │ postgres     │  │ chromadb           │    │
│  │ (FastAPI)    │  │ (with RLS)   │  │ (3 collections)    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ parser_llm   │  │ orchestrator │  │ pdf_sandbox        │    │
│  │ (process)    │  │ (process)    │  │ (--network=none)   │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ image_sbx    │  │ otel-collector│ │ tempo + grafana    │    │
│  │ (sandboxed)  │  │              │  │ (observability)    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
│  ┌──────────────┐  ┌──────────────────────────────────────┐    │
│  │ adversarial  │  │ console (Next.js dev server)         │    │
│  │ (isolated)   │  │                                      │    │
│  └──────────────┘  └──────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 Directory Structure

```
secureclaim-ai/
├── agent_system/
│   ├── orchestrator/                   # deterministic state machine
│   │   ├── state_machine.py
│   │   ├── transitions.py
│   │   └── budgets.py
│   ├── parser/                         # quarantined parser LLMs
│   │   ├── intake_parser.py
│   │   ├── document_parser.py
│   │   └── schemas/                    # strict JSON schemas
│   ├── actors/                         # privileged actor LLMs
│   │   ├── intake_actor.py
│   │   ├── identity_verifier.py
│   │   ├── claims_processor.py
│   │   └── settlement_actor.py
│   ├── tools/
│   │   ├── registry.py                 # capability-token enforcement
│   │   └── implementations/
│   ├── sanitisation/
│   │   ├── text.py
│   │   ├── image.py                    # includes vision pre-redaction
│   │   └── pdf.py
│   ├── ifc/                            # information flow control
│   │   ├── labels.py
│   │   ├── propagation.py
│   │   └── enforcement.py
│   ├── identity/
│   │   ├── keys.py                     # Ed25519 keypair management
│   │   └── signing.py
│   ├── audit/
│   │   ├── log.py                      # append-only with hash chain
│   │   └── verify.py                   # chain integrity check
│   └── egress/
│       └── filter.py                   # P10
├── adversarial_agent/
│   ├── strategy.py
│   └── runner.py
├── formal/
│   ├── workflow.tla
│   ├── workflow.cfg
│   └── conformance_test.py
├── console/                            # Next.js Resilience Console
│   ├── app/
│   ├── components/
│   └── lib/
├── data/
│   ├── seeds/                          # 30–50 claims, 15 PDFs, 25 images
│   ├── attack_payloads/                # 79 categories × variants
│   └── rag_corpus/
│       ├── public/
│       ├── confidential/
│       └── secret/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── red_team/
│       ├── 01_prompt_input/
│       ├── 02_goal_hijack/
│       ├── ...
│       └── conftest.py
├── docs/                               # this document set
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## 7. API Design

### 7.1 Customer-Facing (used by the embedded demo on the Console)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/claims` | Create new claim |
| POST | `/api/v1/claims/{id}/messages` | Send chat message |
| POST | `/api/v1/claims/{id}/uploads` | Upload evidence (returns sanitisation status) |
| GET | `/api/v1/claims/{id}` | Status |

### 7.2 Showcase API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/showcase/matrix` | Full attack-defense matrix with numbers |
| GET | `/showcase/matrix/{attack_id}` | Single attack: defenses, code refs, recent attempts |
| GET | `/showcase/patterns` | Defense pattern catalog |
| GET | `/showcase/architecture` | Live architecture metadata (nodes, edges, current health) |
| GET | `/showcase/sessions/{trace_id}` | Replay payload for a session |
| GET | `/showcase/sse/audit` | Server-sent events: live audit stream |
| GET | `/showcase/sse/adversarial` | Server-sent events: adversarial agent feed |
| POST | `/showcase/playground/submit` | Submit an attack attempt; returns trace_id |
| WS | `/showcase/playground/stream/{trace_id}` | Live defense-trace stream |

### 7.3 Internal (per-agent JWT + capability token required)

Tool invocation endpoints, parser LLM calls, audit writes. Not exposed externally.

---

## 8. Failure Modes & Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Parser returns invalid JSON | Schema validator | Quarantine input, emit `parser_schema_violation`, return generic decline to user |
| Actor agent timeout (>15s) | Orchestrator | Retry once with lower temperature; second failure → ESCALATED |
| Capability token signature invalid | Tool registry | Deny + audit + alert |
| Hash chain integrity check fails | Audit verifier | Loud Console banner; quarantine instance |
| LLM provider unavailable | Health check | Halt new sessions; existing sessions degrade to deterministic-only path where possible |
| Token budget exceeded | Orchestrator | Halt session, ESCALATED, audit |
| Adversarial agent finds successful breach | Adversarial logger | Loud Console banner + open issue; do not auto-disable (transparency) |
| Output filter denies SECRET surface | Filter | Replace with generic, audit original; user-visible message: "Cannot share that detail" |

---

*End of Technical Architecture Document — Document 2 of 6*
