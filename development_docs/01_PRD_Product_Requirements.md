# SecureClaim AI — Product Requirements Document (PRD)

**Version:** 2.0
**Date:** May 27, 2026
**Status:** Final v2.0
**Author:** Athish G R
**Classification:** Internal

---

## 1. Executive Summary

SecureClaim AI is a **security-first multi-agent reference architecture** built to demonstrate resilience against a 79-category curated taxonomy of agentic AI attacks. The system uses an auto-insurance claims pipeline as a realistic vehicle for adversarial testing — the domain is incidental; the architectural patterns and measured defenses are the product.

The artifact has two halves:

1. A **resilient agent system** built around a small set of architecturally rigorous patterns — deterministic orchestration, the dual-LLM (parser/actor) separation, information-flow labels, capability-scoped tools, sandboxed file processing, and an append-only hash-chained audit log.
2. A **public showcase platform** (the "Resilience Console") that lets any reviewer attempt attacks live, observe which defense layer fires, inspect the audit trail, and read a measured attack-defense matrix grounded in real telemetry.

The deliverable is a portfolio artifact whose primary audience is a technical reviewer assessing the builder's ability to design and ship a production-pattern resilient agentic system in a non-production environment.

---

## 2. Problem Statement

Modern agentic AI systems are exposed to attack surfaces no traditional application faces: prompt injection through any retrieved text, indirect injection through documents and images, multi-agent orchestration exploits, capability misuse, data exfiltration via legitimate-looking summarisation, and cascading failures across tool chains. Public reference implementations either treat security as a checklist of regexes and rate limits, or hand-wave it entirely.

The curated 79-category attack taxonomy (see `agentic_ai_attack_types.md`) synthesises OWASP Agentic Top 10, MITRE ATLAS, CSA MAESTRO, NIST AI RMF, and contemporary research. No existing open implementation engages this taxonomy end-to-end with measured outcomes.

Auto-insurance claims processing is chosen as the vehicle because it naturally exercises a wide cross-section of the taxonomy: untrusted document ingestion, multimodal input, multi-agent coordination, tiered data sensitivity, financial write operations, and ML model inference. Realism beyond what's necessary for adversarial coverage is explicit non-goal.

---

## 3. Project Objectives

| ID | Objective | Success Metric |
|----|-----------|----------------|
| O1 | Implement a minimal but coherent claims pipeline that exercises every attack class in the taxonomy | 4 specialist agents + deterministic orchestrator behind an interactive interface |
| O2 | Engineer at least one architectural defense pattern per attack class, with each pattern named, cited, and code-traceable | Defense pattern catalog complete; every attack ID maps to ≥1 pattern |
| O3 | Categorise each of the 79 attacks as live-tested / architecturally prevented / scoped-out, with a published rationale per item | 79/79 categorised; zero "unknown" status |
| O4 | For live-tested attacks, publish measured block rates, false-positive rates, and partial-leak counts based on real test runs | All live-test rows in the matrix carry numbers, not pass/fail |
| O5 | Build the Resilience Console showcase platform with a live attack playground a reviewer can use without supervision | Playground accessible publicly; sub-2s defense feedback |
| O6 | Run an autonomous adversarial agent against the system continuously and publish its results | Adversarial agent operational; results streamed to the Console |
| O7 | Produce a formal state-machine specification of the claim workflow and verify the implementation against it | TLA+ (or equivalent) spec + conformance test |

**Explicit non-goals:** real-world claim processing accuracy, realistic fraud-model performance, production-grade damage classifier accuracy, intent-classification breadth, multi-language support, mobile UI, regulatory compliance.

---

## 4. Target Audience

### 4.1 Technical Reviewer (Primary)
- **Profile:** Hiring manager, security engineer, AI safety researcher, principal engineer
- **Goal:** Assess in 10–20 minutes whether the builder genuinely understands resilient agentic-AI architecture
- **Behaviour:** Opens the Console, attempts a few injections in the playground, scans the attack-defense matrix, drills into one or two architectural defenses, glances at the GitHub repo
- **What convinces them:** Measured numbers, named patterns with citations, the ability to actually try attacks, the formal artifact, the autonomous adversarial agent

### 4.2 Red-Team Operator (Secondary)
- **Profile:** AI security researcher or curious practitioner
- **Goal:** Try to break the system in ways the builder did not anticipate
- **Behaviour:** Power-uses the playground, files issues on GitHub, possibly forks
- **What convinces them:** Depth of telemetry, replay-shareable URLs, public test suite, honest residual-risk register

### 4.3 Policyholder Persona (Demonstration Only)
- The "John, 34, files a fender-bender claim" persona exists only to drive the happy-path demo on the Console. No real product-management thinking about this persona is required.

### 4.4 Claims Adjuster Persona (Demonstration Only)
- The "Maria, senior adjuster" persona exists only to show escalation works. Not a real user.

---

## 5. Scope

### 5.1 In Scope

**Agent system (minimal viable for the showcase):**
- 4 specialist LLM agents: Intake Parser, Identity Verifier, Claims Processor, Settlement Actor
- Deterministic orchestrator (plain code, not an LLM)
- Dual-LLM separation: every untrusted input is parsed by a quarantined LLM into a strict schema before any privileged LLM acts on it
- Two intent surfaces sharing the same agents: new-claim filing AND customer inquiry (claim status / policy questions / FAQ / complaint capture)
- Stubbed fraud scoring and damage classification (deterministic functions, not trained models)

**Security primitives (the bulk of engineering effort):**
- Input sanitisation pipeline (text, image, PDF) with vision-redaction OCR pre-pass
- Information-flow labels on every datum (PUBLIC / PERSONAL / CONFIDENTIAL / SECRET / UNTRUSTED)
- Capability-scoped tool registry with server-side permission enforcement
- Per-agent Ed25519 signing keys for provenance on inter-agent messages
- PostgreSQL row-level security enforcing per-customer isolation
- Append-only audit log with row-level hash chain
- Sandbox container per file-processing job (no network, no filesystem outside scratch)
- LLM-agnostic output filter (PII regex, URL allowlist, label-aware redaction)

**Showcase platform (the Resilience Console — see Doc 06):**
- Interactive attack playground
- Architecture explorer
- Filterable attack-defense matrix with live numbers
- Live audit stream
- Autonomous adversarial agent live feed
- Defense pattern library with citations
- Happy-path claim demo

**Artifacts:**
- Formal state-machine specification (TLA+ or equivalent)
- Measured attack-defense report
- Residual-risk register
- Public GitHub repo
- 5-minute demo recording

### 5.2 Out of Scope
- Real ML model training (fraud, damage classification): stubs only
- Real data realism: 30–50 synthetic claims, ~15 documents (≈half clean, half attack payloads) is the entire dataset
- Bitext intent classification or any intent layer (orchestrator is a state machine)
- Production deployment to real insurance infrastructure
- Real payment integrations
- Mobile UI
- Regulatory compliance certification
- Multi-language support

---

## 6. Functional Requirements

### FR1: Claim Pipeline (Minimum Viable)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | System accepts a claim narrative via chat | P0 |
| FR1.2 | System accepts image upload (JPEG/PNG) of damage | P0 |
| FR1.3 | System accepts PDF upload (police report / repair estimate) | P0 |
| FR1.4 | System routes the claim through the deterministic state machine: INTAKE → IDENTITY → PROCESSING → SETTLEMENT → CLOSED | P0 |
| FR1.5 | System produces a settlement decision (auto-approve / escalate / deny) with a structured rationale | P0 |
| FR1.6 | System completes a happy-path claim end-to-end in a single browser session | P0 |

### FR2: Dual-LLM Separation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | Every piece of untrusted content (user text, OCR output, PDF text) is processed first by a quarantined LLM whose only output is a strict JSON schema | P0 |
| FR2.2 | Privileged LLMs receive only the structured output, never the raw untrusted text | P0 |
| FR2.3 | The quarantined LLM has no tool access | P0 |
| FR2.4 | Schema-validation failure quarantines the input and emits a security event | P0 |

### FR3: Information Flow Control

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Every datum in the system (DB row, message field, tool argument) carries an explicit trust label | P0 |
| FR3.2 | Tools declare their minimum required label; calls with insufficient label are rejected server-side | P0 |
| FR3.3 | Output filter denies any customer-visible response that would surface a SECRET-labelled value | P0 |
| FR3.4 | Label propagation is logged at every transformation | P1 |

### FR4: Deterministic Orchestration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Workflow transitions are decided by plain code, not by an LLM | P0 |
| FR4.2 | Each transition is gated by structured pre-conditions checked against the database, not against LLM output | P0 |
| FR4.3 | An LLM may propose the next step but a proposal that violates the state machine is rejected and logged | P1 |
| FR4.4 | The workflow has a published formal specification, and a conformance test confirms the implementation matches | P1 |

### FR5: Identity Verification (Capability Boundary Demonstration)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR5.1 | PII values are never placed in any LLM context (parser or actor) | P0 |
| FR5.2 | Identity comparison is performed by a server-side function returning only `{verified: bool, attempts_remaining: int}` | P0 |
| FR5.3 | Three failed attempts lock the session for the remainder of the demo run | P0 |

### FR6: Audit & Replay

| ID | Requirement | Priority |
|----|-------------|----------|
| FR6.1 | Every tool call, agent message, sanitisation event, and state transition writes one audit row | P0 |
| FR6.2 | Audit rows are hash-chained; tampering with any historical row breaks the chain | P0 |
| FR6.3 | Any session can be replayed in the Console, step by step, from the audit log | P0 |
| FR6.4 | Replays produce shareable URLs | P1 |

### FR7: Showcase Platform (See Doc 06 for detail)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR7.1 | Public Resilience Console with no login required for read-only and playground operations | P0 |
| FR7.2 | Attack playground accepts chat input, file uploads, and pre-loaded attack templates; shows layer-by-layer defense trace | P0 |
| FR7.3 | Architecture explorer renders the system as an interactive diagram with click-through detail panels | P0 |
| FR7.4 | Attack-defense matrix is filterable, sortable, and links each row to evidence | P0 |
| FR7.5 | Live audit stream shows real events as they occur, with filtering and replay | P0 |
| FR7.6 | Autonomous adversarial agent stream shows the bot's attempts and outcomes in near real time | P0 |
| FR7.7 | Command palette (cmd/ctrl+K) for power navigation | P1 |

### FR8: Autonomous Adversarial Agent

| ID | Requirement | Priority |
|----|-------------|----------|
| FR8.1 | A Claude-powered agent continuously attempts attacks from the taxonomy against a sandboxed instance | P0 |
| FR8.2 | The agent's prompt, attack strategy, and outcomes are logged and exposed in the Console | P0 |
| FR8.3 | Any successful breach increments a "successful breach" counter that is publicly visible | P0 |

### FR9: Customer Inquiry Path

The system handles non-claim-filing interactions as a first-class flow, exercising the same agents and security primitives against a different intent surface. No new agents or infrastructure are introduced — the intake parser classifies inbound chat into one of five intents and the orchestrator dispatches accordingly.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR9.1 | The intake parser classifies inbound chat into intent: `new_claim`, `faq`, `claim_status`, `policy_question`, `complaint` | P0 |
| FR9.2 | `faq` intent is answered by the intake actor using the PUBLIC RAG corpus, without requiring identity verification; the egress filter still applies | P0 |
| FR9.3 | `claim_status`, `policy_question`, and `complaint` intents require identity verification before any customer-scoped data is fetched | P0 |
| FR9.4 | Verified `claim_status` queries return claim stage and offered_amount via an RLS-scoped lookup, passed through the egress filter | P0 |
| FR9.5 | Verified `policy_question` intents are answered using an RLS-scoped policy fetch combined with CONFIDENTIAL RAG retrieval, with label-aware egress filtering | P0 |
| FR9.6 | `complaint` intent captures a structured complaint record, transitions the session to ESCALATED, and returns a generic acknowledgment | P0 |
| FR9.7 | The customer-inquiry path is testable in the Playground as a second attack surface alongside the claim-filing path, with category-specific attack templates | P0 |

---

## 7. Non-Functional Requirements

### NFR1: Resilience (Primary)

| ID | Requirement | Target |
|----|-------------|--------|
| NFR1.1 | Every attack ID in the taxonomy has either a live test case with a measured block rate or a documented architectural prevention with citation | 79/79 |
| NFR1.2 | Live-tested attacks have ≥30 input variants each | Median 30, minimum 10 |
| NFR1.3 | Cross-customer data leakage attempts blocked | 100% (architectural via RLS) |
| NFR1.4 | Direct prompt-injection variants reaching the privileged actor LLM | 0 (dual-LLM separation) |
| NFR1.5 | Honest "successful breach" counter on the Console | Publicly visible, updated in real time |

### NFR2: Showcase Quality

| ID | Requirement | Target |
|----|-------------|--------|
| NFR2.1 | Playground attack-to-defense-feedback latency | <2s p95 |
| NFR2.2 | Console page load (LCP) | <1.5s |
| NFR2.3 | Console accessibility | WCAG 2.1 AA |
| NFR2.4 | All Console claims are backed by linked telemetry or code references | No unbacked marketing copy |

### NFR3: Observability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR3.1 | End-to-end OpenTelemetry traces on every claim session | Trace per claim, span per agent step |
| NFR3.2 | Audit log retention for showcase | 30 days rolling |
| NFR3.3 | Security event alerting | Console banner + GitHub issue (manual or webhook) |

### NFR4: Cost Discipline

| ID | Requirement | Target |
|----|-------------|--------|
| NFR4.1 | Per-session LLM token budget enforced at the orchestrator | 50K tokens / session |
| NFR4.2 | Adversarial agent monthly spend cap | $50/month |
| NFR4.3 | Total monthly LLM spend cap | $200/month |

---

## 8. Data Requirements

### 8.1 Sensitivity Tiers (Information-Flow Labels)

| Tier | Label | Examples | Default access |
|------|-------|----------|----------------|
| T1 | PUBLIC | FAQs, glossary, public policy summaries | All agents, all users |
| T2 | PERSONAL | Name, email, claim status (own) | Owner-scoped agents only |
| T3 | CONFIDENTIAL | Policy details, claim amounts, damage reports | Authorised agents per role |
| T4 | SECRET | SSN, bank details, fraud rules, fraud reasoning | Specific agents via capability tokens, never in LLM context |
| T0 | UNTRUSTED | Raw user-supplied content (chat, uploads, OCR output) | Quarantined parser only |

### 8.2 Dataset Footprint (Minimal Deliberate Set)

| Item | Count | Source | Purpose |
|------|-------|--------|---------|
| Claims | 30–50 | Hand-curated subset of Kaggle Auto Insurance Claims | Enough to populate the demo and exercise the matrix |
| Customers + linked PII | 30–50 | Faker, deterministic seed | Identity verification demo |
| Policies | 30–50 | Synthesised to match claims | Coverage lookup demo |
| Damage images | 20–30 | Hand-picked from CarDD | Multimodal injection surface |
| PDFs (police reports / estimates) | ~15 total | ~7 hand-written clean, ~8 adversarial | Indirect injection surface |
| Public RAG docs | ~10 | Hand-written | Demonstration of public retrieval |
| Confidential RAG docs | ~10 | Hand-written | Demonstration of tiered retrieval |
| Secret RAG docs | ~5 | Hand-written | Demonstration of strict isolation |
| Attack payload corpus | 79 categories × ≥10 variants | Built by hand, by template, and by adversarial agent | The actual test suite |

**Cut from previous plan:** the 1,000 stitched claims, 105K Mendeley policies, XGBoost training set, Bitext intents, 400 generated PDFs. None of this serves the showcase goal.

---

## 9. Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| Attack taxonomy coverage | Each of 79 categorised as live-tested / architectural / out-of-scope with rationale | 79/79 with no "unknown" |
| Live-tested attacks with measured outcomes | Number of attack rows carrying real block-rate numbers | ≥40 |
| Architectural defenses with named pattern + citation | Number of defenses traceable to a named pattern in the catalog | All defenses |
| Live attack playground usable by reviewer | A reviewer can attempt three categories of attack without help in <5 min | Yes |
| Autonomous adversarial agent | Continuously running, results publicly visible | Yes |
| Formal state-machine artifact | Specification published, conformance test passes | Yes |
| Console publicly deployed | URL stable; uptime visible | Yes |
| GitHub repo published with reproducible setup | `make demo-up` boots the full stack locally | Yes |

---

## 10. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Adversarial agent finds a real bypass before launch | Embarrassing → portfolio strength | Medium | Treat as a feature: ship anyway, fix in public, show the audit trail |
| LLM cost overrun on adversarial agent | High | Medium | Hard monthly cap + Haiku-only model for the adversary |
| Console becomes the work, agent system underdeveloped | High | High | Build the agent system end-to-end first; Console comes after vertical slice works |
| Scope creep into the insurance domain (more agents, more realism) | High | High | Strict 4-agent cap; cuts itemised in §5.2 are firm |
| Formal spec turns into rabbit hole | Medium | Medium | Time-box TLA+ work to 1 week; degrade to documented invariants if needed |
| Reviewer dismisses as toy due to UI quality | Medium | Medium | Console design system is a first-class deliverable; see Doc 06 |

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| Dual-LLM pattern | Architectural separation between a quarantined LLM that parses untrusted input into structured form, and a privileged LLM that acts only on structured input |
| IFC (Information Flow Control) | Trust labels attached to data, propagated through computation, and enforced at action sites |
| Capability token | A signed grant authorising a specific agent to invoke a specific tool with specific scoped parameters |
| Resilience Console | The public showcase website; see Doc 06 |
| Adversarial agent | A continuously running LLM whose role is to attempt attacks from the taxonomy |
| Hash chain | A linked sequence of audit rows where each row's hash includes the previous row's hash; tampering breaks the chain |
| RLS (Row-Level Security) | PostgreSQL feature enforcing per-row access policies at the database |
| Sandbox | An isolated execution environment (container / process) with no network and restricted filesystem |
| 79-category taxonomy | The curated attack list in `agentic_ai_attack_types.md` |

---

*End of PRD — Document 1 of 6*
