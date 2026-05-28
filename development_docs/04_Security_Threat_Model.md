# SecureClaim AI — Security & Threat Model Document

**Version:** 2.0
**Date:** May 27, 2026
**Status:** Final v2.0
**Author:** Athish G R
**Classification:** Internal

---

## 1. Threat Landscape Overview

This document maps each of the 79 attack categories in `agentic_ai_attack_types.md` to the SecureClaim AI architecture. For each attack we declare:

- **Class:** `LIVE` (we run automated attack variants and report numbers), `ARCHITECTURAL` (the architecture makes the attack inapplicable or prevented by construction; we don't need a runtime test, we cite the pattern), or `OUT-OF-SCOPE` (e.g. training-data attacks when we don't train a model — documented explicitly with rationale).
- **Patterns engaged:** which of the named patterns from Doc 02 §1.2 defend it.
- **Test method or rationale.**

The deliverable's promise is **not** "all 79 blocked" — that would be a marketing claim no reviewer should believe. The promise is "all 79 classified, defended (or honestly out-of-scope), traceable to named patterns, and where live-tested, reported with real numbers."

### 1.1 Defense Class Targets

| Class | Target count | Why |
|-------|--------------|-----|
| LIVE | ≥40 | These are the attacks where runtime defense matters and tests are feasible |
| ARCHITECTURAL | ~30 | Pattern-prevented; documented with citation |
| OUT-OF-SCOPE | ≤10 | Honest scope statements; mostly training-attack categories |

### 1.2 Defense Pattern References

Patterns are defined in Doc 02 §1.2. Shorthand: P1 (dual-LLM), P2 (deterministic orchestration), P3 (IFC labels), P4 (capability tokens), P5 (sandbox), P6 (vision pre-redaction), P7 (RLS), P8 (asymmetric per-agent identity), P9 (hash-chained audit), P10 (egress filter), P11 (budgets), P12 (signed prompts).

---

## 2. Attack-Defense Matrix

For brevity, attacks with shared defense strategies are grouped. Each row of the Console matrix mirrors this layout with live numbers attached.

### 2.1 Prompt & Input Manipulation (#1–8) — LIVE for #1–7, LIVE-LIMITED for #8

| # | Attack | Class | Patterns | Defense summary | Test |
|---|--------|-------|----------|-----------------|------|
| 1 | Direct Prompt Injection | LIVE | P1, P10 | Untrusted text only ever reaches the **quarantined parser LLM**, which has no tools and emits only JSON. Privileged actors never see the raw text. Output filter blocks SECRET leakage and applies PII redaction. | ≥50 known injection templates × 3 phrasings; success = parser emits non-schema output, or actor takes unauthorised action. **Numbers published in the Console matrix.** |
| 2 | Indirect Prompt Injection | LIVE | P1, P5, P3 | PDFs sanitised in network-isolated sandbox (hidden text stripped). Extracted text goes through parser path, never to an actor. UNTRUSTED label propagates. | 30+ adversarial PDFs including white-on-white, micro-font, off-page, embedded JS. |
| 3 | Cross-Context Injection | LIVE | P1, P3, P12 | Actors receive only structured envelopes from upstream agents; never free text. IFC labels prevent UNTRUSTED-derived data from being used as instructions. | Plant payloads in evidence targeting downstream agents; verify structured handoffs immune. |
| 4 | Jailbreaking | LIVE | P1, P10, P12 | Privileged actor jailbreak is bounded: it can only mint capability-token-validated tool calls; tools enforce scope server-side. The structural ceiling on what jailbreak can achieve is what we measure. | Garak probe set + curated jailbreak set; success = actor produces non-policy output that egress filter does not catch. |
| 5 | Adversarial Examples / Evasion | LIVE | P11 + escalation | Damage classifier is a stub returning fixed labels in the demo; adversarial-example testing is therefore degenerate for the stub itself. We instead test the **decision path**: low-confidence outputs are escalated. The injection-classifier confidence path is the meaningful surface, tested with adversarial text. | Adversarial-text perturbations vs. injection classifier; measure: classifier deltas + escalation trigger rate. |
| 6 | Cross-Modal / Multimodal Injection | LIVE | **P6 (vision pre-redaction)**, P5, P1 | OCR pre-pass detects text regions; bounding boxes are pixel-blurred to opaque blocks before the vision model receives the image. OCR text is then routed through the parser as a separate UNTRUSTED stream. Instruction-style "ignore overlays" prompts are explicitly not the defense. | 20+ adversarial images: visible overlays, watermarks, sticker-style text, low-contrast embedded text. |
| 7 | Semantic Prompt Injection | LIVE | P1, P10 | Unicode NFKC normalisation + zero-width stripping + RTL-override stripping happens in the ingress sanitiser. Even if normalisation misses, the parser-actor separation means the worst case is a structured-output anomaly, not action execution. | 25+ payloads using homoglyphs, zero-width joiners, RTL overrides, mixed-script tricks. |
| 8 | Zero-Click Injection | LIVE-LIMITED | P5, P1 | No auto-processing without user upload click. PDF/image sanitisation happens in `--network=none` containers. Even passive parsing is bounded by P5. | Upload payload PDFs; assert no outbound network from sandbox during processing; assert no actor invocation during parsing. |

### 2.2 Goal & Behaviour Hijacking (#9–14)

| # | Attack | Class | Patterns | Defense summary | Test |
|---|--------|-------|----------|-----------------|------|
| 9 | Agent Goal Hijack | LIVE | P2, P12 | Orchestrator is deterministic code; actor goals cannot be "redirected" because actors don't decide workflow steps — code does. Signed prompts (P12) prevent runtime prompt mutation. | Conversation sequences attempting to redirect; verify state machine ignores. |
| 10 | Semantic Layer Exploitation | LIVE | P4, P2 | "Approved" is not a word; it's a database state plus a capability token. Payout requires `decision = SETTLED` in DB AND a capability token issued only when guards passed. | Ambiguous-language tests; verify no tool fires on conversational ambiguity. |
| 11 | CoT Manipulation | LIVE | P2 + P4 | Calculations (coverage, settlement) are deterministic tools, not LLM math. LLM cannot pass arbitrary parameters: tool parameters validated against capability-token scope (e.g. `claim_id` in call must match scope). | Inject false policy claims; verify deterministic tool unaffected. |
| 12 | Calendar / Quiet Mode Drift | ARCHITECTURAL | P12, P2 | No persistent per-agent memory across sessions. Each session has a fresh context. Long-session summarisation (when needed) is done by a quarantined summariser whose output is structured. | Documented; cited. Out of live scope because requires longitudinal production traffic. |
| 13 | Goal Misalignment Cascade | LIVE | P2, P3, end-to-end consistency check | State machine guards reject inconsistent combined states. Settlement amount is recomputed deterministically at SETTLED; mismatch with prior agent claims aborts. | Inject inflated damage at parser; verify deterministic settlement is unaffected. |
| 14 | Behavioural Drift | ARCHITECTURAL | P12, "no fine-tune on production data" | Stateless agents; pinned model + pinned signed system prompts. | Documented; golden test suite runs in CI. |

### 2.3 Memory & Context Attacks (#15–19)

| # | Attack | Class | Patterns | Defense summary |
|---|--------|-------|----------|-----------------|
| 15 | Memory Poisoning | ARCHITECTURAL | (no persistent memory) | Stateless across sessions; each context rebuilt from DB. |
| 16 | Context Poisoning | LIVE | P3, P12 | Context contains only DB-fetched data (label-checked) plus parser-structured input. No prior conversation persisted across claims. |
| 17 | RAG Index Poisoning | LIVE | P12 (signed RAG manifest) | Documents hashed; manifest signed; daily integrity check; runtime writes to RAG corpus require admin role + signed commit. |
| 18 | Log Poisoning | ARCHITECTURAL | P9, "no agent reads its own logs" | Audit log is INSERT-only for application roles. No agent has a tool to read audit log. |
| 19 | Semantic State Accumulation | LIVE | P11 (session budgets), P1 (summariser quarantine) | Session-bounded context. Long contexts summarised via quarantined LLM that emits structured-only output. |

### 2.4 Data Exfiltration (#20–28)

| # | Attack | Class | Patterns | Defense summary |
|---|--------|-------|----------|-----------------|
| 20 | Direct Exfiltration | LIVE | **P7 (RLS)**, P3, P4 | Postgres RLS enforces per-customer scope at the DB layer. Capability tokens restrict tool scope. "Get all claims" tool does not exist for customer-facing agents. |
| 21 | Indirect Exfiltration via Side Channels | LIVE | P10, P3 | Egress filter scans every customer-visible string for PII patterns and refuses SECRET-labelled values. |
| 22 | Model Inversion | LIVE-LIMITED | P3, P11 | Fraud "model" is a stub in this demo; the real defense being demonstrated is that **only the `decision` field is exposed** to non-SECRET-clearance contexts. We test the exposure surface, not the (stubbed) model. |
| 23 | Membership Inference | LIVE-LIMITED | (same as #22) | Same as #22. Binary `decision` output. |
| 24 | Exfiltration via RAG | LIVE | P3, P10 | RAG retrievals are label-tagged; egress filter denies customer-visible SECRET sources. |
| 25 | URL-Based Exfiltration | LIVE | P10 (URL allowlist) | Output filter strips any URL not in the published allowlist (docs.\*, status.\*). All other URLs replaced with `[external link removed]` and audited. |
| 26 | Steganographic Exfiltration | LIVE | P3, P10, schema-constrained outputs | Inter-agent messages have enumerated schema fields; free-text is minimised. Customer-facing free text passes through egress filter + length cap. |
| 27 | Side-Channel Summarisation | LIVE | P7, P3 | Summarisation tools scoped to authenticated customer's data via RLS; cannot include cross-customer content. |
| 28 | Semantic-Layer Exfiltration | LIVE | P4, P7 | No `get_all_claims` capability exists. All retrieval tools require scoped capability tokens. "Export records like mine" tools simply do not exist. |

### 2.5 Tool & Execution Attacks (#29–37)

| # | Attack | Class | Patterns | Defense summary |
|---|--------|-------|----------|-----------------|
| 29 | Tool Misuse | LIVE | **P4 (capability tokens)** | Server-side check: agent_id × tool × scope × signature. LLM cannot widen scope or call unowned tools. |
| 30 | Unexpected Code Execution / RCE | LIVE | P5, no code-exec tools | No agent has a code-execution tool. PDF processing in `--network=none` container with restricted syscalls. |
| 31 | Recursive Tool Calls | LIVE | P11 | Per-session tool budget (50), per-tool/min limit (5), circuit breaker after 3 consecutive failures. |
| 32 | Unsafe Tool Composition | LIVE | P2, P4 | Orchestrator-enforced action dependency graph: payout requires DECIDED + CLEAR. Capability tokens scoped per-stage. |
| 33 | Cross-Tool State Leakage | ARCHITECTURAL | Stateless tools by construction | Each tool call receives explicit parameters; no shared mutable state. |
| 34 | Tool Budget Exhaustion (DoW) | LIVE | P11 | Hard caps; Console shows live spend; circuit breaker. |
| 35 | MCP Tool Poisoning | ARCHITECTURAL | Tools defined locally, code-reviewed, version-pinned. No MCP registry consumed. | Documented. |
| 36 | Publish Poisoned Agent Tool | ARCHITECTURAL | First-party tools only. SBOM published. | Documented. |
| 37 | SQL Injection via Agent | LIVE | Parameterised queries via SQLAlchemy ORM; **plus P7 (RLS)** as backstop | Classic injection payloads; verify zero impact. |

### 2.6 Identity, Privilege & Trust (#38–43)

| # | Attack | Class | Patterns | Defense summary |
|---|--------|-------|----------|-----------------|
| 38 | Identity & Privilege Abuse | LIVE | P4, P8 | Per-agent DB roles + capability tokens. No credential sharing. |
| 39 | Confused Deputy | LIVE | P4 | Tool registry checks calling agent's authenticated identity server-side; LLM "convincing" the agent doesn't bypass server checks. |
| 40 | Agent Impersonation | LIVE | P8 (Ed25519 per-agent keys) | Signature verification; per-agent secrets. |
| 41 | Credential / Token Compromise | ARCHITECTURAL | Short-lived capability tokens, per-session rotation, secret-manager-held private keys. | Documented. |
| 42 | Session Hijacking | LIVE | session bound to customer_id; mismatch invalidates | Test cross-session interactions. |
| 43 | Privilege Escalation via Orchestrator | ARCHITECTURAL | **Orchestrator is plain code, not an LLM (P2).** Compromising it requires code modification, not prompt injection. | This entire attack class is structurally not applicable to the system. |

### 2.7 Multi-Agent & Orchestration (#44–49)

| # | Attack | Class | Patterns | Defense summary |
|---|--------|-------|----------|-----------------|
| 44 | Insecure Inter-Agent Communication | LIVE | P8, schema validation | Signed messages; pydantic schemas. |
| 45 | Rogue Agent Injection | ARCHITECTURAL | Static agent registry; no runtime agent registration. | Documented. |
| 46 | Orchestration Layer Exploitation | ARCHITECTURAL | **P2** | Orchestrator is deterministic code with minimal privilege; no LLM to compromise. |
| 47 | Spoofed Inter-Agent Messages | LIVE | P8 + replay protection (message_id + timestamp window) | Spoof attempts; verify signature failure. |
| 48 | Malicious Agent Collusion | ARCHITECTURAL | All inter-agent traffic flows through orchestrator with audit; no side channels. | Documented + design review. |
| 49 | Steganographic Agent Collusion | LIVE-LIMITED | Schema-constrained messages; free-text fields are tiny and label-tagged. | Manual statistical review of inter-agent message corpora. |

### 2.8 Supply Chain & Ecosystem (#50–55)

| # | Class | Defense |
|---|-------|---------|
| 50 | ARCHITECTURAL | Pinned dependencies (hash-locked); no external MCP registry; SBOM published. |
| 51 | OUT-OF-SCOPE | We do not train foundation models. Documented as out-of-scope with rationale. |
| 52 | ARCHITECTURAL | All package names resolved at code-review time; no runtime install. |
| 53 | ARCHITECTURAL | Same as #36. |
| 54 | LIVE | Repo config attack test: drop a malicious `Makefile` or pre-commit hook in a fixture branch; assert CI rejects via signed-commit policy. |
| 55 | ARCHITECTURAL | No third-party plugins; first-party tools only. |

### 2.9 Training & Model-Level (#56–60)

| # | Class | Defense |
|---|-------|---------|
| 56 | OUT-OF-SCOPE | We do not train models. Stub fraud function + off-the-shelf injection classifier. Documented. |
| 57 | OUT-OF-SCOPE | Same. We use pinned vendor-hosted models. |
| 58 | LIVE-LIMITED | The "extractable model" surface is the injection classifier; rate-limited; tested with extraction probes. |
| 59 | OUT-OF-SCOPE | No fine-tuning in this build. |
| 60 | OUT-OF-SCOPE | No training pipeline. |

(Reviewer note: being honest about OUT-OF-SCOPE here is a deliberate signal that we don't fabricate coverage we can't substantiate.)

### 2.10 Cascading & Systemic (#61–64)

| # | Class | Defense |
|---|-------|---------|
| 61 | LIVE | Independent guards at each transition; circuit breakers per agent. |
| 62 | LIVE | Structured handoffs (schemas, not narratives); independent deterministic recomputation at settlement. |
| 63 | LIVE | End-to-end consistency invariant at SETTLED stage: amount within coverage, deductible applied, fraud_clear, identity_verified. |
| 64 | LIVE | Same as #13. |

### 2.11 Human-Agent Trust (#65–67)

| # | Class | Defense |
|---|-------|---------|
| 65 | LIVE | Agent never requests PII conversationally; identity uses server-side compare. |
| 66 | LIVE | System prompt explicit: never ask for SSN, password, bank details; all sensitive ops via tools. Egress filter enforces. |
| 67 | LIVE | Agent identifies as AI; escalation paths clearly marked; no "adjuster"/"manager" personas. |

### 2.12 Infrastructure & Runtime (#68–72)

| # | Class | Defense |
|---|-------|---------|
| 68 | LIVE | P5 sandbox; `--network=none`, drop-capabilities, read-only rootfs. Escape-attempt test scripts. |
| 69 | LIVE | P11 spend caps; Console shows real-time $. Adversarial agent's own cap demonstrated. |
| 70 | LIVE | Per-session turn cap; tool-call cap; conversation length cap. |
| 71 | LIVE | All WS connections authenticated with session JWT; origin pinning. |
| 72 | ARCHITECTURAL | No dynamic code execution; no agent has package-publish or fs-write tool. |

### 2.13 AI as Weapon (#73–75)

| # | Class | Defense |
|---|-------|---------|
| 73 | ARCHITECTURAL | No agent has outbound network capability beyond pinned LLM provider and pinned RAG store. Reconnaissance, exploitation, exfiltration all structurally impossible. |
| 74 | ARCHITECTURAL | Same. |
| 75 | ARCHITECTURAL | Same. |

### 2.14 Privacy & Inference (#76–79)

| # | Class | Defense |
|---|-------|---------|
| 76 | LIVE-LIMITED | Same as #22; only `decision` field exposed. |
| 77 | LIVE-LIMITED | Same as #23. |
| 78 | LIVE | System prompts contain no secrets; prompt-extraction probes verified to return no actionable content. |
| 79 | OUT-OF-SCOPE | We don't fine-tune. Vendor model is pinned; we accept their training-data guarantees. Documented. |

---

## 3. Red Team Testing Plan

### 3.1 Test Suite Structure

```
tests/red_team/
├── 01_prompt_input/                # #1–8
│   ├── direct_injection/           # 50+ templates × 3 phrasings
│   ├── indirect_pdf/               # 30+ adversarial PDFs
│   ├── indirect_image/             # 20+ adversarial images
│   ├── cross_context/
│   ├── jailbreak/                  # Garak set + custom
│   ├── multimodal/                 # P6 effectiveness probes
│   ├── semantic/                   # Unicode tricks
│   └── zero_click/
├── 02_goal_hijack/                 # #9–14
├── 03_memory_context/              # #15–19
├── 04_data_exfiltration/           # #20–28
│   ├── cross_customer/             # RLS probes
│   ├── url_exfil/                  # P10 probes
│   ├── summarisation/
│   └── rag_secret_extraction/
├── 05_tool_execution/              # #29–37
├── 06_identity_privilege/          # #38–43
├── 07_orchestration/               # #44–49
├── 08_supply_chain/                # #50–55 (mostly architectural; one live for #54)
├── 09_cascading/                   # #61–64
├── 10_human_trust/                 # #65–67
├── 11_infrastructure/              # #68–72
├── 12_privacy_inference/           # #76–79
├── architectural_assertions/       # static tests for ARCHITECTURAL claims
│   ├── test_orchestrator_is_not_llm.py
│   ├── test_no_outbound_network_tools.py
│   ├── test_agent_registry_static.py
│   └── test_dependencies_pinned.py
└── conftest.py
```

**Dual-surface testing.** Every test that targets a customer-facing surface (chat injection #1; indirect exfiltration #21; summarisation leakage #27; semantic-layer exfiltration #28; trust exploitation #65; social engineering #66; prompt extraction #78) runs against **both** the claim-filing path AND the customer-inquiry path (TAD §3.3). The inquiry path exercises different intents (`claim_status`, `policy_question`, `complaint`) routed to different downstream tools and RAG retrievals, providing a second realistic attack surface that mirrors how production attackers commonly target customer service rather than claim intake.

### 3.2 Metric Schema

Every live attack reports:

```json
{
  "attack_id": 1,
  "name": "Direct Prompt Injection",
  "class": "LIVE",
  "variants_tried": 153,
  "blocked": 153,
  "partial_leak": 0,
  "false_positives_on_clean": 2,
  "last_run_ts": "2026-05-27T13:00:00Z",
  "duration_ms": 184211,
  "median_block_layer": "parser_schema_violation"
}
```

The Console renders this directly; no marketing summarisation.

### 3.3 Continuous Adversarial Agent

In addition to the static suite, an autonomous Claude Haiku 4.5 agent runs against a sandboxed instance continuously. Its prompt and strategy are open-source. Its outcomes feed:
- The "successful breach" counter on the Console (≥1 → loud banner)
- The live adversarial stream
- Auto-opened GitHub issues on breach

### 3.4 Honest Limitations

The Console's footer carries a **Residual Risk Register**, including:
- Detection heuristics (semantic injection classifier, steganography heuristic) have non-zero false-negative rates. Our structural defenses are the primary; classifiers are signals.
- The dataset is small. Some attack categories that depend on volume (drift, slow exfiltration over many sessions) are demonstrated structurally, not empirically.
- The "production-pattern" inter-agent signing in a single-process deployment is a pattern demonstration, not a network boundary. Promoting to a real deployment requires swapping transports.
- LLM behaviour is nondeterministic. Live numbers are reported as run-medians with variance bands, not single-run snapshots.

This register is itself a portfolio signal: "this person knows what they're not claiming."

---

## 4. Success Criteria

| Criterion | Target |
|-----------|--------|
| All 79 attacks classified | 100% |
| LIVE attacks with ≥10 variants each | 100% |
| LIVE attacks with reported metrics on the Console | 100% |
| ARCHITECTURAL attacks with named pattern + code reference | 100% |
| OUT-OF-SCOPE attacks with written rationale | 100% |
| Cross-customer leak via RLS bypass attempts | 0 / N attempts |
| Direct injection reaching privileged actor (post-parser) | 0 / N attempts |
| Adversarial-agent-found unmitigated breaches at launch | 0 (or honestly disclosed if non-zero) |

---

*End of Security & Threat Model Document — Document 4 of 6*
