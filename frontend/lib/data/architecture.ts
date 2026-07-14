// All static data extracted from Architecture.dc.html

// ── Diagram ──────────────────────────────────────────────────────────────────

export const ZONE_COLORS = {
  untrusted: "#E5484D",
  quarantine: "#E2A336",
  control: "#3ECF8E",
  actors: "#5B8DEF",
  data: "rgba(255,255,255,0.55)",
} as const;

export interface DiagZone {
  id: string;
  label: string;
  x: number;
  w: number;
  color: string;
  desc: string;
}

export const DIAG_ZONES: DiagZone[] = [
  { id: "untrusted",  label: "Untrusted zone",         x: 20,  w: 190, color: ZONE_COLORS.untrusted,  desc: "raw input — sanitised, sandboxed, redacted" },
  { id: "quarantine", label: "Quarantine",              x: 250, w: 190, color: ZONE_COLORS.quarantine, desc: "parser LLM · zero tools · JSON out only" },
  { id: "control",    label: "Deterministic control",   x: 480, w: 190, color: ZONE_COLORS.control,    desc: "orchestrator code · no LLM to compromise" },
  { id: "actors",     label: "Privileged actors",       x: 710, w: 190, color: ZONE_COLORS.actors,     desc: "capability-scoped LLM agents" },
  { id: "data",       label: "Labelled data",           x: 940, w: 190, color: ZONE_COLORS.data,       desc: "IFC labels · RLS · hash-chained audit" },
];

export interface DiagNode {
  id: string;
  zone: string;
  x: number;
  y: number;
  name: string;
  sub: string;
  detail: string;
}

// W=190, H=54 per node; viewBox = 1160x460
export const NODE_W = 190;
export const NODE_H = 54;
export const SVG_W = 1160;
export const SVG_H = 460;

export const DIAG_NODES: DiagNode[] = [
  { id: "ingress-sanitiser",   zone: "untrusted",  x: 20,  y: 150, name: "Ingress Sanitiser",    sub: "P1 · UNTRUSTED",   detail: "Strips zero-width/RTL characters, scans for injection templates, tags everything UNTRUSTED before it goes anywhere near quarantine." },
  { id: "file-sandbox",        zone: "untrusted",  x: 20,  y: 250, name: "File Sandbox",          sub: "P5 · UNTRUSTED",   detail: "PDFs parsed in a network-isolated, read-only container; rejected outright if they carry JS or embedded executables." },
  { id: "vision-pre-redact",   zone: "untrusted",  x: 20,  y: 350, name: "Vision Pre-Redact",    sub: "P6 · UNTRUSTED",   detail: "OCR locates on-image text and pixel-blurs it before the vision model ever looks; extracted text re-enters the text pipeline." },
  { id: "quarantined-parser",  zone: "quarantine", x: 250, y: 250, name: "Quarantined Parser",   sub: "P1 · QUARANTINE",  detail: "The only LLM that reads raw user text. Zero tools, no privileged data, one legal output shape: strict JSON or quarantine." },
  { id: "egress-filter",       zone: "control",    x: 480, y: 110, name: "Egress Filter",         sub: "P10 · TRUSTED",    detail: "Four checks in a fixed order on every customer-visible string — SECRET kill-switch, URL allowlist, PII regex, length cap." },
  { id: "orchestrator",        zone: "control",    x: 480, y: 250, name: "Orchestrator",           sub: "P2 · TRUSTED",     detail: "Plain Python. Reads database state, decides the next legal transition, mints capability tokens. Nothing here for a jailbreak to reach." },
  { id: "capability-registry", zone: "control",    x: 480, y: 390, name: "Capability Registry",  sub: "P4 · TRUSTED",     detail: "Verifies signature, agent, tool, scope, and expiry on every token before a privileged call is allowed to run." },
  { id: "intake-actor",        zone: "actors",     x: 710, y: 100, name: "Intake Actor",          sub: "P4 · ACTORS",      detail: "Turns parsed intake JSON into ready_for_identity / needs_more_info / reject_as_out_of_scope. No workflow authority of its own." },
  { id: "identity-verifier",   zone: "actors",     x: 710, y: 200, name: "Identity Verifier",    sub: "P4 · ACTORS",      detail: "Coordinates identity checks through a server-side function that returns a boolean and a retry count — never the PII itself." },
  { id: "claims-processor",    zone: "actors",     x: 710, y: 300, name: "Claims Processor",     sub: "P4 · ACTORS",      detail: "The reasoning-heavy actor: damage, coverage, fraud signal. Fraud scores never enter its context, only the decision." },
  { id: "settlement-actor",    zone: "actors",     x: 710, y: 400, name: "Settlement Actor",     sub: "P4 · ACTORS",      detail: "Applies policy math and drafts the summary; payout is re-verified server-side against fraud decision and the auto-approve cap." },
  { id: "postgres-rls",        zone: "data",       x: 940, y: 150, name: "Postgres + RLS",       sub: "P7 · DATA",        detail: "Row-level security scopes every read to the calling agent's own claim, beneath the application layer." },
  { id: "pii-vault",           zone: "data",       x: 940, y: 250, name: "PII Vault",            sub: "P7 · DATA",        detail: "Argon2id-hashed SSNs, AES-256-GCM-encrypted bank details. No agent holds SELECT — only one boolean-returning function." },
  { id: "audit-log",           zone: "data",       x: 940, y: 390, name: "Audit Log (chained)",  sub: "P9 · DATA",        detail: "Hash-chained, append-only. Every privileged hop writes exactly one row; tampering breaks the chain visibly." },
];

// Pre-compute bezier path strings (curve = cubic bezier using anchor points)
function anchorR(nodeId: string): [number, number] {
  const n = DIAG_NODES.find(n => n.id === nodeId)!;
  return [n.x + NODE_W, n.y + NODE_H / 2];
}
function anchorL(nodeId: string): [number, number] {
  const n = DIAG_NODES.find(n => n.id === nodeId)!;
  return [n.x, n.y + NODE_H / 2];
}
function curve(from: string, to: string): string {
  const [ax, ay] = anchorR(from);
  const [bx, by] = anchorL(to);
  const mid = (ax + bx) / 2;
  return `M ${ax} ${ay} C ${mid} ${ay}, ${mid} ${by}, ${bx} ${by}`;
}
function vertical(from: string, to: string, cx: number): string {
  const nf = DIAG_NODES.find(n => n.id === from)!;
  const nt = DIAG_NODES.find(n => n.id === to)!;
  const fromDown = nf.y < nt.y;
  const y1 = fromDown ? nf.y + NODE_H : nf.y;
  const y2 = fromDown ? nt.y : nt.y + NODE_H;
  return `M ${cx} ${y1} L ${cx} ${y2}`;
}

export type EdgeType = "untrusted" | "control" | "token" | "data" | "audit";

export interface DiagEdge {
  id: string;
  from: string;
  to: string;
  type: EdgeType;
  color: string;
  d: string;
}

const TYPE_COLORS: Record<EdgeType, string> = {
  untrusted: "#E5484D",
  control:   "#3ECF8E",
  token:     "#8A6FA8",
  data:      "#5B8DEF",
  audit:     "rgba(255,255,255,0.4)",
};

export const DIAG_EDGES: DiagEdge[] = [
  { id: "e1",  from: "ingress-sanitiser",   to: "quarantined-parser",  type: "untrusted", color: TYPE_COLORS.untrusted, d: curve("ingress-sanitiser",   "quarantined-parser") },
  { id: "e2",  from: "file-sandbox",        to: "quarantined-parser",  type: "untrusted", color: TYPE_COLORS.untrusted, d: curve("file-sandbox",        "quarantined-parser") },
  { id: "e3",  from: "vision-pre-redact",   to: "quarantined-parser",  type: "untrusted", color: TYPE_COLORS.untrusted, d: curve("vision-pre-redact",   "quarantined-parser") },
  { id: "e4",  from: "quarantined-parser",  to: "orchestrator",        type: "control",   color: TYPE_COLORS.control,   d: curve("quarantined-parser",  "orchestrator") },
  { id: "e5",  from: "egress-filter",       to: "orchestrator",        type: "control",   color: TYPE_COLORS.control,   d: vertical("egress-filter",    "orchestrator", 575) },
  { id: "e6",  from: "orchestrator",        to: "capability-registry", type: "control",   color: TYPE_COLORS.control,   d: vertical("orchestrator",     "capability-registry", 575) },
  { id: "e7",  from: "capability-registry", to: "intake-actor",        type: "token",     color: TYPE_COLORS.token,     d: curve("capability-registry", "intake-actor") },
  { id: "e8",  from: "capability-registry", to: "identity-verifier",   type: "token",     color: TYPE_COLORS.token,     d: curve("capability-registry", "identity-verifier") },
  { id: "e9",  from: "capability-registry", to: "claims-processor",    type: "token",     color: TYPE_COLORS.token,     d: curve("capability-registry", "claims-processor") },
  { id: "e10", from: "capability-registry", to: "settlement-actor",    type: "token",     color: TYPE_COLORS.token,     d: curve("capability-registry", "settlement-actor") },
  { id: "e11", from: "egress-filter",       to: "intake-actor",        type: "control",   color: TYPE_COLORS.control,   d: curve("egress-filter",       "intake-actor") },
  { id: "e12", from: "intake-actor",        to: "postgres-rls",        type: "data",      color: TYPE_COLORS.data,      d: curve("intake-actor",        "postgres-rls") },
  { id: "e13", from: "identity-verifier",   to: "pii-vault",           type: "data",      color: TYPE_COLORS.data,      d: curve("identity-verifier",   "pii-vault") },
  { id: "e14", from: "claims-processor",    to: "postgres-rls",        type: "data",      color: TYPE_COLORS.data,      d: curve("claims-processor",    "postgres-rls") },
  { id: "e15", from: "claims-processor",    to: "pii-vault",           type: "data",      color: TYPE_COLORS.data,      d: curve("claims-processor",    "pii-vault") },
  { id: "e16", from: "settlement-actor",    to: "postgres-rls",        type: "data",      color: TYPE_COLORS.data,      d: curve("settlement-actor",    "postgres-rls") },
  { id: "e17", from: "settlement-actor",    to: "audit-log",           type: "audit",     color: TYPE_COLORS.audit,     d: curve("settlement-actor",    "audit-log") },
  { id: "e18", from: "orchestrator",        to: "audit-log",           type: "audit",     color: TYPE_COLORS.audit,     d: curve("orchestrator",        "audit-log") },
];

export const DIAG_LEGEND = [
  { color: "#E5484D",              label: "untrusted input" },
  { color: "#3ECF8E",              label: "schema / control" },
  { color: "#8A6FA8",              label: "capability token" },
  { color: "#5B8DEF",              label: "labelled data" },
  { color: "rgba(255,255,255,0.4)", label: "audit log" },
];

// ── State machine ────────────────────────────────────────────────────────────

export interface ScenarioStep {
  state: string;
  tag: string;
  tagColor: string;
  msg: string;
}

export interface Scenario {
  name: string;
  steps: ScenarioStep[];
}

const g = "#3ECF8E", r = "#E5484D", a = "#E2A336", w = "rgba(255,255,255,0.6)";

export const SCENARIOS: Scenario[] = [
  {
    name: "Happy path",
    steps: [
      { state: "INTAKE",             tag: "guard_pass",    tagColor: g, msg: "intake_complete=true in DB → INTAKE → IDENTITY_PENDING" },
      { state: "IDENTITY_PENDING",   tag: "identity_ok",   tagColor: g, msg: "verify_identity() → {verified: true, attempts_remaining: 2}" },
      { state: "IDENTITY_VERIFIED",  tag: "guard_pass",    tagColor: g, msg: "identity_log.verified=true for session → PROCESSING" },
      { state: "PROCESSING",         tag: "tools",         tagColor: w, msg: "classify_damage: minor · lookup_coverage: applies · score_fraud → decision=CLEAR (score IFC-stripped)" },
      { state: "DECIDED",            tag: "guard_pass",    tagColor: g, msg: "fraud=CLEAR AND $1,840 ≤ auto_approve_limit → SETTLED" },
      { state: "SETTLED",            tag: "payout",        tagColor: g, msg: "request_payout: state=DECIDED verified, session-bound payee resolved" },
      { state: "CLOSED",             tag: "closed",        tagColor: w, msg: "claim closed · 14 audit rows written, chain intact" },
    ],
  },
  {
    name: "Fraud-flagged",
    steps: [
      { state: "INTAKE",             tag: "guard_pass",    tagColor: g, msg: "intake_complete=true → IDENTITY_PENDING" },
      { state: "IDENTITY_PENDING",   tag: "identity_ok",   tagColor: g, msg: "verified=true" },
      { state: "IDENTITY_VERIFIED",  tag: "guard_pass",    tagColor: g, msg: "→ PROCESSING" },
      { state: "PROCESSING",         tag: "fraud_flag",    tagColor: a, msg: "score_fraud → decision=FLAG · risk score + factors never enter LLM context" },
      { state: "DECIDED",            tag: "guard_route",   tagColor: a, msg: "fraud=FLAG → ESCALATED (SETTLED is unreachable by construction)" },
      { state: "ESCALATED",          tag: "escalated",     tagColor: a, msg: "customer receives escalation acknowledgment — not a settlement amount" },
    ],
  },
  {
    name: "Identity lockout",
    steps: [
      { state: "INTAKE",             tag: "guard_pass",    tagColor: g, msg: "intake_complete=true → IDENTITY_PENDING" },
      { state: "IDENTITY_PENDING",   tag: "identity_fail", tagColor: r, msg: "attempt 1/3 failed · {verified: false, attempts_remaining: 2}" },
      { state: "IDENTITY_PENDING",   tag: "identity_fail", tagColor: r, msg: "attempt 2/3 failed · attempts_remaining: 1" },
      { state: "IDENTITY_PENDING",   tag: "identity_fail", tagColor: r, msg: "attempt 3/3 failed · attempts_remaining: 0" },
      { state: "LOCKED",             tag: "session_locked",tagColor: r, msg: "lockout enforced at the server-side function — not conversationally. All further requests denied." },
    ],
  },
  {
    name: "Forced transition",
    steps: [
      { state: "INTAKE",             tag: "guard_pass",       tagColor: g, msg: "intake_complete=true → IDENTITY_PENDING" },
      { state: "IDENTITY_PENDING",   tag: "identity_ok",      tagColor: g, msg: "verified=true → IDENTITY_VERIFIED → PROCESSING" },
      { state: "PROCESSING",         tag: "actor_proposal",   tagColor: w, msg: "compromised actor proposes: advance_stage(PROCESSING → SETTLED)" },
      { state: "PROCESSING",         tag: "transition_violation", tagColor: r, msg: "edge not in _VALID_EDGES · rejected in code · transition_violation audit row written" },
      { state: "PROCESSING",         tag: "unchanged",        tagColor: w, msg: "state unchanged — the LLM suggested, the orchestrator declined" },
    ],
  },
];

export const MAIN_STATES = ["INTAKE", "IDENTITY_PENDING", "IDENTITY_VERIFIED", "PROCESSING", "DECIDED"];

export const BRANCH_STATES = [
  { name: "SETTLED",   guard: "fraud=CLEAR ∧ amount ≤ cap" },
  { name: "ESCALATED", guard: "fraud=FLAG/DENY ∨ amount > cap" },
  { name: "DENIED",    guard: "coverage does not apply" },
];

export const GUARDS = [
  { edge: "INTAKE → IDENTITY_PENDING",             req: "intake_complete = true in DB" },
  { edge: "IDENTITY_PENDING → IDENTITY_VERIFIED",  req: "identity_log.verified = true for the current session" },
  { edge: "PROCESSING → DECIDED",                  req: "non-null damage assessment + coverage calculation + fraud decision" },
  { edge: "DECIDED → SETTLED",                     req: "fraud_decision = CLEAR AND amount ≤ auto_approve_limit" },
  { edge: "DECIDED → ESCALATED",                   req: "fraud FLAG/DENY OR amount > limit — the only route past a flag is a human" },
];

export const LIMITS = [
  { name: "Per-session token budget",  value: "50,000 hard cap" },
  { name: "Per-tool call budget",      value: "per session" },
  { name: "Per-tool rate limit",       value: "per minute" },
  { name: "Circuit breaker",           value: "trips on consecutive failures" },
];

// ── Actor cards ──────────────────────────────────────────────────────────────

export interface ActorTool {
  sig: string;
  note: string;
}

export interface ActorCard {
  name: string;
  model: string;
  labelColor: string;
  role: string;
  tools: ActorTool[];
  access: string;
  cannot: string;
}

export const ACTOR_CARDS: ActorCard[] = [
  {
    name: "Intake Actor", model: "Claude Haiku 4.5", labelColor: "#5FA8A0",
    role: "Decides intake outcome from the parser's structured JSON: ready_for_identity, needs_more_info, or reject_as_out_of_scope. Handles FAQ queries against PUBLIC RAG with no identity required.",
    tools: [
      { sig: "request_more_info(field)",       note: "asks for a missing field" },
      { sig: "mark_intake_complete(summary)",  note: "sets the DB flag the guard reads" },
      { sig: "search_public_faq(query)",       note: "PUBLIC RAG only" },
    ],
    access: "PUBLIC · PERSONAL (own claim, RLS)",
    cannot: "cannot: read CONFIDENTIAL/SECRET · make workflow decisions · see raw user text",
  },
  {
    name: "Identity Verifier", model: "Claude Haiku 4.5", labelColor: "#5FA8A0",
    role: "Coordinates identity verification. PII never touches its context: the check is a server-side function against the vault that returns a boolean and a retry count.",
    tools: [
      { sig: "request_identity_check(policy, dob_hint, ssn_last4)", note: "returns {verified, attempts_remaining} only" },
    ],
    access: "PERSONAL (boolean result only)",
    cannot: "cannot: fetch raw PII · read the vault · override the 3-attempt lockout",
  },
  {
    name: "Claims Processor", model: "Claude Sonnet 4.6", labelColor: "#E2A336",
    role: "The reasoning-heavy actor. Composes the structured assessment — damage, coverage, fraud signal, policy lookup — and handles post-identity inquiry intents.",
    tools: [
      { sig: "classify_damage(evidence_ref)",         note: "deterministic stub" },
      { sig: "score_fraud(claim_id)",                 note: "SECRET record; only decision forwarded — score IFC-stripped" },
      { sig: "search_policy_docs(query)",             note: "CONFIDENTIAL RAG, capability-gated" },
      { sig: "search_fraud_rules(query)",             note: "returns doc_id + source ref, never rule text" },
      { sig: "lookup_claim_status(claim_id)",         note: "RLS-scoped" },
      { sig: "capture_complaint(session, cat, desc)", note: "writes + triggers ESCALATED" },
    ],
    access: "CONFIDENTIAL (own claim, RLS)",
    cannot: "cannot: read other customers' data · surface fraud scores or rule text · issue tokens",
  },
  {
    name: "Settlement Actor", model: "Claude Sonnet 4.6", labelColor: "#E2A336",
    role: "Applies policy math and drafts the customer-facing summary. Payout is verified server-side against orchestrator state, fraud decision, and the auto-approve cap.",
    tools: [
      { sig: "calculate_settlement(claim_id)",   note: "pure deterministic function" },
      { sig: "request_payout(claim_id)",         note: "server-side; payee session-bound; any failed check → deny + audit" },
      { sig: "draft_summary(structured_decision)", note: "output passes the egress filter" },
    ],
    access: "CONFIDENTIAL (own claim, RLS)",
    cannot: "cannot: choose the payee · override fraud decisions · modify the amount",
  },
];

// ── Ingress columns ──────────────────────────────────────────────────────────

export interface IngressCol {
  title: string;
  noteColor: string;
  note: string;
  steps: { n: string; text: string }[];
}

export const INGRESS_COLS: IngressCol[] = [
  {
    title: "TEXT", noteColor: "#8A6FA8", note: "→ UNTRUSTED → parser LLM",
    steps: [
      { n: "01", text: "Unicode NFKC normalisation; strip zero-width and RTL-override characters" },
      { n: "02", text: "Static pattern detection against a curated injection-template list" },
      { n: "03", text: "Semantic classifier — a logged detection signal, not the primary defense" },
      { n: "04", text: "UNTRUSTED label attached; wrapped in untrusted delimiters" },
    ],
  },
  {
    title: "IMAGE", noteColor: "#8A6FA8", note: "→ redacted image + separate UNTRUSTED text stream",
    steps: [
      { n: "01", text: "EXIF / XMP / IPTC metadata stripped; image re-encoded" },
      { n: "02", text: "OCR locates all text regions; bounding boxes pixel-blurred to opaque blocks before the vision model looks" },
      { n: "03", text: "OCR text routed separately through the text pipeline" },
      { n: "04", text: "LSB chi-square steganography heuristics — flag + quarantine, honest about being heuristic" },
    ],
  },
  {
    title: "PDF", noteColor: "#8A6FA8", note: "→ extracted text → text pipeline",
    steps: [
      { n: "01", text: "Parsed inside a container: no network, read-only rootfs, ephemeral filesystem" },
      { n: "02", text: "Rejected outright if it contains JavaScript, embedded executables, or active forms" },
      { n: "03", text: "Hidden-content detection: white-on-white, microscopic fonts, off-page content" },
      { n: "04", text: "Original and sanitised SHA-256 both kept for forensic integrity" },
    ],
  },
];

// ── Capability tokens ────────────────────────────────────────────────────────

export const TOKEN_CHECKS = [
  { check: "Signature valid (Ed25519, orchestrator key)", fail: "forged → denied",        color: "#E5484D" },
  { check: "agent_id matches the caller",                 fail: "confused deputy → denied", color: "#E5484D" },
  { check: "tool matches the requested tool",             fail: "tool swap → denied",      color: "#E5484D" },
  { check: "scope covers the target claim_id",            fail: "scope widening → denied", color: "#E5484D" },
  { check: "expires_at in the future",                    fail: "replay → denied",         color: "#E5484D" },
];

// ── Data model ───────────────────────────────────────────────────────────────

const dash =  { text: "—",               color: "#E5484D" };
const g2 =    { text: "INSERT",          color: "#3ECF8E" };

export const ACCESS_ROWS = [
  { agent: "Orchestrator",      cells: [ { text: "id only", color: "rgba(255,255,255,0.55)" }, dash, dash, { text: "stage only", color: "rgba(255,255,255,0.55)" }, dash, { text: "decision only", color: "rgba(255,255,255,0.55)" }, { text: "status only", color: "rgba(255,255,255,0.55)" }, g2 ] },
  { agent: "Intake actor",      cells: [ { text: "id+name RLS", color: "rgba(255,255,255,0.7)" }, dash, dash, { text: "INSERT new", color: "#3ECF8E" }, dash, dash, dash, g2 ] },
  { agent: "Identity verifier", cells: [ dash, { text: "fn only", color: "#E2A336" }, dash, dash, dash, dash, dash, g2 ] },
  { agent: "Claims processor",  cells: [ dash, dash, { text: "RLS own", color: "rgba(255,255,255,0.7)" }, { text: "RLS own", color: "rgba(255,255,255,0.7)" }, { text: "RLS sanitised", color: "rgba(255,255,255,0.7)" }, { text: "fn · IFC-stripped", color: "#E2A336" }, dash, g2 ] },
  { agent: "Settlement actor",  cells: [ { text: "id+name+addr RLS", color: "rgba(255,255,255,0.7)" }, { text: "payee ref only", color: "#E2A336" }, dash, { text: "RLS own", color: "rgba(255,255,255,0.7)" }, dash, { text: "decision only", color: "rgba(255,255,255,0.55)" }, { text: "INSERT/UPDATE", color: "#3ECF8E" }, g2 ] },
];

export const LATTICE = [
  { name: "PUBLIC",       color: "rgba(255,255,255,0.4)", sep: "<" },
  { name: "PERSONAL",     color: "#5FA8A0",              sep: "<" },
  { name: "CONFIDENTIAL", color: "#E2A336",              sep: "<" },
  { name: "SECRET",       color: "#E5484D",              sep: "" },
];

// ── Egress steps ─────────────────────────────────────────────────────────────

export const EGRESS_STEPS = [
  { n: "01", name: "SECRET kill-switch",  what: "Any response containing a SECRET-labelled datum is replaced with a generic message immediately.",       why: "short-circuits everything else — nothing downstream can re-leak it" },
  { n: "02", name: "URL allowlist strip", what: "Any URL not on the published allowlist becomes [external link removed].",                               why: "runs before the PII check — URLs can smuggle PII patterns inside themselves" },
  { n: "03", name: "PII regex",           what: "SSN patterns, card formats, phone numbers: any hit blocks the response and writes an audit row.",       why: "after URL strip, so nothing hides inside a link" },
  { n: "04", name: "Length cap",          what: "Text truncated to MAX_OUTPUT_CHARS.",                                                                   why: "last on purpose — truncating earlier would silently discard PII in the tail without detection" },
];

// ── Arch nav links ───────────────────────────────────────────────────────────

export const ARCH_NAV_LINKS = [
  { label: "Topology",    href: "#topology" },
  { label: "Orchestrator", href: "#orchestrator" },
  { label: "Parser",      href: "#parser" },
  { label: "Agents",      href: "#agents" },
  { label: "Ingress",     href: "#ingress" },
  { label: "Capabilities", href: "#tokens" },
  { label: "Data model",  href: "#data" },
  { label: "Egress",      href: "#egress" },
];
