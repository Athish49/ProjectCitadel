export type AdversarialVerdict =
  | "BLOCKED_INGRESS"
  | "EVADED_INGRESS"
  | "API_ERROR";

export interface AdversarialAttempt {
  trace_id: string;
  session_id: string;
  attack_id: number;
  verdict: AdversarialVerdict;
  sanitizer_detections: string[];
  chars_stripped: number;
  is_breach: boolean;
  breach_count: number;
  last_breach_at: string | null;
  timestamp: string;
}

export interface BreachCountEvent {
  breach_count: number;
  last_breach_at: string | null;
}
