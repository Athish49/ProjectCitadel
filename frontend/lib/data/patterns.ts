export interface Pattern {
  id: string;
  name: string;
  problem: string;
  shape: string;
  code?: string;
  codeRef: string;
  testRef: string;
  risk: string;
  ref: string;
  defeats: number[];
}

export const PATTERNS: Pattern[] = [
  {
    id: "P1",
    name: "Dual-LLM separation",
    problem:
      "Any LLM that reads raw user text can be steered by it, however good the system prompt.",
    shape:
      "A quarantined, tool-less parser turns all untrusted content into strict JSON before any privileged agent sees it. Deviation is a parser_schema_violation and the input is quarantined.",
    codeRef: "backend/agent_system/parser/intake_parser.py",
    testRef: "backend/tests/unit/test_attack_suite.py::TestAttack01DirectPromptInjection",
    risk: "The parser is a real LLM and can be confused. It can only emit malformed JSON, which validation catches.",
    ref: "Willison, “Prompt Injection Explained” · Anthropic, Constitutional Classifiers",
    defeats: [1, 2, 3, 4, 5, 6, 7, 8, 66],
  },
  {
    id: "P2",
    name: "Deterministic orchestration",
    problem: "If an LLM decides the next workflow step, convincing the LLM is the whole attack.",
    shape:
      "Transitions are computed by plain Python from database state. LLMs propose; guard functions decide. No backward moves, no skipped stages.",
    codeRef: "backend/agent_system/orchestrator/transitions.py",
    testRef: "backend/tests/unit/test_orchestrator.py",
    risk: "Deterministic code has no judgment. Ambiguous edge cases route to ESCALATED.",
    ref: "TLA+ formal spec · formal/workflow.tla",
    defeats: [9, 11, 13, 43, 46, 61, 63, 64],
  },
  {
    id: "P3",
    name: "Information flow control",
    problem: "A model that can see SECRET data can eventually be talked into repeating it.",
    shape:
      "Every datum carries a label: PUBLIC < PERSONAL < CONFIDENTIAL < SECRET, plus an UNTRUSTED taint. Columns and tools declare labels; every check writes an audit row.",
    codeRef: "backend/agent_system/ifc/labels.py",
    testRef: "backend/tests/unit/test_ifc.py",
    risk: "RR-01. The semantic classifier is a heuristic signal, not a proof. Two false positives on clean traffic are on record.",
    ref: "Myers & Liskov, “Complete, Safe Information Flow” (POPL ’97)",
    defeats: [3, 7, 10, 15, 16, 20, 22, 24, 33, 37, 76, 77],
  },
  {
    id: "P4",
    name: "Capability-scoped tools",
    problem: "“Convince the LLM to call X” fails if X needs a credential the LLM cannot produce.",
    shape:
      "Every tool call carries a token signed with the orchestrator’s Ed25519 key. The registry verifies it server-side. The LLM cannot mint or widen one.",
    code:
      '{ "agent_id": "claims_processor", "tool": "score_fraud",\n  "scope": { "claim_id": "CLM-000123" },\n  "expires_at": "ISO-8601", "signature": "ed25519(...)" }',
    codeRef: "backend/agent_system/tools/capability_tokens.py",
    testRef: "backend/tests/unit/test_capability_tokens.py",
    risk: "Token issuance is trusted code. A bug in the issuance path would be the way around.",
    ref: "Dennis & Van Horn capabilities model (1966)",
    defeats: [10, 29, 32, 33, 39, 41, 53, 55, 73],
  },
  {
    id: "P5",
    name: "Sandboxed file processing",
    problem: "A PDF or image is an attacker-controlled program if you let it be one.",
    shape:
      "Files are parsed in containers with --network=none, a read-only rootfs and dropped capabilities. PDFs with JavaScript, executables or active forms are rejected first.",
    codeRef: "backend/agent_system/sanitisation/pdf.py",
    testRef: "backend/tests/unit/test_pdf_sandbox.py",
    risk: "Sandbox escape is treated as inapplicable. That claim rests on the container runtime, not this codebase.",
    ref: "Defense in depth for untrusted-file ingress",
    defeats: [2, 8, 30, 68, 74],
  },
  {
    id: "P6",
    name: "Vision pre-redaction",
    problem: "Filtering extracted text does not stop a vision model from reading it visually.",
    shape:
      "OCR finds every text region and blurs it to an opaque block before the vision model looks. The text travels separately, tagged UNTRUSTED.",
    codeRef: "backend/agent_system/sanitisation/redaction.py",
    testRef: "backend/tests/unit/test_vision_redaction.py",
    risk: "RR-03. Steganography heuristics flag but do not block. A careful payload could pass unflagged.",
    ref: "Removes the visual channel instead of filtering it",
    defeats: [5, 6],
  },
  {
    id: "P7",
    name: "DB-enforced tenancy",
    problem: "A missing WHERE clause is how most cross-customer leaks happen.",
    shape:
      "Postgres RLS enforces per-customer scope, keyed to SET LOCAL app.current_customer_id after JWT verification. A compromised app layer still cannot read another row.",
    codeRef: "backend/db/migrations/001_initial_schema.sql",
    testRef: "backend/tests/integration/test_rls.py",
    risk: "Depends on the session variable being set on every connection. A missed SET LOCAL is a single point of failure.",
    ref: "Isolation enforced below the application",
    defeats: [20, 23, 27, 28, 36, 42, 71],
  },
  {
    id: "P8",
    name: "Per-agent identity",
    problem: "If every agent shares one identity, compromising one compromises all.",
    shape:
      "Each agent holds its own Ed25519 keypair. Inter-agent messages are signed and verified against a public-key registry.",
    codeRef: "backend/agent_system/identity/keys.py",
    testRef: "backend/tests/unit/test_ed25519_signing.py",
    risk: "RR-02. On one host this is a pattern demonstration, not a network boundary. The multi-host migration is not done.",
    ref: "Honest scope: single-host demo",
    defeats: [38, 40, 44, 45, 47, 48, 49, 67],
  },
  {
    id: "P9",
    name: "Hash-chained audit log",
    problem: "A tampered log is worse than no log. It looks trustworthy until it matters.",
    shape:
      "Every action is one INSERT-only row whose hash includes the previous row’s. The writing role has no UPDATE or DELETE grant.",
    code: "row_hash = sha256(prev_hash || canonical_json(row_minus_hash))",
    codeRef: "backend/audit/chain.py",
    testRef: "backend/tests/unit/test_audit_chain.py",
    risk: "Detection is on demand, not continuous.",
    ref: "Verifiable on demand",
    defeats: [18, 62],
  },
  {
    id: "P10",
    name: "Egress output filter",
    problem: "Every other defense sits upstream of a mistake reaching the customer. This is the last one.",
    shape:
      "Four steps in strict order: SECRET kill-switch, URL allowlist strip, PII regex, length cap. The order is itself the security property.",
    codeRef: "backend/agent_system/egress/filter.py",
    testRef: "backend/tests/unit/test_egress_filter.py",
    risk: "RR-04. One partial leak on record: a reflected query fragment slipped past the URL step. The order was patched; the trace is public.",
    ref: "Order explained on the Architecture page",
    defeats: [1, 21, 25, 26, 27, 65, 75, 78],
  },
  {
    id: "P11",
    name: "Token & cost budgets",
    problem: "An unbounded agent loop is a denial-of-wallet attack, intended or not.",
    shape:
      "A 50K-token session cap, per-tool call counters, per-minute rate limits, monthly spend caps and circuit breakers after consecutive failures.",
    codeRef: "backend/agent_system/orchestrator/budgets.py",
    testRef: "backend/tests/unit/test_orchestrator.py::TestConsumeTokens",
    risk: "Budgets bound cost, not correctness. A cheap, low-volume attack stays under every threshold.",
    ref: "Visible live: adversarial agent spend against its $50 monthly cap",
    defeats: [19, 31, 34, 69, 70],
  },
  {
    id: "P12",
    name: "Signed system prompts",
    problem: "A system prompt that can change without review is a standing invitation to drift.",
    shape:
      "Each agent verifies its loaded prompt hash against a signed manifest at runtime. Changes need a reviewed pull request.",
    codeRef: "backend/agent_system/orchestrator/prompts.py",
    testRef: "backend/tests/unit/test_prompt_registry.py",
    risk: "Defends prompt integrity, not content. A reviewed-in mistake ships as intended.",
    ref: "Prompt registry + signed manifest",
    defeats: [4, 9, 12, 14, 17, 52, 54],
  },
];
