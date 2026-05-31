export type TrustLabel = "public" | "personal" | "confidential" | "secret" | "untrusted";
export type MatrixClass = "LIVE" | "ARCHITECTURAL" | "OUT-OF-SCOPE";
export type MatrixStatus = "ok" | "warn" | "alert" | "na";
export type AttackCategory =
  | "Prompt/Input"
  | "Goal Hijack"
  | "Memory"
  | "Exfiltration"
  | "Tool"
  | "Identity"
  | "Multi-Agent"
  | "Supply Chain"
  | "Training"
  | "Cascading"
  | "Trust"
  | "Infra"
  | "Weapon"
  | "Privacy";
export type PatternId = "P1" | "P2" | "P3" | "P4" | "P5" | "P6" | "P7" | "P8" | "P9" | "P10" | "P11" | "P12";
export type AttackOutcome = "blocked" | "partial" | "successful";
export type AgentId = "orchestrator" | "intake_parser" | "claims_processor" | "settlement_actor" | "adversarial_agent";
export type NodeType = "agent" | "parser" | "orchestrator" | "datastore" | "filter" | "external";
export type NodeStatus = "healthy" | "degraded" | "offline" | "unknown";
export type EdgeTransport = "envelope" | "tool_call" | "sse" | "rest" | "rls_query" | "direct";

export interface CodeRef {
  label: string;
  path: string;
  lineStart?: number | null;
  lineEnd?: number | null;
}

export interface MatrixRow {
  attackId: number;
  name: string;
  category: AttackCategory;
  class: MatrixClass;
  patterns: PatternId[];
  variantCount: number | null;
  blockedCount: number;
  partialCount: number;
  successfulCount: number;
  falsePositiveCount: number;
  lastTestedAt: string | null;
}

export interface MatrixResponse {
  rows: MatrixRow[];
  generatedAt: string;
}

export interface AttemptSummary {
  traceId: string;
  outcome: AttackOutcome;
  blockedByPattern: PatternId | null;
  ts: string;
}

export interface AttackDetail {
  attackId: number;
  name: string;
  description: string;
  class: MatrixClass;
  patterns: PatternId[];
  codeRefs: CodeRef[];
  recentAttempts: AttemptSummary[];
}

export interface Pattern {
  id: PatternId;
  name: string;
  summary: string;
  description: string;
  attackIds: number[];
  implemented: boolean;
  codeRefs: CodeRef[];
  testCount: number;
}

export interface PatternsResponse {
  patterns: Pattern[];
  generatedAt: string;
}

export interface ArchNode {
  id: string;
  label: string;
  type: NodeType;
  status: NodeStatus;
  patterns: PatternId[];
}

export interface ArchEdge {
  id: string;
  source: string;
  target: string;
  label: string | null;
  transport: EdgeTransport | null;
  dataLabel: TrustLabel | null;
}

export interface NodeSpec {
  id: string;
  role: string;
  model: string | null;
  tools: string[];
  labelAccess: TrustLabel[];
  description: string;
  patterns: PatternId[];
}

export interface ArchitectureResponse {
  nodes: ArchNode[];
  edges: ArchEdge[];
  snapshotAt: string;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
}

export interface CITestSuite {
  total: number;
  passed: number;
  failed: number;
  duration_seconds: number;
}

export interface CIAttackCoverage {
  tests: number;
  passed: number;
  failed: number;
}

export interface CIResults {
  timestamp: string;
  commit: string;
  commit_short: string;
  branch: string;
  run_url: string;
  unit: CITestSuite;
  integration: CITestSuite | null;
  attack_coverage: Record<string, CIAttackCoverage>;
}
