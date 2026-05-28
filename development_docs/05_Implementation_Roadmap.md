# SecureClaim AI — Implementation Roadmap

**Version:** 2.0
**Date:** May 27, 2026
**Status:** Final v2.0
**Author:** Athish G R
**Classification:** Internal

---

## 1. Phase Overview

The plan is **security-primitives-first**. Agents are built into the security gauntlet rather than retrofitted with it. The Resilience Console (Doc 06) is a first-class deliverable, not a polish item, but its build is parallelisable once the API contracts are stable.

```
Phase 1: Security Primitives & Foundation       (Weeks 1–2.5)
Phase 2: Vertical Slice                          (Weeks 2.5–4)
Phase 3: Console + Attack Playground             (Weeks 4–6)        ← runs in parallel with Phase 4
Phase 4: Remaining Agents & Adversarial Agent    (Weeks 4–7)
Phase 5: Hardening, Measurement, Docs            (Weeks 7–9)
Phase 6: Showcase Polish & Launch                (Weeks 9–11)
```

```
            ┌──────────────────┐
            │ Phase 1          │
            │ Security         │
            │ primitives       │
            └────────┬─────────┘
                     │
                     ▼
            ┌──────────────────┐
            │ Phase 2          │
            │ Vertical slice   │
            │ (1 claim E2E)    │
            └────────┬─────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
      ┌────────────┐  ┌─────────────────┐
      │ Phase 3    │  │ Phase 4          │
      │ Console +  │  │ Remaining agents │
      │ playground │  │ + adversarial    │
      └──────┬─────┘  └────────┬────────┘
             │                 │
             └────────┬────────┘
                      ▼
            ┌──────────────────┐
            │ Phase 5          │
            │ Hardening, full  │
            │ matrix, formal   │
            │ spec, docs       │
            └────────┬─────────┘
                     ▼
            ┌──────────────────┐
            │ Phase 6          │
            │ Console polish,  │
            │ launch, video    │
            └──────────────────┘
```

---

## 2. Phase 1 — Security Primitives & Foundation (Weeks 1–2.5)

### Goal
Every architectural defense pattern is implemented and unit-tested before any agent code exists.

### Sprint 1.1 — Foundation (Week 1, Days 1–3)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 1.1.1 | Repo bootstrap; Docker Compose skeleton; Postgres+ChromaDB+OTel-collector+Tempo+Grafana | `make up` boots stack | 4 |
| 1.1.2 | DB schema with RLS policies on all customer-scoped tables (Doc 03 §2) | Migrations applied, RLS tests pass | 5 |
| 1.1.3 | Per-agent DB roles with scoped GRANTs (Doc 03 §3) | Role tests pass: each role can only see/do what matrix says | 4 |
| 1.1.4 | Audit log table + hash-chain implementation + `verify_chain` job | Inserting rows produces verifiable chain | 5 |
| 1.1.5 | Seed data: 30–50 claims + customers + policies + vehicles (Doc 03 §5) | `make seed` populates a clean instance | 4 |
| 1.1.6 | OpenTelemetry SDK wired into FastAPI skeleton | Trace appears in Tempo | 2 |

### Sprint 1.2 — Defense Primitives (Week 1.5–2)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 1.2.1 | Ed25519 keypair manager + signing helpers (P8) | `sign_message`, `verify_message` | 3 |
| 1.2.2 | Capability token issuer + registry verifier (P4) | tokens persisted in `capability_token_log` | 5 |
| 1.2.3 | Tool registry with server-side scope enforcement | Sample tool: bad scope → denied + audited | 4 |
| 1.2.4 | IFC label types + propagation helpers (P3) | `Labeled[T]`, join, taint | 4 |
| 1.2.5 | Egress output filter (P10) | PII scrub + URL allowlist + label-aware redaction; unit-tested | 5 |
| 1.2.6 | Text sanitiser: Unicode normalisation, zero-width strip, pattern detection, untrusted tagging | text sanitiser + tests | 4 |
| 1.2.7 | PII vault: Argon2id with pepper; AES-256-GCM for fields | `verify_identity()` function-only access, unit-tested | 4 |

### Sprint 1.3 — Sandboxes & Vision Pre-Redaction (Week 2–2.5)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 1.3.1 | PDF sandbox container (`--network=none`, read-only rootfs, drop-caps) (P5) | sandbox container + parse_pdf RPC | 6 |
| 1.3.2 | Image sandbox container | same for images | 4 |
| 1.3.3 | Vision pre-redaction pipeline (P6): OCR pass → text-region detection → pixel-blur → store redacted artefact | unit-tested with 5 sample images including overlay attacks | 6 |
| 1.3.4 | Hidden-content detection for PDFs (white-on-white, micro-font, off-page) | unit-tested with sample adversarial PDFs | 4 |
| 1.3.5 | Deterministic orchestrator skeleton: state machine + transition guards + budget counters (P2, P11) | state transitions + audited; rejects invalid | 6 |
| 1.3.6 | Signed system prompt registry (P12) | prompt manifest signed; runtime verifies on load | 3 |

**Phase 1 Milestone:** All twelve defense patterns implemented and unit-tested **before** any agent exists. `make test-primitives` passes. Audit chain verifiable. RLS prevents cross-customer reads. Sandboxes have no network access (verified).

---

## 3. Phase 2 — Vertical Slice (Weeks 2.5–4)

### Goal
One end-to-end claim runs through the entire security gauntlet using the minimum agent set. The pipeline shape is proven before fan-out.

### Sprint 2.1 — Parser + Intake (Week 2.5–3)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 2.1.1 | Schema definitions for parser outputs (intake, document, vision-observation) | Pydantic v2 schemas; schema-violation handling | 3 |
| 2.1.2 | Quarantined intake parser LLM (Claude Haiku 4.5; no tools) | Parser running; schema enforced; audit trail | 4 |
| 2.1.3 | Intake actor LLM with capability-token-gated tools | Intake actor produces structured intake_complete envelope | 4 |
| 2.1.4 | Identity verifier actor + server-side compare function | Identity verification end-to-end, PII never in context | 5 |
| 2.1.5 | Stub claims processor (returns hardcoded structured assessment) | Vertical slice continues through processor | 3 |
| 2.1.6 | Stub settlement actor (returns hardcoded settlement) | Vertical slice reaches SETTLED | 3 |

### Sprint 2.2 — Vertical Slice Integration (Week 3.5–4)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 2.2.1 | End-to-end test: chat → intake → identity → processing(stub) → settlement(stub) → CLOSED | Passing test with audit-chain verification | 5 |
| 2.2.2 | Inter-agent message signing wired (P8) | Messages signed and verified | 3 |
| 2.2.3 | Capability tokens issued at every tool call; verified server-side | Sample bad-scope call denied and audited | 3 |
| 2.2.4 | First five LIVE attack tests run against the slice: #1 direct injection, #20 cross-customer, #29 tool misuse, #37 SQL injection, #43 orchestrator privilege escalation (architectural-assertion test) | All five tests pass; numbers logged | 6 |

**Phase 2 Milestone:** One claim end-to-end. Five attacks tested. Audit chain verifiable across the run. `make test-vertical-slice` passes. **This is the earliest point a reviewer could meaningfully see the system; ship a tiny demo here.**

---

## 4. Phase 3 — Console + Attack Playground (Weeks 4–6) — runs parallel with Phase 4

### Goal
The Resilience Console exists, deployed publicly, with the playground operational.

### Sprint 3.1 — Console Skeleton (Week 4)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 3.1.1 | Next.js 15 app scaffold; shadcn/ui baseline; dark-mode design tokens | `console/` boots locally + on Vercel preview | 4 |
| 3.1.2 | Design system: type scale, monospace blocks, code rendering (Shiki), motion primitives | Storybook of primitives | 6 |
| 3.1.3 | Showcase API spec finalised (REST + SSE + WS) | OpenAPI spec | 3 |
| 3.1.4 | Public showcase API endpoints: matrix, patterns, architecture metadata | Endpoints return real data | 4 |

### Sprint 3.2 — Attack Playground (Week 4.5–5.5)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 3.2.1 | Playground UI: split pane (attack input / defense trace) | Working chat + upload + template picker | 8 |
| 3.2.2 | WebSocket stream of defense events from playground submission to UI | Layer-by-layer trace renders in real time | 6 |
| 3.2.3 | "Defense fired" component: which pattern, which attack ID match, audit row link | Reviewer can click through to evidence | 5 |
| 3.2.4 | Attack template library: 20+ pre-loaded attack starting points across categories | Templates load and run with one click | 4 |
| 3.2.5 | Replay system: every session → shareable URL → loads exact trace | Replay URLs work | 5 |

### Sprint 3.3 — Architecture Explorer + Matrix (Week 5.5–6)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 3.3.1 | Interactive architecture diagram (React Flow); clickable nodes; detail panel | Click → see agent spec, tools, label access | 8 |
| 3.3.2 | Attack-defense matrix dashboard: filter / sort / drill into evidence | Working with live numbers | 6 |
| 3.3.3 | Live audit stream page (SSE) with filtering | Real audit events stream as they happen | 4 |

**Phase 3 Milestone:** Console deployed publicly (Vercel). Playground works for at least 10 attack categories. Architecture explorer interactive. Matrix populated from real test runs. `make console-ci` passes.

---

## 5. Phase 4 — Remaining Agents & Adversarial Agent (Weeks 4–7) — parallel with Phase 3

### Goal
All four specialist agents are real (not stubs); the autonomous adversarial agent runs continuously.

### Sprint 4.1 — Real Claims Processor (Week 4.5–5.5)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 4.1.1 | `classify_damage(evidence_ref)` deterministic stub function (returns seeded label) | tool with audit + IFC label | 2 |
| 4.1.2 | `lookup_coverage(claim_id)` deterministic | tool | 3 |
| 4.1.3 | `score_fraud(claim_id)` rule-based; returns SECRET-labelled full record | tool with SECRET propagation | 4 |
| 4.1.4 | Confidential RAG retriever for policy docs (capability-gated) | tool | 3 |
| 4.1.5 | Secret RAG retriever for fraud rules (separate credential) | tool | 3 |
| 4.1.6 | Claims processor actor; composes assessment envelope | full actor end-to-end | 6 |
| 4.1.7 | Extend intake parser schema for intent classification (`new_claim` / `faq` / `claim_status` / `policy_question` / `complaint`); orchestrator dispatches on intent | parser emits intent; orchestrator routes correctly | 3 |
| 4.1.8 | Inquiry handlers in claims processor: RLS claim_status lookup; policy_question via RLS policy fetch + CONFIDENTIAL RAG | both inquiry tools wired end-to-end through egress filter | 5 |
| 4.1.9 | Complaint capture tool + `complaints` table writes + ESCALATED transition; FAQ handler in intake actor for pre-identity intent | inquiry flow end-to-end for all five intents | 4 |

### Sprint 4.2 — Real Settlement Actor (Week 5.5–6)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 4.2.1 | `calculate_settlement(claim_id)` deterministic | tool | 3 |
| 4.2.2 | `request_payout(claim_id)` session-bound payee; server-side guards (state=DECIDED, fraud=CLEAR, amount≤cap) | tool with all guards + audit | 5 |
| 4.2.3 | `draft_summary` actor flow; output through egress filter | summary generated, PII-clean | 4 |
| 4.2.4 | End-to-end claim flow with real agents on real seed data | 5 happy-path + 2 escalation paths pass | 6 |

### Sprint 4.3 — Adversarial Agent (Week 6–7)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 4.3.1 | Adversarial agent container (isolated network egress, separate API instance) | sandbox running | 5 |
| 4.3.2 | Strategy module: rotate through attack categories; mutate payloads from feedback | autonomous attack loop | 8 |
| 4.3.3 | Spend cap enforcement: hard $50/month with circuit breaker | cap enforced and surfaced | 3 |
| 4.3.4 | Live feed to Console (SSE); "successful breach" counter; auto-open GitHub issue on breach | feed live; breaches loud | 4 |

**Phase 4 Milestone:** All four real agents work end-to-end. Adversarial agent has run for ≥48 hours continuously. Console live feed shows real adversarial attempts.

---

## 6. Phase 5 — Hardening, Measurement, Formal Spec, Docs (Weeks 7–9)

### Goal
Every attack category in the taxonomy is either live-tested with numbers, architecturally documented with citation, or honestly out-of-scope.

### Sprint 5.1 — Full Live Test Suite (Week 7–8)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 5.1.1 | Build adversarial PDF corpus (≥30 variants) | corpus in `data/attack_payloads/pdfs/` | 4 |
| 5.1.2 | Build adversarial image corpus (≥20 variants) including overlay attacks for P6 | corpus | 4 |
| 5.1.3 | Build direct prompt-injection corpus (≥50 templates × 3 phrasings) | corpus | 4 |
| 5.1.4 | Build cross-customer / RLS probe suite | suite | 3 |
| 5.1.5 | Build URL/PII egress probe suite | suite | 3 |
| 5.1.6 | Build capability-token bypass probe suite | suite | 3 |
| 5.1.7 | CI pipeline runs full red-team suite on every PR; reports to Console matrix | green CI on main; matrix updated | 6 |
| 5.1.8 | Architectural-assertion test suite (e.g. `test_orchestrator_is_not_llm.py`) | suite passes | 4 |

### Sprint 5.2 — Formal Specification (Week 8)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 5.2.1 | TLA+ spec for workflow state machine | `formal/workflow.tla` | 6 |
| 5.2.2 | TLC model-check core invariants | `make formal-check` passes | 4 |
| 5.2.3 | Conformance test: enumerate reachable states in implementation; assert match against spec | conformance test passes | 4 |
| 5.2.4 | Console page rendering spec invariants with last-check timestamp | "Formal" tab in Console | 3 |

### Sprint 5.3 — Documentation & Residual Risk (Week 8.5–9)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 5.3.1 | Defense Pattern Library page with citations, code refs, animated diagrams | live on Console | 6 |
| 5.3.2 | Residual Risk Register on Console + in repo | published | 3 |
| 5.3.3 | All 6 docs updated to v2 final state | docs/ shipped | 4 |
| 5.3.4 | README, CONTRIBUTING, SECURITY.md | repo polished | 3 |
| 5.3.5 | Code reference deep-links (Console → GitHub line numbers) | links work | 3 |

**Phase 5 Milestone:** 79/79 classified; ≥40 LIVE with numbers; formal spec passes; residual risks named publicly.

---

## 7. Phase 6 — Showcase Polish & Launch (Weeks 9–11)

### Goal
The Console is professional, fast, accessible, and convincing. The launch package is ready.

### Sprint 6.1 — Polish (Week 9–10)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 6.1.1 | Command palette (cmd+K) implementation | works site-wide | 5 |
| 6.1.2 | Performance pass: LCP <1.5s, TTFB <200ms; CDN + image optimisation | Lighthouse passes | 5 |
| 6.1.3 | Accessibility pass: WCAG 2.1 AA; keyboard nav; screen-reader pass | axe-clean | 4 |
| 6.1.4 | Defense Pattern Library: animated diagrams per pattern (Framer Motion) | each pattern has a diagram | 6 |
| 6.1.5 | Adversarial agent dashboard: hours-since-breach counter, attempt histogram, cost graph | dashboard live | 5 |
| 6.1.6 | Embed mode (?embed=1) for sharing single playground sessions | works | 3 |

### Sprint 6.2 — Launch (Week 10–11)

| # | Task | Output | Hours |
|---|------|--------|-------|
| 6.2.1 | Final E2E rehearsal of 3 demo scripts (happy path, fraud catch, attack blocked) | clean scripts | 4 |
| 6.2.2 | Record 5-minute demo video walking through the Console | video file | 4 |
| 6.2.3 | Write 1-page "for the recruiter" summary (single PDF) | PDF | 2 |
| 6.2.4 | Public deployment: Console on Vercel, API on Fly/Render, Postgres on Neon | URLs stable | 5 |
| 6.2.5 | GitHub repo final pass: clean commits, signed, README polished | repo ready | 3 |
| 6.2.6 | Soft-launch on personal channels; collect feedback | feedback log | 3 |

**Phase 6 Milestone:** Demo-ready. Console deployed. Video recorded. Repo public. Adversarial agent running. Reviewers can self-serve.

---

## 8. Dependency Chain

```
Phase 1 primitives (RLS, audit chain, capability tokens, IFC, sandboxes, vision pre-redaction, orchestrator skeleton)
        │
        ▼
Phase 2 vertical slice (parser + 4 agents stubbed; identity real)
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
Phase 3 Console + playground         Phase 4 real agents + adversarial
(API contract → frontend)            (real processor, real settlement)
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
Phase 5 full attack matrix, formal spec, docs
                       ▼
Phase 6 polish, accessibility, launch
```

---

## 9. Risk Register

| Risk | Impact | Likelihood | Mitigation | Contingency |
|------|--------|------------|------------|-------------|
| Console becomes the work; agent system thin | High | High | Phase 2 milestone is the gate: agents must work end-to-end before Console starts | Push Console scope to Phase 6 if needed |
| Adversarial agent finds bypass before launch | Medium → High depending on framing | Medium | **Treat as feature.** Publish, fix in public; this is portfolio-positive when handled with audit trail | Soft-launch first to validate fix loop |
| LLM cost overrun | Medium | Medium | Haiku-only adversarial agent; hard caps; cost dashboard on Console | Pause adversarial agent; demonstrate on schedule basis only |
| TLA+ rabbit hole | Medium | Medium | Time-box to 1 week (Sprint 5.2); fall back to documented invariants + property tests | "Formal artifact" downgraded but still present |
| Vision pre-redaction has false negatives | Medium | Medium | Multiple OCR engines (Tesseract + a vision-model OCR pass) + redact unions | Document residual risk; cite as a known limitation |
| Scope creep into insurance realism | High | High | Strict 4-agent cap; cuts in PRD §5.2 are firm | Cut Phase 4 nice-to-haves before extending |
| Reviewer dismisses dual-LLM as "two LLMs to do one thing" | Medium | Low | Console explicitly explains the pattern, with citations and a comparison demo ("with vs without P1") | Add a "naïve baseline" attack demo showing what happens without P1 |

---

## 10. Technology Decision Log

| Decision | Options Considered | Chosen | Rationale |
|----------|--------------------|--------|-----------|
| Agent framework | LangGraph, CrewAI, AutoGen, custom | Custom (Python async) | Frameworks hide control flow; we want every decision auditable. LangGraph's state graph is unnecessary because our state machine is plain code. |
| Orchestrator | LLM-based, code-based | Code-based (P2) | Determinism is a core defense; LLM orchestrator is itself an attack surface. |
| LLM provider | Claude, GPT, local | Claude (Anthropic) | Best tool-use; current latest models Opus 4.7 / Sonnet 4.6 / Haiku 4.5 |
| Per-model selection | One model everywhere vs mixed | Haiku for parsers & adversarial; Sonnet for actors needing reasoning | Cost / latency / capability balance |
| Vector store | ChromaDB, Qdrant, pgvector | ChromaDB | Adequate for ≤25 docs; minimal ops burden |
| Database | Postgres, SQLite, MySQL | Postgres 16 | RLS, JSONB, hash-chain SQL, mature ecosystem |
| Sandbox | Docker, gVisor, Firecracker | Docker `--network=none` + drop-caps + read-only rootfs | Reproducible; sufficient demonstration; can swap to gVisor for production-shaped deploy |
| Inter-agent signing | HMAC shared secret, Ed25519 asymmetric | Ed25519 | Compromise of one agent doesn't reveal others |
| Secret hashing | SHA-256, HMAC, Argon2id | Argon2id + per-deployment pepper | SSN keyspace (10⁹) defeats bare SHA-256 |
| Console framework | Next.js, Remix, plain React | Next.js 15 App Router | SSR for SEO; RSC for performance; Vercel deploy |
| Console UI library | shadcn/ui, MUI, Mantine, custom | shadcn/ui | Professional baseline; full customisation; matches dark monospace aesthetic |
| Diagrams | React Flow, Mermaid, D3 | React Flow for interactive; Mermaid for docs | Interactive needed for explorer |
| Observability | OTel, custom logs | OpenTelemetry → Tempo + Grafana | Industry-standard; demonstrable; traces feed Console |
| Formal method | TLA+, Alloy, Lean | TLA+ (TLC model-checker) | Best documented for workflow specs; PlusCal is approachable |

---

## 11. Definition of Done

A sprint is done when:

1. Code merged to `main` via reviewed PR (self-review acceptable solo)
2. Unit tests pass (>80% coverage on touched code)
3. Integration tests pass where applicable
4. Red-team tests pass for the relevant attack rows (with numbers updated)
5. Console renders the new state (if applicable)
6. Audit chain verifies clean
7. OTel traces visible in Tempo
8. Docs updated (where applicable)

---

## 12. Effort Estimate

| Phase | Hours | Weeks |
|-------|-------|-------|
| 1. Security primitives | 68 | 2.5 |
| 2. Vertical slice | 45 | 1.5 |
| 3. Console + playground | 70 | 2 (parallel with 4) |
| 4. Real agents + adversarial | 62 | 3 (parallel with 3) |
| 5. Full matrix + formal spec + docs | 65 | 2 |
| 6. Polish + launch | 49 | 2 |
| **Total (serialised)** | **359** | **11 weeks at ~30h/wk** |
| **Total (with Phase 3 ‖ Phase 4)** | **359** | **9 weeks at ~40h/wk** |

The estimate is roughly 1.6× the previous version's 216h. The increase reflects realistic security-engineering effort, dedicated Console build, formal-spec work, and adversarial-agent build — partially offset by cuts to ML training, synthetic data generation, intent classification, and the 7-agent overscope.

---

*End of Implementation Roadmap — Document 5 of 6*
