export type AdversarialVerdict =
  | "BLOCKED_INGRESS"
  | "EVADED_INGRESS"
  | "API_ERROR";

export type AgentStatusValue = "LIVE" | "OFFLINE" | "CONNECTING";

export interface AdversarialAttempt {
  trace_id: string;
  session_id: string;
  attack_id: number;
  verdict: AdversarialVerdict;
  sanitizer_detections: string[];
  chars_stripped: number;
  is_breach: boolean;
  pipeline_verdict?: string | null;
  blocked_by_layer?: string | null;
  timestamp: string;
}

export interface BreachStatsEvent {
  total_attempts: number;
  breach_count: number;
  last_breach_at: string | null;
}

export interface AgentStatusEvent {
  status: AgentStatusValue;
  last_seen_at: string | null;
}
