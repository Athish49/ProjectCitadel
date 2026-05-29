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
  submittedAt: string;
  layers: TraceLayer[];
  verdict: TraceVerdict;
  isExample: boolean;
}

export interface AttackTemplate {
  id: string;
  attackId: number;
  attackName: string;
  label: string;
  payload: string;
  tab: AttackComposerTab;
  category: string;
}
