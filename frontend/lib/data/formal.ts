/**
 * Static copy + structural data for the /formal page, sourced from the
 * approved Formal.dc.html design file. The only numbers NOT sourced here are
 * the ones the live BFS model checker returns at /api/formal/run-check
 * (visited, violations, stages_seen, elapsed_ms, all_hold, invariant_results)
 * — those are rendered from the real response, not from this file.
 */

/** The 7 invariant names, in the exact order / casing the backend uses as
 *  keys of `invariant_results`. */
export const INVARIANT_NAMES = [
  "TypeOK",
  "ClosedIsAbsorbing",
  "ForwardProgress",
  "EventualClosure",
  "MonotonicFlags",
  "FraudDecisionFinal",
  "SettlementAmountFinal",
] as const;

export type InvariantName = (typeof INVARIANT_NAMES)[number];

export interface HeroStat {
  n: string;
  label: string;
  color?: string;
  /** When set, the page overrides `n`/`color` with a value derived from the
   *  live /api/formal/run-check response once it has loaded. */
  live?: "visited" | "invariants";
}

export const HERO_STATS: HeroStat[] = [
  { n: "9", label: "workflow stages" },
  { n: "11", label: "legal transitions" },
  { n: "918", label: "reachable states, all visited", live: "visited" },
  { n: "3,580", label: "state changes checked" },
  { n: "7 / 7", label: "invariants hold", color: "#3ECF8E", live: "invariants" },
  { n: "138 / 138", label: "spec tests passing", color: "#3ECF8E" },
];

/** 9 workflow stages, in rank order (matches backend RANK / STAGES). */
export const STATES = [
  "INTAKE", "IDENTITY_PENDING", "IDENTITY_VERIFIED", "PROCESSING",
  "DECIDED", "SETTLED", "ESCALATED", "DENIED", "CLOSED",
] as const;

export const STATES_SHORT = ["INT", "ID_P", "ID_V", "PROC", "DEC", "SET", "ESC", "DEN", "CLO"];

/** Absolute layout position (px, within a 1152×432 canvas) of each state's
 *  node in the rank diagram — ranks run left to right, co-terminal states
 *  (SETTLED/ESCALATED/DENIED) share a column. Mirrors Formal.dc.html. */
export const NODE_POS: { x: number; y: number }[] = [
  { x: 0, y: 222 },    // INTAKE
  { x: 170, y: 222 },  // IDENTITY_PENDING
  { x: 340, y: 222 },  // IDENTITY_VERIFIED
  { x: 510, y: 222 },  // PROCESSING
  { x: 680, y: 222 },  // DECIDED
  { x: 850, y: 222 },  // SETTLED
  { x: 850, y: 102 },  // ESCALATED
  { x: 850, y: 342 },  // DENIED
  { x: 1020, y: 222 }, // CLOSED
];

/** 11 legal transitions — [fromIdx, toIdx, plain-language guard]. Edge
 *  number = array index + 1 (matches the design's `_VALID_EDGES` numbering). */
export const EDGES: [number, number, string][] = [
  [0, 1, "Intake is complete"],
  [1, 2, "Identity check has passed"],
  [2, 3, "No data guard. The orchestrator starts processing"],
  [2, 6, "A complaint is on file"],
  [3, 4, "Damage assessed, coverage calculated and fraud scored"],
  [4, 5, "Fraud is clear and the amount is within the $10,000 auto-approval limit"],
  [4, 6, "Fraud is flagged or denied, or the amount is over the limit"],
  [4, 7, "Administrative override. No data guard"],
  [5, 8, "Always allowed. Closes the claim"],
  [6, 8, "Always allowed. Closes the claim"],
  [7, 8, "Always allowed. Closes the claim"],
];

/** Example claim paths through the state machine, as sequences of STATES
 *  indices, for the "Trace a claim" demo. */
export const TRACE_PATHS: { name: string; seq: number[] }[] = [
  { name: "Settled automatically", seq: [0, 1, 2, 3, 4, 5, 8] },
  { name: "Escalated to a human", seq: [0, 1, 2, 3, 4, 6, 8] },
  { name: "Complaint", seq: [0, 1, 2, 6, 8] },
  { name: "Denied", seq: [0, 1, 2, 3, 4, 7, 8] },
];

export const METHOD_NODES = [
  { title: "Orchestrator code", sub: "11 transitions, each behind a guard" },
  { title: "TLA+ specification", sub: "The same machine, as mathematics" },
  { title: "Model checker", sub: "Visits every reachable state" },
  { title: "7 of 7 invariants hold", sub: "in all 918 states", accent: true },
];
export const METHOD_ARROW_LABELS = ["modelled as", "explored by", "proves"];
export const METHOD_LOOP_CAPTION = "conformance tests replay all 81 stage pairs";

export interface InvariantCopy {
  name: InvariantName;
  kind: "SAFETY" | "LIVENESS";
  plain: string;
  allowed: string;
  never: string;
  standards: string[];
}

export const INVARIANTS: InvariantCopy[] = [
  {
    name: "TypeOK", kind: "SAFETY",
    plain: "Every variable stays inside its declared set of values.",
    allowed: "stage = DECIDED", never: "stage = anything else",
    standards: ["NIST SI-10", "ASVS V5.1"],
  },
  {
    name: "ClosedIsAbsorbing", kind: "SAFETY",
    plain: "A closed claim can never be reopened.",
    allowed: "CLOSED → CLOSED", never: "CLOSED → PROCESSING",
    standards: ["NIST AU-9", "CC FPT_RIP"],
  },
  {
    name: "ForwardProgress", kind: "SAFETY",
    plain: "Every move increases rank. No loops, no going back.",
    allowed: "PROCESSING → DECIDED", never: "DECIDED → PROCESSING",
    standards: ["NIST AC-3", "NIST CM-7", "CC FDP_ACF.1"],
  },
  {
    name: "EventualClosure", kind: "LIVENESS",
    plain: "Every claim can always reach CLOSED. Nothing gets stuck.",
    allowed: "any state ⇝ CLOSED", never: "a dead-end state",
    standards: ["NIST CP-10", "ISO 27001 A.17.2"],
  },
  {
    name: "MonotonicFlags", kind: "SAFETY",
    plain: "A completed step cannot be reset and replayed.",
    allowed: "identity_verified: false → true", never: "identity_verified: true → false",
    standards: ["NIST SI-7", "ASVS V5.1"],
  },
  {
    name: "FraudDecisionFinal", kind: "SAFETY",
    plain: "A fraud decision is written once. It cannot be laundered.",
    allowed: "NONE → FLAG", never: "FLAG → CLEAR",
    standards: ["NIST AU-9", "NIST SI-7", "PCI-DSS Req. 6"],
  },
  {
    name: "SettlementAmountFinal", kind: "SAFETY",
    plain: "A proposed amount cannot change mid-flight.",
    allowed: "unset → 10,000", never: "10,000 → 15,000",
    standards: ["NIST SI-7", "PCI-DSS Req. 6"],
  },
];

export const SCOPE_PROVEN = [
  "No claim can skip, repeat or reverse a stage",
  "A payout needs a clear fraud decision and an amount within the limit",
  "Decisions, amounts and completed steps are write-once",
  "Every claim can always be closed",
];

export const SCOPE_OUTSIDE = [
  "What an LLM writes. Runtime layers handle that",
  "Classifier and sanitiser accuracy",
  "Amounts beyond the three modelled values: unset, at the limit, over it",
  "FAQ, inquiry and complaint flows, which hold no state",
];

/** 9×9 reachability matrix for the heatmap — rows = from, cols = to. */
const edgeSet = new Set(EDGES.map(([from, to]) => `${from}-${to}`));

export const MATRIX_ROWS = STATES.map((_, from) => ({
  from,
  cells: STATES.map((_, to) => ({
    to,
    valid: edgeSet.has(`${from}-${to}`),
  })),
}));

export const CONFORMANCE_STATS = [
  { n: "11 / 11", label: "legal transitions accepted" },
  { n: "70 / 70", label: "illegal jumps refused" },
  { n: "102 / 102", label: "conformance tests passing" },
  { n: "36 / 36", label: "invariant unit tests passing" },
];
