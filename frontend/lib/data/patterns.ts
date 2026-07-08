export interface Pattern {
  id: string;
  name: string;
  problem: string;
  shape: string;
  citation: string;
  codeRef: string;
  testRef: string;
  residual: string;
  defeats: number[];
  snippet?: string;
}

export const PATTERNS: Pattern[] = [
  {
    id: "P1",
    name: "Dual-LLM Separation",
    problem:
      "Any LLM that reads raw user text can be steered by it, no matter how good the system prompt is.",
    shape:
      "A quarantined, tool-less parser LLM converts every piece of untrusted content — chat, OCR output, PDF text — into strict JSON conforming to a registered schema before any privileged agent sees it. Any deviation from the schema is a parser_schema_violation and the input is quarantined outright.",
    citation:
      'Simon Willison, "Prompt Injection Explained"; Anthropic, Constitutional Classifiers',
    codeRef: "agents/parser/quarantine.py:88",
    testRef: "tests/live/test_attack_001.py::test_variants",
    residual:
      "The parser is a real LLM and can itself be confused — but a confused parser can only emit malformed JSON, which schema validation catches. It cannot take an action.",
    defeats: [1, 2, 3, 4, 5, 6, 7, 8, 66],
  },
  {
    id: "P2",
    name: "Deterministic Orchestration",
    problem:
      "If a workflow's next step is decided by an LLM, convincing the LLM is the whole attack.",
    shape:
      "Claim-workflow transitions are computed by plain Python from database state: INTAKE → IDENTITY_PENDING → IDENTITY_VERIFIED → PROCESSING → DECIDED → SETTLED/ESCALATED/DENIED → CLOSED. LLMs may propose a next step; the orchestrator's guard functions decide whether the database actually supports it. No backward transitions, no stage skipping — any attempt writes a transition_violation audit row.",
    citation: "TLA+ formal spec (formal/workflow.tla); 102/102 conformance tests",
    codeRef: "orchestrator/state_machine.py:142",
    testRef: "formal/check_spec.py — 3,456 states enumerated",
    residual:
      "Deterministic code has no judgment — genuinely ambiguous edge cases still route to ESCALATED rather than being handled cleverly.",
    defeats: [9, 11, 13, 43, 46, 61, 63, 64],
  },
  {
    id: "P3",
    name: "Information Flow Control",
    problem: "A model that can see SECRET data can eventually be talked into repeating it.",
    shape:
      "Every datum carries a static trust label — PUBLIC < PERSONAL < CONFIDENTIAL < SECRET — plus an orthogonal UNTRUSTED taint for anything user-supplied. Every DB column and every tool's inputs/outputs declare a label; the egress filter (P10) is the final enforcement point, and every label check writes an audit row.",
    citation: 'Myers & Liskov, "Complete, Safe Information Flow" (POPL \'97)',
    codeRef: "security/ifc/labels.py:41",
    testRef: "tests/live/test_attack_020.py::test_variants",
    residual:
      "RR-01: the semantic classifier used as one detection signal inside this layer is heuristic, not a proof — 2 logged false positives on clean traffic are on the record.",
    defeats: [3, 7, 10, 15, 16, 20, 22, 24, 33, 37, 76, 77],
  },
  {
    id: "P4",
    name: "Capability-Scoped Tools",
    problem:
      '"Convince the LLM to call X" doesn\'t work if X requires a credential the LLM cannot produce.',
    shape:
      "Every tool call carries a token — agent_id × tool × scope × expiry — signed by the orchestrator's Ed25519 key. The tool registry verifies all five fields server-side before anything executes. The LLM can request a call; it cannot mint or widen a token.",
    snippet:
      '{\n  "token_id": "uuid",\n  "agent_id": "claims_processor",\n  "tool": "score_fraud",\n  "scope": { "claim_id": "CLM-000123" },\n  "expires_at": "ISO-8601",\n  "signature": "ed25519(...)"\n}',
    citation: "Dennis & Van Horn capabilities model (1966); object-capability model",
    codeRef: "security/capabilities/tokens.py:57",
    testRef: "tests/live/test_attack_029.py::test_variants",
    residual:
      "Token issuance is itself trusted code — a bug in the orchestrator's issuance path, not the LLM, would be the way around this.",
    defeats: [10, 29, 32, 33, 39, 41, 53, 55, 73],
  },
  {
    id: "P5",
    name: "Sandboxed File Processing",
    problem: "A PDF or image is an attacker-controlled program if you let it be one.",
    shape:
      "All file parsing runs in Docker containers with --network=none, read-only rootfs, and dropped capabilities. Filesystems are ephemeral with no persistence between jobs. PDFs carrying JavaScript, embedded executables, or active forms are rejected before parsing starts.",
    citation: "defense-in-depth for untrusted-file ingress",
    codeRef: "ingress/sandbox/pdf_runner.py:29",
    testRef: "tests/live/test_attack_002.py::test_variants",
    residual:
      "Sandbox escape (#68) is treated as architecturally inapplicable given the container hardening — that claim rests on the container runtime, not this codebase.",
    defeats: [2, 8, 30, 68, 74],
  },
  {
    id: "P6",
    name: "Vision Pre-Redaction",
    problem:
      "Extracting and filtering embedded text doesn't stop a vision model from reading it visually.",
    shape:
      "An OCR pass finds every text region in an incoming image. Those bounding boxes are pixel-blurred to opaque blocks before the vision model ever sees the image. The OCR text itself is routed separately, through the text sanitisation pipeline, tagged UNTRUSTED.",
    citation: "removes the visual channel entirely, rather than trying to filter it",
    codeRef: "ingress/vision/redact.py:64",
    testRef: "tests/live/test_attack_006.py::test_variants",
    residual:
      "RR-03: lightweight LSB chi-square steganography heuristics downstream flag but do not block — a carefully-encoded payload could still reach the redacted image unflagged.",
    defeats: [5, 6],
  },
  {
    id: "P7",
    name: "DB-Enforced Tenancy",
    problem:
      "A missing WHERE clause in application code is usually how cross-customer leaks happen.",
    shape:
      "PostgreSQL row-level security policies enforce per-customer scope at the database layer, keyed to SET LOCAL app.current_customer_id after JWT verification. Even a fully compromised application layer cannot pull another customer's row — the DB itself refuses.",
    citation: "isolation enforced below the application, not by it",
    codeRef: "db/policies/rls.sql:18",
    testRef: "tests/live/test_attack_028.py::test_variants",
    residual:
      "RLS depends on the session variable being set correctly on every connection — a missed SET LOCAL is a single point of failure for this pattern specifically.",
    defeats: [20, 23, 27, 28, 36, 42, 71],
  },
  {
    id: "P8",
    name: "Per-Agent Asymmetric Identity",
    problem:
      "If every agent shares one identity, compromising one agent compromises all of them.",
    shape:
      "Each agent generates its own Ed25519 keypair at deployment. Inter-agent messages are signed; recipients verify against a published public-key registry. Compromising one agent's key reveals nothing about any other agent's key.",
    citation:
      "honest scope: in the single-host demo this is pattern demonstration, not a real network boundary",
    codeRef: "agents/identity/keys.py:22",
    testRef: "assertion test — CI: test_identity_isolation",
    residual:
      "RR-02: promoting to a real multi-host deployment requires swapping transports, not redesigning the identity model — that migration hasn't been done here.",
    defeats: [38, 40, 44, 45, 47, 48, 49, 67],
  },
  {
    id: "P9",
    name: "Hash-Chained Audit Log",
    problem:
      "A tampered log is worse than no log — it looks trustworthy right up until it matters.",
    shape:
      "row_hash = sha256(prev_hash || canonical_json(row)). Every tool call, agent message, sanitisation event, state transition, and security event is one INSERT-only row. The Postgres role that writes audit rows has no UPDATE or DELETE grant — tampering with a historical row breaks the chain, detectably, on demand.",
    snippet: "row_hash = sha256(prev_hash || canonical_json(row_minus_hash))",
    citation: "verifiable on demand — see Verification",
    codeRef: "audit/hash_chain.py:9",
    testRef: "assertion test — CI: test_chain_tamper_detection",
    residual:
      "Detection is on-demand, not continuous — a break between verifications is caught at the next check, not the instant it happens.",
    defeats: [18, 62],
  },
  {
    id: "P10",
    name: "Egress Output Filter",
    problem:
      "Every other defense here is upstream of a mistake reaching the customer — this is the last one.",
    shape:
      "Every customer-visible string passes four steps in strict order: (1) SECRET label kill-switch — any SECRET-labelled datum in a response replaces the whole response; (2) URL allowlist strip — non-allowlisted URLs become [external link removed], run before the PII check because URLs can smuggle PII; (3) PII regex — SSNs, card numbers, phone numbers, any hit blocks and audits; (4) length cap, run last so truncation can't silently discard PII in the tail.",
    citation: "the order is itself the security property",
    codeRef: "egress/filter.py:12",
    testRef: "tests/live/test_attack_025.py::test_variants",
    residual:
      "RR-04: one partial leak is on the public record — a reflected query fragment on an allowlisted domain slipped past the URL step before the PII regex caught the tail. Filter order was patched afterward; the trace stays public.",
    defeats: [1, 21, 25, 26, 27, 65, 75, 78],
  },
  {
    id: "P11",
    name: "Token & Cost Budgets",
    problem:
      "An unbounded agent loop is a denial-of-wallet attack whether or not anyone intended it that way.",
    shape:
      "Per-session token counters (50K hard cap), per-tool call counters, per-tool-per-minute rate limits, monthly spend caps, and circuit breakers that trip after consecutive failures.",
    citation: "visible live: adversarial-agent spend vs. its $50/mo cap",
    codeRef: "orchestrator/budgets.py:33",
    testRef: "tests/live/test_attack_069.py::test_variants",
    residual:
      "Budgets bound cost and call count, not correctness — a cheap, low-volume attack that stays under every threshold isn't caught by this pattern alone.",
    defeats: [19, 31, 34, 69, 70],
  },
  {
    id: "P12",
    name: "Signed System Prompts",
    problem: "A system prompt that can be changed without review is a standing invitation to drift.",
    shape:
      "A prompt registry holds each agent's current system prompt. At runtime, every agent verifies the loaded prompt's hash against a signed manifest. Changing a prompt requires a reviewed pull request that updates the manifest.",
    citation: "prompt registry + signed manifest",
    codeRef: "agents/prompts/registry.py:47",
    testRef: "assertion test — CI: test_prompt_manifest_integrity",
    residual:
      "This defends the prompt's integrity, not its content — a reviewed-in mistake in the prompt itself would ship as intended.",
    defeats: [4, 9, 12, 14, 17, 52, 54],
  },
];
