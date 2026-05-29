import type { PatternId } from "@/lib/types/showcase";

export type AttackComposerTab =
  | "chat"
  | "pdf"
  | "image"
  | "tool"
  | "cross-customer"
  | "custom";

export type TargetFlow = "intake" | "claims" | "settlement";
export type SessionMode = "live" | "sandboxed";

export type TraceLayerStatus = "pending" | "running" | "blocked" | "partial" | "passed";

export interface TraceEvent {
  ts: string;
  severity: "ok" | "warn" | "alert" | "attack" | "trust" | "audit" | "neutral";
  label?: string;
  message: string;
}

export interface TraceLayer {
  id: string;
  name: string;
  pattern: PatternId | null;
  status: TraceLayerStatus;
  durationMs: number | null;
  events: TraceEvent[];
}

export type PlaygroundVerdict = "BLOCKED" | "PARTIAL" | "BREACH" | "CLEAN";

export interface TraceVerdict {
  outcome: PlaygroundVerdict;
  blockedByPattern: PatternId | null;
  blockedByLayer: string | null;
  summary: string;
}

export interface PlaygroundTrace {
  traceId: string;
  attackId: number;
  attackName: string;
  tab: AttackComposerTab;
  submittedAt: string;
  layers: TraceLayer[];
  verdict: TraceVerdict | null;
  isExample: boolean;
  isReplay: boolean;
}

export const LAYER_DEFINITIONS: { id: string; name: string; pattern: PatternId | null }[] = [
  { id: "ingress",             name: "Ingress Sanitisation", pattern: "P1"  },
  { id: "pattern-detection",   name: "Pattern Detection",    pattern: "P3"  },
  { id: "semantic-classifier", name: "Semantic Classifier",  pattern: "P3"  },
  { id: "untrusted-tagging",   name: "Untrusted Tagging",    pattern: "P3"  },
  { id: "parser-llm",          name: "Parser LLM",           pattern: "P1"  },
  { id: "actor-llm",           name: "Actor LLM",            pattern: "P2"  },
  { id: "egress-filter",       name: "Egress Filter",        pattern: "P10" },
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
