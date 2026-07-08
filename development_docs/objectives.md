# SecureClaim AI — Objectives & System Capabilities Brief

**Purpose of this document:** Input brief for designing the Resilience Console — the public-facing showcase website for the SecureClaim AI project. This document describes what we are trying to achieve, who we are trying to convince, what the backend system can do, and what data and capabilities are available to expose in the UI. There are no frontend implementation constraints in this document; the goal is to give a complete picture of the system so the best possible UI can be designed from scratch.

---

## 1. What We Are Building

SecureClaim AI is a **security-first multi-agent reference architecture**. It uses an auto-insurance claims processing pipeline as a live, attackable specimen to demonstrate that agentic AI systems can be engineered to resist a rigorous, published taxonomy of 79 attack categories.

The insurance domain is incidental. The real product is the **architecture**: a set of named, composable, demonstrable defense patterns that make the agent system measurably resilient against the categories of attack that real agentic AI deployments face.

The **Resilience Console** is the public showcase website. Its job is to put that architecture in front of a technical reviewer and make it immediately, concretely credible — through live attack demonstrations, real telemetry, measured numbers, and deep architectural transparency.

---

## 2. Primary Goal

**Convince a senior technical reviewer, in 10–20 minutes of unsupervised exploration, that the builder genuinely understands how to design and ship a resilient multi-agent AI system.**

This is a portfolio artifact. The reviewer is assessing engineering depth, not insurance software. Every design decision in the Console should serve that single goal.

---

## 3. Target Audiences

### 3.1 Hiring Manager / Principal Engineer (highest priority)
- Has 5–15 minutes, probably unattended
- Wants to know: "Is this person credible? Do they understand real security engineering or did they just add a rate limiter and call it 'secure'?"
- Will open the site, poke around the most interactive thing they can find, look for numbers that back up claims, and then check the GitHub repo
- What convinces them: real measured numbers, named architectural patterns with citations, the ability to *actually try* attacks and see real responses, a formal artifact, an autonomous adversarial agent running live

### 3.2 AI Security Researcher (high priority)
- Wants to actually try to break the system in ways we didn't anticipate
- Will spend 15+ minutes, possibly returns multiple times
- What convinces them: full audit trail transparency, replay-shareable URLs, honest residual-risk register, public test suite, depth of telemetry

### 3.3 Curious Developer (medium priority)
- Wants to understand how the architecture is built
- 5 minutes, probably reads the architecture diagram and a pattern detail
- What convinces them: clear explanations, code references, the "how" is accessible

### 3.4 Non-Technical Recruiter (low priority)
- 30 seconds; forwards to a technical reviewer
- Needs: one clear headline and a visually credible impression of seriousness

---

## 4. What the Console Must Achieve at Each Time Horizon

| Time | What the reviewer must feel | How |
|------|-----------------------------|-----|
| 30 seconds | "This is serious, not a toy" | Live counters showing real attack attempts and defenses; no marketing prose; density of information signals depth |
| 5 minutes | "I can try to break this and see what happens" | Attack playground: fire a real attack, watch the defense trace layer by layer in real time, click through to audit evidence and source code |
| 20 minutes | "The architecture is deep and well-reasoned" | Named defense patterns with citations, interactive architecture diagram, 79-row attack-defense matrix with real numbers, adversarial agent live feed, session replay |
| On inspection | "They're honest about limits" | Residual risk register publicly visible, formal specification published, audit chain integrity verifiable on demand |

---

## 5. Design Philosophy (What the UI Should Feel Like)

These are constraints on tone and aesthetic, not implementation specifics.

- **Looks like a security operations console, not a SaaS marketing site.** Think: SOC dashboard, security research tool, terminal-adjacent. Not startup landing page.
- **Numbers, never adjectives.** "Blocked 153/153 variants" not "highly secure." Every claim must link to evidence.
- **Show the work.** Every defense links to the code that implements it, the test that verifies it, and the pattern that names it.
- **Real telemetry as first-class content.** Audit rows, OTel traces, security events render inline — the reviewer sees actual data, not stock screenshots.
- **Honesty builds more trust than polish.** The residual risk register and honest "successful breaches" counter (even if it's non-zero) are more persuasive than a perfect score.
- **Speed signals quality.** The site being fast is itself a credibility signal.
- **No decoration.** No hero illustrations, no stock photography, no testimonials, no marketing copy, no emoji in body content, no animated background gradients. Restraint signals seriousness.

---

## 6. The Backend Agent System

### 6.1 What the system does

The backend processes auto-insurance claims and customer inquiries through a pipeline of 4 specialist LLM agents coordinated by a deterministic code orchestrator. Every action is logged. Every security event is recorded and classified. The system continuously generates live telemetry that the Console can expose.

There is also an autonomous **adversarial agent** — a separate process that continuously attempts attacks from the taxonomy against a sandboxed instance of the system and streams its results.

### 6.2 The Deterministic Orchestrator

This is the most important component to understand. **The orchestrator is plain Python code, not an LLM.** It enforces a strict state machine for the claim workflow. LLMs suggest actions; the orchestrator code decides whether those actions are permitted. This eliminates an entire class of attacks (#43, #46) by construction.

**Claim workflow states:**
```
INTAKE → IDENTITY_PENDING → IDENTITY_VERIFIED → PROCESSING → DECIDED
→ SETTLED (if fraud=CLEAR and amount ≤ auto-approve limit)
→ ESCALATED (if fraud=FLAG/DENY or amount > limit)
→ DENIED
→ CLOSED
```

**Transition guards** (enforced in code, not by LLM):
- `INTAKE → IDENTITY_PENDING`: requires `intake_complete = true` in DB
- `IDENTITY_PENDING → IDENTITY_VERIFIED`: requires `identity_log.verified = true` for current session
- `PROCESSING → DECIDED`: requires non-null damage assessment + coverage calculation + fraud decision
- `DECIDED → SETTLED`: requires `fraud_decision = CLEAR` AND `amount ≤ auto_approve_limit`
- `DECIDED → ESCALATED`: requires fraud FLAG/DENY OR amount > limit
- No backward transitions. No stage skipping. Any attempt → `transition_violation` audit row.

The orchestrator also enforces:
- Per-session token budgets (50K tokens hard cap)
- Per-tool call budgets
- Circuit breakers after consecutive failures

### 6.3 The Four Specialist Actor Agents

#### Agent 1: Intake Actor
- **Role:** Decide intake outcome based on parsed structured input: `ready_for_identity` / `needs_more_info` / `reject_as_out_of_scope`. Also handles FAQ queries (no identity required, PUBLIC RAG only).
- **Model:** Claude Haiku 4.5
- **Tools available:** `request_more_info(field)`, `mark_intake_complete(structured_summary)`, `search_public_faq(query)`
- **Data label access:** PUBLIC and PERSONAL (own-claim scope only via RLS). Never sees raw user text — receives only structured JSON from the parser.
- **What it cannot do:** Access CONFIDENTIAL or SECRET data. Make workflow decisions. Write to the audit log directly (done via the audit writer role).

#### Agent 2: Identity Verifier
- **Role:** Coordinate identity verification. PII never touches its LLM context.
- **Model:** Claude Haiku 4.5
- **Tools available:** `request_identity_check(policy_number, dob_hint, ssn_last4)` — this is a server-side function call that compares against the PII vault and returns only `{verified: bool, attempts_remaining: int}`. The agent never sees the actual PII.
- **Data label access:** PERSONAL (the boolean result only).
- **Lockout:** 3 failed attempts per session lock the session.
- **What it cannot do:** Fetch raw PII. Read from the PII vault. Override the lockout.

#### Agent 3: Claims Processor
- **Role:** Compose the structured assessment: damage classification, coverage applicability, fraud signal, policy document lookup. Also handles post-identity customer inquiry intents (claim status, policy question, complaint capture).
- **Model:** Claude Sonnet 4.6 (the reasoning-heavy actor)
- **Tools available:**
  - `classify_damage(evidence_ref)` → returns damage label (deterministic stub)
  - `lookup_coverage(claim_id)` → coverage details (deterministic)
  - `score_fraud(claim_id)` → returns SECRET-labelled full record; only `decision` field (CLEAR/FLAG/DENY) is forwarded to the agent — risk score and factors are IFC-stripped before the LLM context
  - `search_policy_docs(query)` → CONFIDENTIAL RAG retrieval (capability-gated)
  - `search_fraud_rules(query)` → SECRET RAG retrieval (returns only doc_id + source reference, not rule text, to the agent)
  - `lookup_claim_status(claim_id)` → RLS-scoped claim stage + offered amount (for inquiry path)
  - `capture_complaint(session_id, category, description)` → writes to complaints table, triggers ESCALATED transition
- **Data label access:** CONFIDENTIAL within own claim scope. Cannot surface SECRET content to the LLM context or any customer output.
- **What it cannot do:** Access other customers' data (RLS enforced at DB layer). Surface fraud model scores or fraud rule text. Issue capability tokens.

#### Agent 4: Settlement Actor
- **Role:** Apply policy math, draft customer-facing settlement summary.
- **Model:** Claude Sonnet 4.6
- **Tools available:**
  - `calculate_settlement(claim_id)` → pure deterministic function (deductible + coverage limits)
  - `request_payout(claim_id)` → server-side; resolves session-bound payee; verifies orchestrator state is DECIDED, fraud is CLEAR, amount ≤ cap. Any failure → deny + audit.
  - `draft_summary(structured_decision)` → generates customer-facing prose; output goes through egress filter
- **Data label access:** CONFIDENTIAL within own claim scope. Bank details are session-bound and never enter agent context.
- **What it cannot do:** Choose the payee (it's pre-bound). Override fraud decisions. Modify the settlement amount directly.

### 6.4 The Quarantined Parser LLMs

Before any actor agent runs, **every piece of untrusted content** (user chat, OCR output from images, text extracted from PDFs) passes through a quarantined parser LLM.

- **Model:** Claude Haiku 4.5
- **Tools available:** **None. Zero tool access.**
- **Input:** Raw untrusted content wrapped in `<untrusted>` delimiters + a strict JSON schema
- **Output contract:** Strict JSON conforming to the registered schema. Any deviation → `parser_schema_violation` audit event + input quarantined.
- **What it parses:** Chat narrative → intake schema; OCR text → text-event schema; PDF text → document-fields schema; vision output → damage-observation schema; also classifies intent: `new_claim / faq / claim_status / policy_question / complaint`
- **Why this matters:** Actor LLMs downstream **never see raw user text**. Even a perfectly jailbroken parser is bounded: it produces only JSON, has no tools, and sees no data worth stealing. This is the most important single defense in the system.

### 6.5 The Autonomous Adversarial Agent

A separate process running Claude Haiku 4.5. Its purpose is to continuously attempt attacks from the 79-category taxonomy against a sandboxed instance of the system.

- **Isolation:** Separate container; can only reach the adversarial-test instance of the API (not the live showcase instance)
- **Budget:** Hard cap of $50/month
- **Strategy:** Rotates through attack categories; mutates payloads with feedback from blocked vs. partially-leaked outcomes; strategy is open-source and displayed verbatim
- **Output:** Every attempt → log entry → live Console stream; successful breaches → loud Console banner + auto-opened GitHub issue
- **Honesty:** The "successful breaches" counter is publicly visible and always accurate. The builder's competence is demonstrated by *handling* breaches transparently, not by claiming a perfect record.

---

## 7. The 12 Defense Patterns

These are the named architectural building blocks. Every defense in the system maps to one or more of these. They are the substance of the portfolio artifact — not individual security rules, but reusable architectural shapes with citations.

### P1 — Dual-LLM Separation
Quarantined parser LLM converts all untrusted input into a strict JSON schema. Privileged actor LLMs operate only on the schema output and never see raw user content.

**What it defeats:** Direct prompt injection (#1), indirect prompt injection (#2), cross-context injection (#3), jailbreaking (#4), semantic injection (#7), cross-modal injection (#6), zero-click injection (#8)

**The key insight:** The parser's compromise is bounded. It emits only JSON, has no tools, and sees no data worth stealing. Even a successfully jailbroken parser cannot trigger an action because actors downstream only accept structured input.

**References:** Simon Willison's "Prompt Injection Explained"; Anthropic Constitutional Classifiers paper

### P2 — Deterministic Orchestration
Workflow transitions are computed by plain code from database state. LLMs may suggest next steps; code decides whether the suggestion is permitted.

**What it defeats:** Agent goal hijack (#9), CoT manipulation (#11), orchestrator privilege escalation (#43), orchestration layer exploitation (#46), cascading failures (#61), goal misalignment cascade (#13, #64)

**The key insight:** There is no LLM in the orchestrator to compromise. Attack #46 (orchestration layer exploitation) is architecturally inapplicable. The state machine is formally specified (TLA+) and conformance-tested.

### P3 — Information Flow Control (IFC) Labels
Every datum in the system carries a trust label: `PUBLIC < PERSONAL < CONFIDENTIAL < SECRET`, plus orthogonal `UNTRUSTED` taint for raw user-supplied content. Tools declare minimum required label. The egress filter refuses any customer-visible response containing SECRET-labelled values.

**What it defeats:** Data exfiltration (#20–#28), RAG exfiltration (#24), indirect exfiltration (#21), summarisation exfiltration (#27), context poisoning (#16)

**Implementation:** Every DB column has a static label in the schema. Every tool declares its input and output labels. The egress filter (P10) is the enforcement point. Every label check writes an audit row.

**References:** Myers & Liskov "Complete, Safe Information Flow" (POPL '97)

### P4 — Capability-Scoped Tools
Every tool call carries a capability token signed by the orchestrator's Ed25519 private key. The token encodes: `agent_id × tool × scope (e.g. claim_id) × expiry`. The tool registry verifies all five fields server-side. The LLM cannot mint tokens. The LLM cannot widen scope.

**What it defeats:** Tool misuse (#29), confused deputy (#39), unsafe tool composition (#32), privilege abuse (#38), semantic layer exploitation (#10), semantic-layer exfiltration (#28)

**The key insight:** Even a perfectly jailbroken LLM is bounded by what the orchestrator issued a capability token for. "Convince the LLM to do X" does not work when X requires a token the LLM cannot produce.

**References:** Dennis & Van Horn capabilities model (1966); Object-capability model

Token structure:
```json
{
  "token_id": "uuid",
  "agent_id": "claims_processor",
  "tool": "score_fraud",
  "scope": { "claim_id": "CLM-000123" },
  "expires_at": "ISO-8601",
  "signature": "ed25519(...)"
}
```

### P5 — Sandboxed File Processing
All file parsing (PDF, image) runs in Docker containers with `--network=none`, read-only rootfs, and dropped capabilities. Ephemeral filesystems; no persistence between jobs. PDFs with JavaScript, embedded executables, or active forms are rejected before parsing begins.

**What it defeats:** Indirect prompt injection via PDF (#2), unexpected code execution (#30), sandbox escape (#68), zero-click injection (#8)

### P6 — Vision Pre-Redaction
Before any image reaches a vision model, an OCR pass identifies all text regions. Detected text bounding boxes are **pixel-blurred to opaque blocks**. The vision model receives the redacted image. The OCR text is sent separately through the text sanitisation pipeline as a distinct UNTRUSTED stream.

**What it defeats:** Cross-modal/multimodal injection (#6) — "ignore previous instructions" overlays, watermark-style injections, sticker text, low-contrast embedded instructions

**Why pixel-blur instead of text extraction:** Extracting and filtering the text doesn't prevent the vision model from "reading" it in its visual context. Pixel-blurring removes the visual information entirely.

### P7 — DB-Enforced Tenancy (RLS)
PostgreSQL row-level security policies enforce per-customer scope at the database layer, independent of application code. A missing WHERE clause in application code does not produce a cross-customer leak.

**What it defeats:** Direct data exfiltration (#20), cross-customer access (#28), session hijacking (#42), summarisation exfiltration (#27)

**Implementation:** `SET LOCAL app.current_customer_id = ...` on the connection after JWT verification. Every customer-scoped table has a RLS policy keyed to this setting. Even if the application layer is compromised, the DB layer enforces isolation.

### P8 — Per-Agent Asymmetric Identity
Each agent has its own Ed25519 keypair generated at deployment time. Inter-agent messages are signed. Recipients verify signatures against a published public-key registry. Compromise of one agent's key does not reveal any other agent's key.

**What it defeats:** Agent impersonation (#40), insecure inter-agent communication (#44), spoofed inter-agent messages (#47)

**Honest scope:** In the single-host demo, this is pattern demonstration, not a real network boundary. The architecture is designed so that promoting to a real multi-host deployment requires only swapping transports, not redesigning the identity model.

### P9 — Append-Only Hash-Chained Audit Log
Every tool call, agent message, sanitisation event, state transition, and security event writes one audit row. Each row's hash includes the previous row's hash:

```
row_hash = sha256(prev_hash || canonical_json(row_minus_hash))
```

The Postgres role for writing audit rows has INSERT only — no UPDATE, no DELETE granted to any application role. Tampering with any historical row breaks the chain, detectable on demand.

**What it defeats:** Log poisoning (#18); provides forensic recovery capability for all categories

**The Console can verify chain integrity on demand.** A public "audit integrity" badge shows last verification time.

### P10 — Egress Output Filter
Every customer-visible string passes through four steps in strict order (order is security-load-bearing):

1. **SECRET label kill-switch:** Any response containing a SECRET-labelled datum is immediately replaced with a generic message. Short-circuits everything else.
2. **URL strip:** Any URL not on the published allowlist is replaced with `[external link removed]`. Runs before PII check because URLs can contain PII patterns.
3. **PII regex:** SSN patterns, card formats, phone numbers → block response + audit on any hit.
4. **Output length cap:** Text truncated to MAX_OUTPUT_CHARS. Last step only — truncating earlier would discard PII in the tail without detection.

**What it defeats:** Indirect exfiltration (#21), URL-based exfiltration (#25), PII leakage (#26), steganographic exfiltration (#26), prompt extraction (#78)

### P11 — Token & Cost Budgets
Per-session token counter (50K hard cap), per-tool call counter, per-tool-per-minute rate limit, monthly spend caps, circuit breakers after consecutive failures.

**What it defeats:** Denial of wallet (#69), recursive tool call loops (#31), tool budget exhaustion (#34), semantic state accumulation (#19)

**Visible to reviewers:** The Console shows real-time cost for the adversarial agent (vs. monthly cap) and per-session token consumption.

### P12 — Signed System Prompts
A prompt registry holds the current system prompt for each agent. At runtime, each agent verifies that the loaded prompt's hash matches a signed manifest. A prompt change requires a reviewed pull request that updates the manifest.

**What it defeats:** Agent goal hijack (#9), behavioral drift (#14), RAG index poisoning (#17)

---

## 8. The Attack Taxonomy

79 distinct attack categories covering the full lifecycle of agentic AI exploitation. Synthesised from OWASP Agentic AI Top 10, MITRE ATLAS, CSA MAESTRO, NIST AI RMF, and additional research.

### Categories:
1. **Prompt & Input Manipulation** (#1–8): Direct injection, indirect injection via PDFs/images, cross-context injection, jailbreaking, adversarial examples, multimodal injection, semantic injection, zero-click injection
2. **Goal & Behavior Hijacking** (#9–14): Agent goal hijack, semantic layer exploitation, CoT manipulation, quiet mode drift, goal misalignment cascade, behavioral drift
3. **Memory & Context Attacks** (#15–19): Memory poisoning, context poisoning, RAG index poisoning, log poisoning, semantic state accumulation
4. **Data Exfiltration** (#20–28): Direct exfiltration, side-channel summarisation, model inversion, membership inference, RAG exfiltration, URL-based exfiltration, steganographic exfiltration, summarisation exfiltration, semantic-layer exfiltration
5. **Tool & Execution Attacks** (#29–37): Tool misuse, RCE via code execution, recursive tool loops, unsafe tool composition, cross-tool state leakage, denial of wallet, MCP tool poisoning, SQL injection via agent
6. **Identity, Privilege & Trust** (#38–43): Identity abuse, confused deputy, agent impersonation, credential/token compromise, session hijacking, orchestrator privilege escalation
7. **Multi-Agent & Orchestration** (#44–49): Insecure inter-agent communication, rogue agent injection, orchestration exploitation, spoofed messages, malicious agent collusion, steganographic collusion
8. **Supply Chain & Ecosystem** (#50–55): Supply chain vulnerabilities, ML supply chain compromise, package hallucination, poisoned tool publishing, repo-config exploitation, plugin supply chain
9. **Training & Model-Level** (#56–60): Data poisoning, model backdoor, model extraction, adversarial fine-tuning, training pipeline compromise
10. **Cascading & Systemic Failures** (#61–64): Cascading failures, hallucination propagation, cross-zone causality chains, goal misalignment cascade
11. **Human-Agent Trust Exploitation** (#65–67): Trust exploitation, social engineering via agent, authority spoofing
12. **Infrastructure & Runtime** (#68–72): Sandbox escape, denial of wallet, denial of service via loops, WebSocket hijacking, self-replicating agent worm
13. **AI as Offensive Weapon** (#73–75): AI-orchestrated cyberattack, autonomous ransomware, accelerated exfiltration
14. **Privacy & Inference** (#76–79): Model inversion, membership inference, prompt extraction, training data extraction

### Classification per attack:
- **LIVE (≥40 attacks):** Automated test suite with real payloads; measured block rates, partial-leak counts, false-positive rates published
- **ARCHITECTURAL (~30 attacks):** The architecture makes the attack inapplicable by construction; documented with named pattern + citation; assertion tests verify the architectural claim in CI
- **OUT-OF-SCOPE (≤10 attacks):** Honest scope statements (e.g., training-data attacks when no model is trained); rationale documented

---

## 9. The Ingress Sanitisation Pipeline

Every input goes through this pipeline before reaching any LLM:

### Text input:
1. Unicode NFKC normalisation; strip zero-width characters; strip RTL override characters
2. Static pattern detection (curated list of known injection templates)
3. Semantic classifier (moderation API + curated pattern list) — used as a **detection signal** (logged, surfaced in Console), not as the primary defense
4. UNTRUSTED label attached; input wrapped in `<untrusted>` delimiters

### Image input:
1. EXIF / XMP / IPTC metadata stripped; image re-encoded
2. **Vision pre-redaction (P6):** OCR pass identifies text regions → pixel-blur bounding boxes → vision model receives redacted image; OCR text → separate UNTRUSTED text stream
3. Lightweight steganography heuristics (LSB chi-square) — flagged images quarantine + audit but do not auto-block (heuristic only)

### PDF input:
1. Parse in sandboxed container (no network, ephemeral filesystem, restricted syscalls)
2. Reject PDFs with JavaScript, embedded executables, or active forms
3. Hidden-content detection: white-on-white, microscopic font, off-page content
4. Extracted text → text sanitisation pipeline → UNTRUSTED label → parser LLM

---

## 10. Data Model Overview

### Data labels and what they mean
| Label | What it contains | Who can access |
|-------|-----------------|----------------|
| PUBLIC | FAQs, glossary, public policy summaries | All agents, all users |
| PERSONAL | Name, email, claim status (own only) | Owner-scoped agents via RLS |
| CONFIDENTIAL | Policy details, claim amounts, damage reports | Authorised agents per role |
| SECRET | SSN, bank details, fraud rules, fraud scores | Server-side functions only; **never in any LLM context** |
| UNTRUSTED | Raw user-supplied content (chat, uploads, OCR output) | Quarantined parser LLM only |

### Key entities and their labels
- **customers** (PERSONAL): name, contact info, DOB — per-agent column-level grants; no agent has direct SELECT on DOB
- **pii_vault** (SECRET): Argon2id-hashed SSN, AES-256-GCM encrypted bank account and drivers license — **no agent has DB access**; only server-side `verify_identity()` function can read it
- **policies** (CONFIDENTIAL): coverage type, deductible, auto-approve limit — RLS-scoped
- **claims** (CONFIDENTIAL): incident description stored escaped, claim stage — RLS-scoped
- **evidence** (CONFIDENTIAL): sanitised artefact only; raw bytes are ephemeral in sandbox; both original and sanitised SHA-256 kept for forensic integrity
- **fraud_scores** (SECRET): risk score and risk factors are SECRET (never in LLM context); only `decision` field (CLEAR/FLAG/DENY) is forwarded
- **settlements** (CONFIDENTIAL): offered amount, payout status
- **audit_log** (CONFIDENTIAL, append-only, hash-chained): every action; INSERT-only for application roles
- **capability_token_log** (CONFIDENTIAL): every token issued and used
- **security_events** (CONFIDENTIAL): every defense firing, classified by taxonomy attack ID
- **complaints** (CONFIDENTIAL): RLS-scoped; written by claims processor on complaint intent; triggers ESCALATED transition

### Agent-to-database access matrix
| Agent | customers | pii_vault | policies | claims | evidence | fraud_scores | settlements | audit_log |
|-------|-----------|-----------|----------|--------|----------|--------------|-------------|-----------|
| Orchestrator | id only | — | — | stage only | — | decision only | status only | INSERT |
| Intake actor | id+name (RLS) | — | — | INSERT new only | — | — | — | INSERT |
| Identity verifier | — | function-only (no SELECT) | — | — | — | — | — | INSERT |
| Claims processor | — | — | RLS read own | RLS read own | RLS read sanitised | function-call; IFC strips SECRET fields | — | INSERT |
| Settlement actor | id+name+addr (RLS) | session-bound payee ref only | — | RLS own / update settlement | — | decision only | INSERT/UPDATE | INSERT |

---

## 11. Available Live Data Feeds

The backend exposes Server-Sent Events (SSE) streams. These are the live data channels available to the Console:

### SSE: `/sse/audit`
Continuous stream of audit log rows as they are written. Every tool call, state transition, sanitisation event, capability token use, and security event appears here in real time. Each row contains: timestamp, trace_id, agent_id, action type, target, data label, whether it's a security event.

### SSE: `/sse/adversarial`
Continuous stream of the adversarial agent's attempts. Each event contains: attack category, payload (redacted if needed), target endpoint, outcome, which defense layer blocked it, duration.

### SSE: `/sse/health`
System status and aggregate counters every 5 seconds: attacks tried today, blocked count, successful breaches count, which patterns are currently armed, current adversarial agent status, API health.

### SSE: `/sse/playground/{trace_id}`
Per-submission 7-layer defense trace stream for the attack playground. Emits one `layer_result` event per defense layer as it executes, then a final `verdict` event. This is what powers the live defense trace in the playground.

---

## 12. The Attack Playground — Backend Capability

The playground runs the **full production defense pipeline** on every submission. It is not a simulation.

### Submit endpoint: `POST /showcase/playground/submit`
Accepts a raw text payload (or file upload). Runs it through the full ingress sanitisation pipeline. Stores a `TraceEntry` in an ephemeral in-memory store (120s TTL). Returns immediately with `{ trace_id, sse_url, attack }`.

The `TraceEntry` captures:
- `payload`: original user text
- `detections`: list of injection pattern IDs found (e.g., `["delimiter_injection", "role_switch_attempt"]`)
- `chars_stripped`: count of zero-width/format chars removed
- `sanitized`: `<untrusted>...</untrusted>`-wrapped text

### Defense trace stream: `GET /sse/playground/{trace_id}`
Runs all 7 defense layers in sequence, yielding one event per layer:

| Layer | Defense pattern | What runs |
|-------|----------------|-----------|
| 1 — Ingress Sanitisation | P1 | Encoding normalisation results, chars stripped |
| 2 — Pattern Detection | P3 | Injection pattern matches found |
| 3 — Semantic Classifier | P3 | Live Claude Haiku call; classifies adversarial intent; blocks if confidence ≥ 0.7 |
| 4 — Untrusted Tagging | P3 | `<untrusted>` wrapping applied |
| 5 — Parser LLM | P1 | Live `run_intake_parser()` call; blocks on schema violation |
| 6 — Actor LLM | P2 | Live `run_intake_actor()` with ephemeral capability tokens |
| 7 — Egress Filter | P10 | Live `filter_output()`: SECRET kill-switch → URL strip → PII regex → length cap |

Final `verdict` event contains: attack vector matched (taxonomy ID + name), outcome (BLOCKED/PARTIAL/PASSED), what data was surfaced (if any), how many audit rows were written, which security events fired.

### What the playground can accept
- Free-form text injection payloads
- Pre-loaded attack templates (from taxonomy categories)
- PDF file uploads (adversarial PDFs: white-on-white hidden text, embedded JS, micro-font, off-page content)
- Image file uploads (adversarial images: overlay text, sticker-style injections, watermarks, low-contrast embedded text)
- Tool-misuse simulation: select an agent, select a tool it shouldn't have, observe capability-token denial
- Cross-customer probe: attempt to access another customer's data, observe RLS denial

### Two attack surfaces
The playground can target either:
1. **Claim-filing path** — the main pipeline (intake → identity → processing → settlement)
2. **Customer-inquiry path** — the service path (FAQ, claim status, policy question, complaint)

Many attacks have surface-specific templates for each path. This matters because real attackers commonly target customer service surfaces, not just claim intake.

---

## 13. REST API Capabilities (Showcase)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/showcase/matrix` | Full 79-row attack-defense matrix with measured numbers per row |
| GET | `/showcase/matrix/{attack_id}` | Single attack detail: defenses, code refs, test refs, recent attempt samples |
| GET | `/showcase/patterns` | All 12 defense patterns with summaries |
| GET | `/showcase/patterns/{id}` | Full pattern detail: problem, pattern shape, implementation, citations, defenses, residual risk |
| GET | `/showcase/architecture` | Live architecture metadata: nodes, edges, current health, recent traffic per node |
| GET | `/showcase/sessions/{trace_id}` | Full replay payload for a session |
| GET | `/showcase/formal` | Formal spec status: invariant check results, conformance test results, last-run timestamp |

### Matrix row structure (what's queryable per attack)
```json
{
  "attack_id": 1,
  "name": "Direct Prompt Injection",
  "class": "LIVE",
  "patterns": ["P1", "P10"],
  "variants_tried": 153,
  "blocked": 153,
  "partial_leak": 0,
  "false_positives_on_clean": 2,
  "last_run_ts": "ISO-8601",
  "duration_ms": 184211,
  "median_block_layer": "parser_schema_violation"
}
```

---

## 14. Formal Specification

The claim workflow state machine is formally specified in TLA+ (`formal/workflow.tla`).

**8 state variables:** `stage`, `intake_complete`, `identity_verified`, `damage_assessed`, `coverage_calculated`, `complaint_captured`, `fraud_decision`, `settlement_amount`

**11 workflow transitions** (mirroring the code's `_VALID_EDGES`)

**4 safety invariants:**
- **TypeOK:** All variables stay in declared domains throughout
- **ClosedIsAbsorbing:** Once a claim reaches CLOSED, it stays CLOSED
- **ForwardProgress:** All transitions are strictly rank-increasing (no cycles, no backward movement)
- **EventualClosure:** Every execution eventually closes (liveness property under weak fairness)

**Verification:** Python BFS exhaustive checker (`formal/check_spec.py`) enumerates the bounded state space (≤ 3,456 states). **30 invariant tests** verify the spec model. **102 conformance tests** drive the real `advance_stage()` implementation against the spec edge set — all 11 valid edges accepted, all 70 invalid pairs rejected.

The Console can expose: the TLA+ source rendered, the reachable state diagram, live invariant check status with last-run timestamp, conformance test pass/fail.

---

## 15. Audit Chain Verification

The audit log is hash-chained. The Console can:
- Display the current chain head hash
- Trigger on-demand chain verification (recomputes the entire chain from genesis)
- Display last-verification timestamp
- Show a "chain integrity" badge (green = verified clean, red = broken)
- Stream new audit rows in real time

The `security_events` table feeds a filterable security-event view where every defense firing is recorded with: event type, taxonomy attack ID (if applicable), severity, trace_id, timestamp, full JSONB details.

---

## 16. Session Replay

Every session (claim filing, inquiry, playground submission) is replayable. The replay payload contains:
- All audit rows for the trace, in order
- All agent messages (structured envelopes, not raw text)
- All tool calls and their results (IFC-safe views)
- All state transitions and their guards
- All security events

From a `trace_id`, the Console can reconstruct:
- What the claim state was at every point in time
- Which tool was called when, with what scope
- Which defense fired at which layer
- What the parser produced from the raw input
- What the actor proposed and whether the orchestrator accepted it

Replay URLs should be shareable (encode the `trace_id`).

---

## 17. Three Demo Scenarios the System Can Run End-to-End

### Happy path — minor claim
Customer files a fender-bender claim. Intake parses it. Identity verified. Claims processor classifies damage as minor + coverage applies + fraud score CLEAR. Settlement calculated deterministically. Payout requested. Claim CLOSED.

### Fraud-flagged claim
Claims processor's `score_fraud` tool returns FLAG/DENY decision. Orchestrator transitions to ESCALATED (not SETTLED). Customer receives escalation acknowledgment (not settlement amount). Demonstrates that fraud decisions made by the stub are respected by the deterministic orchestrator.

### Identity failure
Customer fails identity verification 3 times. Session locked. All subsequent requests denied. Audit log shows 3 `identity_fail` events followed by `session_locked`. Demonstrates lockout is enforced at the server-side function level, not conversationally.

**Inquiry path scenarios:**
- FAQ (no identity required) — demonstrates PUBLIC RAG + egress filter
- Claim status lookup (identity required) — demonstrates RLS-scoped retrieval
- Policy question (identity required) — demonstrates CONFIDENTIAL RAG + label-aware egress filtering
- Complaint capture — demonstrates structured capture + ESCALATED transition
- Identity failure on inquiry — same lockout behaviour, different path

---

## 18. What We Want a Reviewer to Walk Away Knowing

After 20 minutes on the Console, a technical reviewer should be able to honestly say:

1. **"I tried to inject into the system and could see exactly why it failed at each layer."** — The playground trace makes defense reasoning transparent.
2. **"The architecture has a clear shape — a small set of principled patterns, not a pile of one-off checks."** — The defense pattern library names and explains each pattern.
3. **"The numbers are real."** — The matrix shows real test run counts, timestamps, and outcomes — not invented figures.
4. **"An autonomous attacker is running against this right now and I can see what it's finding."** — The adversarial agent feed is live.
5. **"The state machine is formally verified."** — The formal spec page shows the TLA+ source + conformance test results.
6. **"They're honest about what doesn't work."** — The residual risk register names 13 specific limitations with root causes.
7. **"I can trace any claim to its raw telemetry."** — Session replay reconstructs every decision.
8. **"The system is actually running — this isn't a mockup."** — Audit rows, security events, and adversarial attempts stream live.

---

## 19. What the Console Should NOT Do

These are anti-patterns that would undermine the artifact's credibility with technical reviewers:

- Use vague or marketing language ("highly secure", "next-generation", "enterprise-grade") anywhere
- Show a single metric without linking to its source or methodology
- Simulate or mock the defense pipeline — the playground must run against the real system
- Claim zero breaches without showing the adversarial agent is actually running
- Obscure residual risks or limitations — honesty is more persuasive than a perfect score
- Present the insurance domain as the product — it is a testbed, not the point
- Look like a SaaS landing page, startup website, or marketing brochure
- Show anything that a technically skeptical reviewer would identify as filler

---

## 20. Summary: What We Have to Work With

| Capability | Available |
|-----------|-----------|
| Live 7-layer defense traces (SSE) | Yes — per playground submission |
| Real-time audit log stream (SSE) | Yes — continuous |
| Adversarial agent live feed (SSE) | Yes — continuous |
| System health + aggregate counters (SSE) | Yes — every 5s |
| 79-row attack-defense matrix with measured numbers | Yes |
| 12 named defense patterns with full detail | Yes |
| Per-agent specifications (role, model, tools, label access) | Yes |
| Interactive architecture metadata (nodes, edges, health) | Yes |
| Session replay (full audit reconstruction from trace_id) | Yes |
| Formal specification (TLA+ source, invariant check results) | Yes |
| Capability token log (every issuance and use) | Yes |
| Security events (classified by taxonomy attack ID) | Yes |
| Audit chain integrity verification (on-demand) | Yes |
| Three claim demo scenarios + five inquiry scenarios | Yes |
| Residual risk register (13 named items) | Yes |
| Code references (GitHub line-anchored) for every defense | Yes |
| Test references (file + run) for every LIVE attack | Yes |
| Pre-loaded attack templates for playground | Yes |

The backend is feature-complete for the showcase. The Console's job is to make all of this accessible, credible, and compelling to a technical reviewer who is deciding whether the builder knows what they're doing.
