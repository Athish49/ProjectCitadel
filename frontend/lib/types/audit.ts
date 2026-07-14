export type AuditAgent =
  | "ingress"
  | "parser"
  | "orchestrator"
  | "intake_actor"
  | "identity_verifier"
  | "claims_processor"
  | "settlement_actor"
  | "tool_registry"
  | "data_layer"
  | "egress_filter"
  | "adversarial_agent";

export type AuditSeverity = "ok" | "info" | "warn" | "alert";

export interface AuditRow {
  id: string;
  ts: string;
  traceId: string;
  agent: AuditAgent;
  action: string;
  label: string | null;
  severity: AuditSeverity;
  outcome: string;
  detail: Record<string, string | number | boolean | null>;
}
