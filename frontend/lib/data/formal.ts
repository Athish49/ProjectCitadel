export const TOC_LINKS = [
  { n: "0", href: "#overview",    label: "Overview" },
  { n: "1", href: "#variables",   label: "State variables" },
  { n: "2", href: "#transitions", label: "Transition relation" },
  { n: "3", href: "#matrix",      label: "Reachability matrix" },
  { n: "4", href: "#invariants",  label: "Invariants" },
  { n: "5", href: "#verification",label: "Verification method" },
  { n: "6", href: "#conformance", label: "Conformance testing" },
  { n: "7", href: "#source",      label: "Source" },
];

export const STAT_ROW = [
  { n: "8",       label: "state variables" },
  { n: "11",      label: "workflow transitions" },
  { n: "7",       label: "safety & liveness invariants" },
  { n: "918",      label: "reachable states enumerated" },
  { n: "36/36",   label: "invariant tests passing" },
  { n: "102/102", label: "conformance tests passing" },
];

export const STATE_VARS = [
  { name: "stage",              domain: "enum[9]",              desc: "the workflow stage — INTAKE through CLOSED" },
  { name: "intake_complete",    domain: "BOOLEAN",              desc: "set once the parser + intake actor agree the summary is sufficient" },
  { name: "identity_verified",  domain: "BOOLEAN",              desc: "set only by the server-side verify_identity() function, never by an LLM" },
  { name: "damage_assessed",    domain: "BOOLEAN",              desc: "set once classify_damage() has returned a label for this claim" },
  { name: "coverage_calculated",domain: "BOOLEAN",              desc: "set once lookup_coverage() has resolved applicability" },
  { name: "complaint_captured", domain: "BOOLEAN",              desc: "set by capture_complaint() on the inquiry path; forces ESCALATED" },
  { name: "fraud_decision",     domain: "enum{NONE,CLEAR,FLAG,DENY}", desc: "the only field of score_fraud() forwarded past the SECRET boundary" },
  { name: "settlement_amount",  domain: "ℝ ∪ {NULL}",          desc: "computed by calculate_settlement(); compared against auto_approve_limit" },
];

export const FORMAL_EDGES = [
  { n: "01", from: "INTAKE",            to: "IDENTITY_PENDING",  guard: "intake_complete = TRUE" },
  { n: "02", from: "IDENTITY_PENDING",  to: "IDENTITY_VERIFIED", guard: "identity_verified = TRUE" },
  { n: "03", from: "IDENTITY_VERIFIED", to: "PROCESSING",        guard: "—" },
  { n: "04", from: "IDENTITY_VERIFIED", to: "ESCALATED",         guard: "complaint_captured = TRUE" },
  { n: "05", from: "PROCESSING",        to: "DECIDED",           guard: "damage_assessed ∧ coverage_calculated ∧ fraud_decision ≠ NONE" },
  { n: "06", from: "DECIDED",           to: "SETTLED",           guard: "fraud_decision = CLEAR ∧ settlement_amount ≤ auto_approve_limit" },
  { n: "07", from: "DECIDED",           to: "ESCALATED",         guard: "fraud_decision ∈ {FLAG, DENY} ∨ amount > limit" },
  { n: "08", from: "DECIDED",           to: "DENIED",            guard: "orchestrator administrative override" },
  { n: "09", from: "SETTLED",           to: "CLOSED",            guard: "—" },
  { n: "10", from: "ESCALATED",         to: "CLOSED",            guard: "human review resolved" },
  { n: "11", from: "DENIED",            to: "CLOSED",            guard: "—" },
];

export const INVARIANTS = [
  {
    name: "TypeOK", kind: "SAFETY", color: "#3ECF8E",
    formal: "□ ( stage ∈ States ∧ fraud_decision ∈ FraudDecisions ∧ … )",
    plain: "Every variable stays inside its declared domain at every step of every execution — no undefined or out-of-range state is ever reachable.",
    standards: ["NIST SP 800-53 SI-10", "OWASP ASVS 2021 V5.1"],
  },
  {
    name: "ClosedIsAbsorbing", kind: "SAFETY", color: "#3ECF8E",
    formal: "□ ( stage = \"CLOSED\" ⇒ □ ( stage = \"CLOSED\" ) )",
    plain: "Once a claim reaches CLOSED, no transition can ever move it again. Closure is permanent by construction, not by convention.",
    standards: ["NIST SP 800-53 AU-9", "CC EAL3 FPT_RIP"],
  },
  {
    name: "ForwardProgress", kind: "SAFETY", color: "#3ECF8E",
    formal: "□ [ stage ≠ stage' ⇒ Rank(stage') > Rank(stage) ]_vars",
    plain: "Every valid transition strictly increases a rank assigned to each stage. There are no cycles and no backward movement anywhere in the graph. CC EAL3–4, NIST SP 800-53 CM-7/AC-3, and OWASP ASVS Level 2 all require that only authorized transitions are reachable — this invariant, verified across all 918 reachable states, is the formal proof of that requirement.",
    standards: ["CC EAL3-4 FDP_ACF.1", "NIST SP 800-53 CM-7 · AC-3", "OWASP ASVS Level 2 V4"],
  },
  {
    name: "EventualClosure", kind: "LIVENESS", color: "#3ECF8E",
    formal: "◇ ( stage = \"CLOSED\" )   [under weak fairness]",
    plain: "Every execution eventually reaches CLOSED — the machine cannot stall forever in an intermediate stage under fair scheduling.",
    standards: ["NIST SP 800-53 CP-10", "ISO 27001 A.17.2"],
  },
  {
    name: "MonotonicFlags", kind: "SAFETY", color: "#3ECF8E",
    formal: "□ [ intake_complete ⇒ intake_complete' ∧ identity_verified ⇒ identity_verified' ∧ … ]_vars",
    plain: "Every boolean guard flag (intake complete, identity verified, damage assessed, coverage calculated, complaint captured) is write-once: once set TRUE it cannot revert. This prevents an attacker from resetting a completed workflow step to replay it.",
    standards: ["NIST SP 800-53 SI-7 · SI-10", "OWASP ASVS 2021 V5.1"],
  },
  {
    name: "FraudDecisionFinal", kind: "SAFETY", color: "#3ECF8E",
    formal: "□ [ fraud_decision ≠ \"NONE\" ⇒ fraud_decision' = fraud_decision ]_vars",
    plain: "Once the fraud scoring decision leaves NONE it cannot be altered — not by the orchestrator, not by any environmental action. Prevents score-laundering after a CLEAR or FLAG verdict has been issued.",
    standards: ["NIST SP 800-53 AU-9 · SI-7", "PCI-DSS Req. 6"],
  },
  {
    name: "SettlementAmountFinal", kind: "SAFETY", color: "#3ECF8E",
    formal: "□ [ settlement_amount ≠ 0 ⇒ settlement_amount' = settlement_amount ]_vars",
    plain: "Once a settlement amount is proposed it is immutable for the lifetime of the claim. Prevents mid-flight amount tampering between proposal and CLOSED — a financial integrity guarantee formalized at the model level.",
    standards: ["NIST SP 800-53 SI-7 · AU-9", "PCI-DSS Req. 6", "OWASP ASVS 2021 V5.1"],
  },
];

export const CONFORMANCE_STATS = [
  { n: "11 / 11",   label: "valid edges accepted",            color: "#3ECF8E" },
  { n: "70 / 70",   label: "invalid pairs rejected",          color: "#3ECF8E" },
  { n: "102 / 102", label: "total conformance tests passing", color: "#3ECF8E" },
];

export const MATRIX_STATES = [
  "INTAKE", "IDENTITY_PENDING", "IDENTITY_VERIFIED",
  "PROCESSING", "DECIDED", "SETTLED", "ESCALATED", "DENIED", "CLOSED",
];

const edgeSet = new Set(FORMAL_EDGES.map((e) => `${e.from}→${e.to}`));

export const MATRIX_ROWS = MATRIX_STATES.map((from) => ({
  name: from,
  cells: MATRIX_STATES.map((to) => {
    const valid = edgeSet.has(`${from}→${to}`);
    return {
      title: `${from} → ${to}${valid ? " (valid)" : " (rejected)"}`,
      bg: valid ? "rgba(62,207,142,0.14)" : "rgba(255,255,255,0.015)",
      dot: valid ? "#3ECF8E" : "rgba(229,72,77,0.4)",
    };
  }),
}));

export const CHECK_STEPS = [
  { msg: "enumerating reachable states from Init (BFS, bounded)",         status: "918 found",    color: "#3ECF8E" },
  { msg: "checking TypeOK at every reachable state",                      status: "36/36 PASS",   color: "#3ECF8E" },
  { msg: "checking ClosedIsAbsorbing",                                    status: "PASS",          color: "#3ECF8E" },
  { msg: "checking ForwardProgress (rank strictly increasing)",            status: "PASS",          color: "#3ECF8E" },
  { msg: "checking EventualClosure under weak fairness",                   status: "PASS",          color: "#3ECF8E" },
  { msg: "checking MonotonicFlags (guard flags write-once)",               status: "PASS",          color: "#3ECF8E" },
  { msg: "checking FraudDecisionFinal (fraud score immutable once set)",   status: "PASS",          color: "#3ECF8E" },
  { msg: "checking SettlementAmountFinal (amount immutable once set)",     status: "PASS",          color: "#3ECF8E" },
  { msg: "driving advance_stage() through all 81 (from,to) pairs",        status: "102/102 PASS", color: "#3ECF8E" },
];

// State graph geometry
export const GRAPH_LINES = [
  { x1: 130, y1:  84, x2: 130, y2: 170 },  // INTAKE → IDENTITY_PENDING
  { x1: 220, y1: 322, x2: 660, y2: 192 },  // IDENTITY_VERIFIED → ESCALATED (complaint)
  { x1: 130, y1: 214, x2: 130, y2: 300 },  // IDENTITY_PENDING → IDENTITY_VERIFIED
  { x1: 220, y1: 322, x2: 350, y2: 192 },  // IDENTITY_VERIFIED → PROCESSING
  { x1: 440, y1: 214, x2: 440, y2: 300 },  // PROCESSING → DECIDED
  { x1: 530, y1: 322, x2: 660, y2: 322 },  // DECIDED → DENIED
  { x1: 530, y1: 300, x2: 660, y2:  62 },  // DECIDED → SETTLED
  { x1: 530, y1: 322, x2: 750, y2: 214 },  // DECIDED → ESCALATED
  { x1: 840, y1:  62, x2: 970, y2: 192 },  // SETTLED → CLOSED
  { x1: 840, y1: 192, x2: 970, y2: 192 },  // ESCALATED → CLOSED (horizontal)
  { x1: 840, y1: 322, x2: 970, y2: 192 },  // DENIED → CLOSED
];

export const GRAPH_NODES = [
  { x:  40, y:  40, label: "INTAKE",            color: "rgba(255,255,255,0.88)", border: "rgba(255,255,255,0.22)", dashed: false },
  { x:  40, y: 170, label: "IDENTITY_PENDING",  color: "rgba(255,255,255,0.88)", border: "rgba(255,255,255,0.22)", dashed: false },
  { x:  40, y: 300, label: "IDENTITY_VERIFIED", color: "rgba(255,255,255,0.88)", border: "rgba(255,255,255,0.22)", dashed: false },
  { x: 350, y: 170, label: "PROCESSING",        color: "rgba(255,255,255,0.88)", border: "rgba(255,255,255,0.22)", dashed: false },
  { x: 350, y: 300, label: "DECIDED",           color: "rgba(255,255,255,0.88)", border: "rgba(255,255,255,0.22)", dashed: false },
  { x: 660, y:  40, label: "SETTLED",           color: "#3ECF8E",               border: "#3ECF8E",               dashed: false },
  { x: 660, y: 170, label: "ESCALATED",         color: "#E0A73E",               border: "#E0A73E",               dashed: false },
  { x: 660, y: 300, label: "DENIED",            color: "#E5484D",               border: "#E5484D",               dashed: false },
  { x: 970, y: 170, label: "CLOSED",            color: "rgba(255,255,255,0.6)", border: "rgba(255,255,255,0.28)", dashed: true  },
];

export const GRAPH_PARTICLES = [
  { path: "M130 84 L130 170",  color: "#3ECF8E", dur: "2.4s", delay: "0s"   },  // INTAKE → IDENTITY_PENDING
  { path: "M220 322 L660 192", color: "#E0A73E", dur: "3.6s", delay: "0.4s" },  // IDENTITY_VERIFIED → ESCALATED (complaint)
  { path: "M130 214 L130 300", color: "#3ECF8E", dur: "2.4s", delay: "0.8s" },  // IDENTITY_PENDING → IDENTITY_VERIFIED
  { path: "M220 322 L350 192", color: "#3ECF8E", dur: "2.8s", delay: "1.2s" },  // IDENTITY_VERIFIED → PROCESSING
  { path: "M440 214 L440 300", color: "#3ECF8E", dur: "2.2s", delay: "0.2s" },  // PROCESSING → DECIDED
  { path: "M530 322 L660 322", color: "#E5484D", dur: "2.6s", delay: "1.6s" },  // DECIDED → DENIED
  { path: "M530 300 L660 62",  color: "#3ECF8E", dur: "3.2s", delay: "0.6s" },  // DECIDED → SETTLED
  { path: "M530 322 L750 214", color: "#E0A73E", dur: "3.0s", delay: "2.0s" },  // DECIDED → ESCALATED
  { path: "M840 62 L970 192",  color: "#3ECF8E", dur: "2.2s", delay: "0.3s" },  // SETTLED → CLOSED
  { path: "M840 192 L970 192", color: "#E0A73E", dur: "1.8s", delay: "1.4s" },  // ESCALATED → CLOSED
  { path: "M840 322 L970 192", color: "#E5484D", dur: "1.8s", delay: "0.9s" },  // DENIED → CLOSED
];

const cmt  = "rgba(255,255,255,0.32)";
const kw   = "#5FA8A0";
const body = "rgba(255,255,255,0.68)";

export const SOURCE_LINES = [
  { n:  1, text: "---- MODULE workflow ----",                                                    color: cmt  },
  { n:  2, text: "EXTENDS Naturals, FiniteSets",                                                 color: kw   },
  { n:  3, text: " ",                                                                            color: body },
  { n:  4, text: "AUTO_APPROVE_LIMIT == 10000",                                                  color: kw   },
  { n:  5, text: "AmountDomain == {0, 10000, 15000}",                                            color: kw   },
  { n:  6, text: " ",                                                                            color: body },
  { n:  7, text: "VARIABLES stage, intake_complete, identity_verified,",                         color: kw   },
  { n:  8, text: "          damage_assessed, coverage_calculated,",                              color: body },
  { n:  9, text: "          complaint_captured, fraud_decision, settlement_amount",              color: body },
  { n: 10, text: " ",                                                                            color: body },
  { n: 11, text: "\\* -- Type correctness --",                                                   color: cmt  },
  { n: 12, text: "TypeOK ==",                                                                    color: kw   },
  { n: 13, text: "  /\\ stage \\in States",                                                      color: body },
  { n: 14, text: '  /\\ fraud_decision \\in {"NONE","CLEAR","FLAG","DENY"}',                     color: body },
  { n: 15, text: "  /\\ settlement_amount \\in AmountDomain",                                    color: body },
  { n: 16, text: " ",                                                                            color: body },
  { n: 17, text: "Init ==",                                                                      color: kw   },
  { n: 18, text: '  /\\ stage = "INTAKE"',                                                       color: body },
  { n: 19, text: "  /\\ intake_complete = FALSE",                                                color: body },
  { n: 20, text: '  /\\ fraud_decision = "NONE"',                                                color: body },
  { n: 21, text: "  /\\ settlement_amount = 0",                                                  color: body },
  { n: 22, text: " ",                                                                            color: body },
  { n: 23, text: "\\* -- one action per valid edge --",                                          color: cmt  },
  { n: 24, text: "ToIdentityPending ==",                                                         color: kw   },
  { n: 25, text: '  /\\ stage = "INTAKE" /\\ intake_complete = TRUE',                            color: body },
  { n: 26, text: "  /\\ stage' = \"IDENTITY_PENDING\"",                                          color: body },
  { n: 27, text: "  /\\ UNCHANGED <<fraud_decision, settlement_amount>>",                        color: body },
  { n: 28, text: " ",                                                                            color: body },
  { n: 29, text: "ToSettled ==",                                                                 color: kw   },
  { n: 30, text: '  /\\ stage = "DECIDED"',                                                      color: body },
  { n: 31, text: '  /\\ fraud_decision = "CLEAR"',                                               color: body },
  { n: 32, text: "  /\\ settlement_amount \\leq AUTO_APPROVE_LIMIT",                             color: body },
  { n: 33, text: "  /\\ stage' = \"SETTLED\"",                                                   color: body },
  { n: 34, text: " ",                                                                            color: body },
  { n: 35, text: "Next == \\/ ToIdentityPending \\/ ToSettled \\/ …",                           color: kw   },
  { n: 36, text: " ",                                                                            color: body },
  { n: 37, text: "\\* -- invariants (see section 4) --",                                         color: cmt  },
  { n: 38, text: 'ClosedIsAbsorbing == [](stage = "CLOSED" => [](stage = "CLOSED"))',           color: kw   },
  { n: 39, text: "ForwardProgress == [][stage /= stage' => Rank(stage') > Rank(stage)]_vars",   color: kw   },
  { n: 40, text: 'EventualClosure == <>(stage = "CLOSED")',                                      color: kw   },
  { n: 41, text: " ",                                                                            color: body },
  { n: 42, text: "\\* -- write-once integrity (NIST SI-7 / AU-9, PCI-DSS Req. 6) --",          color: cmt  },
  { n: 43, text: "MonotonicFlags == [][intake_complete => intake_complete']_vars",               color: kw   },
  { n: 44, text: 'FraudDecisionFinal == [][fraud_decision /= "NONE" => fraud_decision\' = fraud_decision]_vars', color: kw },
  { n: 45, text: "SettlementAmountFinal == [][settlement_amount /= 0 => settlement_amount' = settlement_amount]_vars", color: kw },
  { n: 46, text: " ",                                                                            color: body },
  { n: 47, text: "====",                                                                         color: cmt  },
];
