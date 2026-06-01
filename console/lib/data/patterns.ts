import type { Pattern, PatternId } from "@/lib/types/showcase";

export const PATTERNS: Pattern[] = [
  {
    id: "P1",
    name: "Dual-LLM Separation",
    summary: "A quarantined parser LLM converts untrusted input into a strict JSON schema; privileged actors operate only on the schema and never see raw user content.",
    description: `**P1 — Dual-LLM Separation** isolates untrusted content from privileged decision-making agents.

An unprivileged, tool-less *parser LLM* (Claude Haiku 4.5) receives raw user input wrapped in \`<untrusted>\` delimiters. Its only job is to emit a strict JSON schema; it has no tool access and sees no business data. Downstream *actor LLMs* receive only the validated schema — raw text never crosses the trust boundary.

This structural separation means even a perfectly jailbroken parser LLM is bounded in its blast radius: it cannot exfiltrate data it never saw, and it cannot invoke tools it was never given.`,
    attackIds: [1, 2, 3, 6, 7, 8],
    implemented: true,
    codeRefs: [
      { label: "run_intake_parser()", path: "backend/agent_system/parser/intake_parser.py", lineStart: 100, lineEnd: 134 },
      { label: "IntakeOutput schema", path: "backend/agent_system/parser/schemas/intake.py", lineStart: 1, lineEnd: null },
    ],
    testCount: 18,
  },
  {
    id: "P2",
    name: "Deterministic Orchestration",
    summary: "Workflow transitions are computed by plain code from database state; the LLM may suggest, but code decides.",
    description: `**P2 — Deterministic Orchestration** removes the LLM from all control-flow decisions.

A plain-code state machine (not an LLM) holds claim state, validates transitions against pre-condition gates, and dispatches task envelopes to agents. The LLM never routes, never authorises, and never transitions state directly.

Attack #46 (Orchestration Layer Exploitation) is architecturally not applicable: there is no LLM in the orchestrator to compromise. A perfectly manipulated actor agent that proposes an invalid transition simply gets rejected — the orchestrator writes a \`transition_violation\` audit row and halts the session.`,
    attackIds: [9, 11, 13, 43, 46, 61, 62, 63, 64],
    implemented: true,
    codeRefs: [
      { label: "Orchestrator.advance_stage()", path: "backend/agent_system/orchestrator/state.py", lineStart: 64, lineEnd: null },
      { label: "TRANSITIONS table", path: "backend/agent_system/orchestrator/transitions.py", lineStart: 1, lineEnd: null },
    ],
    testCount: 102,
  },
  {
    id: "P3",
    name: "Information Flow Control (IFC) Labels",
    summary: "Every datum carries a trust label propagated through transformations and enforced at action sites.",
    description: `**P3 — Information Flow Control** tracks data sensitivity through the entire pipeline.

Every datum carries one of five labels: \`PUBLIC < PERSONAL < CONFIDENTIAL < SECRET\`, plus the orthogonal \`UNTRUSTED\` taint applied to all user-supplied content. Labels are propagated through transformations (a merge of CONFIDENTIAL + SECRET yields SECRET). Tool calls check the label before execution; the egress filter refuses to surface SECRET-labelled values to customers.

This means an agent cannot be coerced into exfiltrating data it is allowed to hold, because the label enforcement happens server-side — not in the agent's context.`,
    attackIds: [20, 21, 24, 26, 27, 28],
    implemented: true,
    codeRefs: [
      { label: "DataLabel enum", path: "backend/agent_system/ifc/labels.py", lineStart: 31, lineEnd: 75 },
      { label: "Label & Labeled classes", path: "backend/agent_system/ifc/labels.py", lineStart: 79, lineEnd: null },
      { label: "join() / taint() propagation", path: "backend/agent_system/ifc/propagation.py", lineStart: 1, lineEnd: null },
    ],
    testCount: 24,
  },
  {
    id: "P4",
    name: "Capability-Scoped Tools",
    summary: "Tools require capability tokens signed for a specific agent, action, and parameter scope; the LLM cannot mint tokens.",
    description: `**P4 — Capability-Scoped Tools** makes the LLM's tool authority a runtime enforcement property, not a prompt property.

Each tool call must carry a capability token minted by the orchestrator and signed with the orchestrator's Ed25519 private key. The token binds: \`agent_id × tool × scope × expiry\`. The registry verifies all five constraints before execution.

The LLM cannot widen scope, cannot mint tokens, and cannot invoke tools outside its issued capability. A perfectly jailbroken Claims Processor agent that attempts \`request_payout\` will be rejected — the orchestrator never issued that capability token.`,
    attackIds: [29, 32, 33, 38, 39],
    implemented: true,
    codeRefs: [
      { label: "CapabilityToken model", path: "backend/agent_system/tools/capability_tokens.py", lineStart: 54, lineEnd: 73 },
      { label: "issue_token()", path: "backend/agent_system/tools/capability_tokens.py", lineStart: 129, lineEnd: 165 },
      { label: "verify_token()", path: "backend/agent_system/tools/capability_tokens.py", lineStart: 195, lineEnd: 244 },
    ],
    testCount: 20,
  },
  {
    id: "P5",
    name: "Sandboxed File Processing",
    summary: "All file parsing runs in network-isolated containers with restricted syscalls and ephemeral filesystems.",
    description: `**P5 — Sandboxed File Processing** contains the blast radius of malicious file content.

PDFs and other documents are parsed in ephemeral containers with no network egress, a restricted syscall set (seccomp profile), and a read-only filesystem except for a single tmpfs scratch volume. PDFs with JavaScript, embedded executables, or active forms are rejected before parsing begins.

Extracted text is labelled UNTRUSTED and routed to the parser LLM (P1). Even a full container escape yields an ephemeral host with no persistent credentials or network reachability.`,
    attackIds: [2, 6, 8, 30, 35, 68],
    implemented: true,
    codeRefs: [
      { label: "_scan_threats()", path: "backend/sandbox/pdf/parse.py", lineStart: 49, lineEnd: 128 },
      { label: "image sandbox entrypoint", path: "backend/sandbox/image/parse.py", lineStart: 108, lineEnd: null },
    ],
    testCount: 12,
  },
  {
    id: "P6",
    name: "Vision Pre-Redaction",
    summary: "Images are OCR-pre-processed; detected text regions are pixel-redacted before the image reaches the vision model.",
    description: `**P6 — Vision Pre-Redaction** eliminates the multimodal injection surface for images.

Before any image reaches a vision model, an OCR pass identifies text regions. Those bounding boxes are pixel-blurred to opaque blocks; the vision model receives only the redacted image. The OCR text is extracted as a separate UNTRUSTED stream and routed through the standard text sanitisation pipeline (P1).

This breaks the attack chain for hidden-text injections in images: the injected text becomes a plaintext UNTRUSTED signal rather than an invisible instruction to the vision model.`,
    attackIds: [6],
    implemented: true,
    codeRefs: [
      { label: "redact_image()", path: "backend/agent_system/sanitisation/redaction.py", lineStart: 164, lineEnd: null },
      { label: "TextRegion / RedactBox", path: "backend/agent_system/sanitisation/redaction.py", lineStart: 46, lineEnd: 86 },
    ],
    testCount: 8,
  },
  {
    id: "P7",
    name: "DB-Enforced Tenancy (RLS)",
    summary: "PostgreSQL row-level security policies enforce per-customer scope at the database layer, independent of application code.",
    description: `**P7 — DB-Enforced Tenancy** moves tenancy enforcement from application code into the database itself.

PostgreSQL row-level security (RLS) policies are attached directly to tables. Each agent role can only see rows matching its session-bound customer scope. No application-layer SQL can override this — RLS is enforced below the query planner.

An agent coerced into running \`SELECT * FROM claims\` via SQL injection (attack #37) cannot return another customer's rows: the database silently filters them. This is the fail-closed baseline even when application-layer defenses fail.`,
    attackIds: [20, 28, 37],
    implemented: true,
    codeRefs: [
      { label: "RLS policies (SQL)", path: "backend/db/migrations/001_initial_schema.sql", lineStart: 24, lineEnd: 31 },
    ],
    testCount: 14,
  },
  {
    id: "P8",
    name: "Per-Agent Asymmetric Identity",
    summary: "Each agent has its own Ed25519 keypair; messages are signed; verification uses public keys; compromise of one agent does not reveal others.",
    description: `**P8 — Per-Agent Asymmetric Identity** makes inter-agent trust cryptographically verifiable.

Every agent process holds a unique Ed25519 private key. Every message crossing an agent boundary is signed with the sender's key. Recipient agents verify the envelope before processing any payload; unknown signers are rejected and audited.

Key isolation means compromising one agent does not yield the keys of others. Spoofed inter-agent messages (attack #47) fail signature verification. Agent impersonation (attack #40) requires forging a key that was never stored in the compromised process.`,
    attackIds: [40, 44, 47],
    implemented: true,
    codeRefs: [
      { label: "sign_message() / verify_message()", path: "backend/agent_system/identity/signing.py", lineStart: 20, lineEnd: 47 },
      { label: "KeypairManager", path: "backend/agent_system/identity/keys.py", lineStart: 1, lineEnd: null },
    ],
    testCount: 10,
  },
  {
    id: "P9",
    name: "Append-Only Hash-Chained Audit",
    summary: "Every action writes one immutable row; each row's hash includes the previous row's hash; tampering breaks the chain.",
    description: `**P9 — Append-Only Hash-Chained Audit** provides tamper-evident forensic coverage for all 79 attack categories.

Every agent action, tool call, security event, and state transition writes exactly one audit row. Each row includes \`SHA-256(payload || prev_hash)\`. A background verifier continuously walks the chain; any gap or hash mismatch triggers an alert.

Log poisoning (attack #18) is directly mitigated: malicious content written to a log cannot retroactively alter prior rows without breaking the hash chain. The audit log is the forensic primitive that makes all other defenses visible and attributable.`,
    attackIds: [18],
    implemented: true,
    codeRefs: [
      { label: "compute_row_hash()", path: "backend/audit/chain.py", lineStart: 35, lineEnd: 37 },
      { label: "append_log()", path: "backend/audit/chain.py", lineStart: 40, lineEnd: 113 },
      { label: "verify_chain()", path: "backend/audit/chain.py", lineStart: 113, lineEnd: null },
    ],
    testCount: 16,
  },
  {
    id: "P10",
    name: "Egress Output Filter",
    summary: "All customer-visible output passes through a filter that strips PII patterns, denies non-allowlisted URLs, and refuses to surface SECRET-labelled values.",
    description: `**P10 — Egress Output Filter** is the last-line defense before data reaches the customer.

Every string destined for customer-visible output passes through a filter pipeline: PII regex patterns (SSN, credit-card, email, phone), URL allowlist enforcement (any non-allowlisted URL is replaced with \`[URL REDACTED]\`), and a label check that refuses to surface any SECRET-labelled value regardless of instruction.

This breaks URL-based exfiltration (attack #25), social engineering via agent (attack #66), and prompt extraction (attack #78) — even when upstream agents have been compromised.`,
    attackIds: [21, 25, 26, 66, 78],
    implemented: true,
    codeRefs: [
      { label: "filter_output()", path: "backend/agent_system/egress/filter.py", lineStart: 43, lineEnd: null },
      { label: "PII patterns", path: "backend/agent_system/egress/patterns.py", lineStart: 1, lineEnd: null },
      { label: "URL allowlist", path: "backend/agent_system/egress/allowlist.py", lineStart: 1, lineEnd: null },
    ],
    testCount: 22,
  },
  {
    id: "P11",
    name: "Token & Cost Budgets",
    summary: "Per-session token budget, per-agent tool budget, monthly spend caps, and circuit breakers prevent resource exhaustion.",
    description: `**P11 — Token & Cost Budgets** provides hard resource limits enforced at the orchestrator level.

The deterministic orchestrator tracks: per-session token consumption (hard cap), per-agent tool-call count (hard cap per session), and global monthly spend (circuit breaker that freezes all new sessions). Exceedance halts the session immediately and emits a \`budget_exceeded\` security event.

This constrains Denial of Wallet (attack #69), recursive tool call loops (attack #31), and tool budget exhaustion (attack #34). Because enforcement is in the deterministic orchestrator — not in any LLM — it cannot be reasoned away.`,
    attackIds: [31, 34, 69, 70],
    implemented: true,
    codeRefs: [
      { label: "SessionBudget", path: "backend/agent_system/orchestrator/budgets.py", lineStart: 30, lineEnd: 54 },
      { label: "consume_tokens()", path: "backend/agent_system/orchestrator/budgets.py", lineStart: 56, lineEnd: 80 },
      { label: "consume_tool_call()", path: "backend/agent_system/orchestrator/budgets.py", lineStart: 82, lineEnd: null },
    ],
    testCount: 8,
  },
  {
    id: "P12",
    name: "Signed System Prompts",
    summary: "A prompt registry stores signed manifests; runtime verifies prompt hash before injection; changes require a reviewed PR.",
    description: `**P12 — Signed System Prompts** prevents runtime system-prompt substitution.

Every system prompt is registered with a content hash and signed manifest. At runtime, the orchestrator fetches the expected hash for each agent role and verifies the actual prompt before it is injected. A mismatch halts the session and emits a \`prompt_integrity_violation\` audit row.

This means behavioral drift (attack #14), model backdoor activation (attack #57), and agent goal hijack via prompt substitution (attack #9) all require a signed manifest change — which requires a reviewed PR and produces a verifiable audit trail.`,
    attackIds: [9, 14, 57],
    implemented: true,
    codeRefs: [
      { label: "PromptManifest", path: "backend/agent_system/orchestrator/prompts.py", lineStart: 50, lineEnd: 65 },
      { label: "verify_manifest()", path: "backend/agent_system/orchestrator/prompts.py", lineStart: 97, lineEnd: 114 },
      { label: "load_and_verify()", path: "backend/agent_system/orchestrator/prompts.py", lineStart: 115, lineEnd: 175 },
    ],
    testCount: 12,
  },
];

export function getPattern(id: PatternId): Pattern | undefined {
  return PATTERNS.find((p) => p.id === id);
}
