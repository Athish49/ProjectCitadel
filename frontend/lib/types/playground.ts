export type AttackComposerTab =
  | "chat"
  | "pdf"
  | "image"
  | "tool"
  | "cross-customer"
  | "custom";

export type TargetFlow = "intake" | "claims" | "settlement";
export type SessionMode = "live" | "sandboxed";

// "pending" and "running" are client-only states used while a layer_result is
// still in flight. Every other value is authoritative from the backend's
// verdict.layers — see backend/app/showcase/playground_sse.py's _LAYER_STATUSES.
export type TraceLayerStatus =
  | "pending"
  | "running"
  | "passed"
  | "blocked"
  | "held"
  | "skipped"
  | "error"
  | "not_reached";

export interface TraceEvent {
  ts: string;
  severity: "ok" | "warn" | "alert" | "attack" | "trust" | "audit" | "neutral";
  label?: string;
  message: string;
}

export interface TraceLayer {
  id: string;
  name: string;
  // A pipeline-layer tag, e.g. "P2·P4" — not always a single entry from the
  // attack matrix's PatternId catalog, so this is a free-form label.
  pattern: string | null;
  status: TraceLayerStatus;
  durationMs: number | null;
  events: TraceEvent[];
}

export type PlaygroundVerdict = "BLOCKED" | "HELD" | "CLEAN" | "ERROR";

export interface TraceVerdict {
  outcome: PlaygroundVerdict;
  blockedByPattern: string | null;
  blockedByLayer: string | null;
  policyHeld: string | null;
  summary: string;
}

// Fixed vocabulary the backend actor can emit via [POLICY_HELD: <slug>] —
// kept in sync with backend/app/showcase/playground_sse.py's _POLICY_HELD_REASONS.
// humanizePolicyHeld() is the single place both UI surfaces turn a raw slug
// into display text, so the wording can't drift between them.
export function humanizePolicyHeld(reason: string | null | undefined): string {
  switch (reason) {
    case "cannot_approve_own_claim":
      return "Declined — cannot approve or pay out a customer's own claim";
    case "cannot_reveal_fraud_score":
      return "Declined — cannot reveal a fraud or risk score";
    case "cannot_access_other_customer_data":
      return "Declined — cannot access another customer's data";
    case "cannot_disclose_identifiers":
      return "Declined — cannot disclose policy numbers, SSNs, or other identifiers";
    case "out_of_scope_request":
      return "Declined — request is outside the assistant's capabilities";
    default:
      return reason ? `Declined — ${reason.replace(/_/g, " ")}` : "Declined per policy boundary";
  }
}

export interface PlaygroundTrace {
  traceId: string;
  attackId: number;
  attackName: string;
  tab: AttackComposerTab;
  targetFlow: TargetFlow;
  submittedAt: string;
  layers: TraceLayer[];
  verdict: TraceVerdict | null;
  isExample: boolean;
  isReplay: boolean;
}

// Kept in sync with backend/app/showcase/playground_sse.py's LAYER_META — the
// backend's verdict.layers is authoritative, but these are the fallback
// labels/order shown before any event has arrived for a layer.
export const LAYER_DEFINITIONS: { id: string; name: string; pattern: string | null }[] = [
  { id: "ingress",             name: "Ingress Sanitisation", pattern: "P1"    },
  { id: "pattern-detection",   name: "Pattern Detection",    pattern: "P3"    },
  { id: "semantic-classifier", name: "Semantic Classifier",  pattern: "P3"    },
  { id: "untrusted-tagging",   name: "Untrusted Tagging",    pattern: "P3"    },
  { id: "parser-llm",          name: "Parser LLM",           pattern: "P1"    },
  { id: "actor-llm",           name: "Actor + Capabilities", pattern: "P2·P4" },
  { id: "egress-filter",       name: "Egress Filter",        pattern: "P10"   },
];

export interface AttackTemplate {
  id: string;
  attackId: number;
  attackName: string;
  label: string;
  payload: string;
  tab: AttackComposerTab;
  category: string;
}
