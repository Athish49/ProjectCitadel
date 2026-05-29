import type { PlaygroundTrace } from "@/lib/types/playground";

export function buildExampleTrace(attackId: number, attackName: string): PlaygroundTrace {
  const now = new Date();
  const fmt = (offset: number) =>
    new Date(now.getTime() + offset)
      .toISOString()
      .replace("T", " ")
      .replace(/\.\d+Z$/, "Z");

  return {
    traceId: `ex-${Math.random().toString(36).slice(2, 9)}`,
    attackId,
    attackName,
    submittedAt: fmt(0),
    isExample: true,
    layers: [
      {
        id: "ingress",
        name: "Ingress Sanitisation",
        pattern: "P1",
        status: "blocked",
        durationMs: 12,
        events: [
          {
            ts: fmt(2),
            severity: "neutral",
            label: "RECV",
            message: "raw user input received (182 chars)",
          },
          {
            ts: fmt(8),
            severity: "warn",
            label: "TAINT",
            message: "input wrapped in <untrusted> delimiter; label=UNTRUSTED applied",
          },
          {
            ts: fmt(11),
            severity: "attack",
            label: "DETECT",
            message: 'prompt injection pattern matched: "ignore all previous instructions"',
          },
          {
            ts: fmt(12),
            severity: "alert",
            label: "BLOCK",
            message: "injection attempt quarantined; payload handed to parser LLM only",
          },
        ],
      },
      {
        id: "pattern-detection",
        name: "Pattern Detection",
        pattern: "P3",
        status: "passed",
        durationMs: 5,
        events: [
          {
            ts: fmt(13),
            severity: "neutral",
            label: "SCAN",
            message: "IFC label propagation check: input label=UNTRUSTED",
          },
          {
            ts: fmt(18),
            severity: "ok",
            label: "PASS",
            message: "no cross-label promotion detected; label unchanged",
          },
        ],
      },
      {
        id: "semantic-classifier",
        name: "Semantic Classifier",
        pattern: "P3",
        status: "blocked",
        durationMs: 34,
        events: [
          {
            ts: fmt(19),
            severity: "neutral",
            label: "CLASSIFY",
            message: "running semantic intent classifier on UNTRUSTED payload",
          },
          {
            ts: fmt(48),
            severity: "attack",
            label: "INTENT",
            message: "classified as: PRIVILEGE_ESCALATION (confidence 0.97)",
          },
          {
            ts: fmt(53),
            severity: "alert",
            label: "BLOCK",
            message: "high-confidence adversarial intent; session flagged for audit",
          },
        ],
      },
      {
        id: "untrusted-tagging",
        name: "Untrusted Tagging",
        pattern: "P3",
        status: "passed",
        durationMs: 3,
        events: [
          {
            ts: fmt(54),
            severity: "trust",
            label: "TAG",
            message: "all derived data inherits UNTRUSTED; no label downgrade attempted",
          },
        ],
      },
      {
        id: "parser-llm",
        name: "Parser LLM",
        pattern: "P1",
        status: "blocked",
        durationMs: 280,
        events: [
          {
            ts: fmt(57),
            severity: "neutral",
            label: "SEND",
            message: "payload dispatched to unprivileged parser LLM (Haiku 4.5); no tools issued",
          },
          {
            ts: fmt(280),
            severity: "warn",
            label: "OUTPUT",
            message: 'parser emitted: {"intent":"UNKNOWN","fields":{},"injection_detected":true}',
          },
          {
            ts: fmt(283),
            severity: "alert",
            label: "REJECT",
            message: "schema validation failed: injection_detected=true triggers halt",
          },
        ],
      },
      {
        id: "actor-llm",
        name: "Actor LLM",
        pattern: "P2",
        status: "pending",
        durationMs: null,
        events: [],
      },
      {
        id: "egress-filter",
        name: "Egress Filter",
        pattern: "P10",
        status: "pending",
        durationMs: null,
        events: [],
      },
    ],
    verdict: {
      outcome: "BLOCKED",
      blockedByPattern: "P1",
      blockedByLayer: "Parser LLM",
      summary:
        "The dual-LLM separation (P1) quarantined the injection attempt. The parser LLM detected adversarial intent and emitted injection_detected=true in its JSON schema. The actor LLM never received the raw payload — structural isolation enforced.",
    },
  };
}
