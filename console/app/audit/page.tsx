import type { Metadata } from "next";
import { AuditFeed } from "@/components/audit/audit-feed";

export const metadata: Metadata = {
  title: "Live Audit Feed — SecureClaim AI",
  description:
    "Real-time stream of audit events from the agent system — tool calls, capability decisions, sanitisation hits, and security events.",
};
import type { AuditAgent, AuditSeverity } from "@/lib/types/audit";

const VALID_AGENTS: AuditAgent[] = [
  "ingress","parser","orchestrator","intake_actor","identity_verifier",
  "claims_processor","settlement_actor","tool_registry","data_layer",
  "egress_filter","adversarial_agent",
];

const VALID_SEVERITIES: AuditSeverity[] = ["ok","info","warn","alert"];

interface PageProps {
  searchParams: Promise<{ agent?: string; severity?: string; trace?: string }>;
}

export default async function AuditPage({ searchParams }: PageProps) {
  const { agent, severity, trace } = await searchParams;

  const initialAgent    = VALID_AGENTS.includes(agent as AuditAgent)           ? (agent as AuditAgent)       : null;
  const initialSeverity = VALID_SEVERITIES.includes(severity as AuditSeverity) ? (severity as AuditSeverity) : null;
  const initialTrace    = trace ? decodeURIComponent(trace) : null;

  return (
    <AuditFeed
      initialAgent={initialAgent}
      initialSeverity={initialSeverity}
      initialTrace={initialTrace}
    />
  );
}
