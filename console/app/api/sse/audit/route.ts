import type { AuditRow, AuditAgent, AuditSeverity } from "@/lib/types/audit";

// ── Helpers ───────────────────────────────────────────────────────────────────

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

function rand(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

let _seq = 0;
function uid(): string {
  return `a${Date.now().toString(36)}${(++_seq).toString(36)}`;
}

// Stable pool of trace IDs so multiple events share the same trace.
const TRACE_POOL = Array.from({ length: 10 }, (_, i) =>
  ((i + 1) * 0x1f3a8b2c + 0xdeadbeef)
    .toString(16)
    .padStart(8, "0")
    .slice(0, 8)
);

// ── Event template definitions ────────────────────────────────────────────────

interface Template {
  agent: AuditAgent;
  action: string;
  label: string | null;
  severity: AuditSeverity;
  outcome: string;
  detail: (traceId: string) => Record<string, string | number | boolean | null>;
  weight: number;
}

const CLAIM_IDS  = ["CLM-8841", "CLM-7723", "CLM-6012", "CLM-9034", "CLM-5501"];
const POLICY_IDS = ["POL-2291", "POL-3370", "POL-1188", "POL-4412"];
const CLT_IDS    = ["CLT-0042", "CLT-1193", "CLT-2284", "CLT-0871"];

const TEMPLATES: Template[] = [
  // ── Normal pipeline – ingress ───────────────────────────────────────────────
  {
    agent: "ingress", action: "recv", label: "UNTRUSTED", severity: "ok", outcome: "ok", weight: 8,
    detail: () => ({ chars: rand(80, 350), source: "api_gateway" }),
  },
  {
    agent: "ingress", action: "taint_applied", label: "UNTRUSTED", severity: "info", outcome: "ok", weight: 8,
    detail: () => ({ labels: 2, delimiter: "<untrusted>" }),
  },
  {
    agent: "ingress", action: "unicode_normalised", label: "UNTRUSTED", severity: "info", outcome: "ok", weight: 4,
    detail: () => ({ zwsp_stripped: rand(0, 3), nfkc: true }),
  },

  // ── Normal pipeline – parser ────────────────────────────────────────────────
  {
    agent: "parser", action: "schema_validated", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 8,
    detail: () => ({ schema: "ClaimIntent", model: "claude-haiku-4-5", injection_detected: false }),
  },

  // ── Normal pipeline – orchestrator ─────────────────────────────────────────
  {
    agent: "orchestrator", action: "state_transition", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 7,
    detail: () => ({ from: pick(["INTAKE","IDENTITY","PROCESSING"]), to: pick(["IDENTITY","PROCESSING","SETTLEMENT"]) }),
  },
  {
    agent: "orchestrator", action: "envelope_signed", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 5,
    detail: () => ({ algo: "Ed25519", recipient: pick(["intake_actor","identity_verifier","claims_processor"]) }),
  },
  {
    agent: "orchestrator", action: "capability_budget_check", label: null, severity: "ok", outcome: "ok", weight: 5,
    detail: () => ({ used_usd: (rand(12, 89) / 100).toFixed(2), cap_usd: "1.00", pct: rand(12, 89) }),
  },

  // ── Normal pipeline – intake_actor ─────────────────────────────────────────
  {
    agent: "intake_actor", action: "tool_call", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 7,
    detail: () => ({ tool: "read_claim_form", claim_id: pick(CLAIM_IDS) }),
  },
  {
    agent: "intake_actor", action: "tool_call", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 4,
    detail: () => ({ tool: "extract_claimant_details", claimant_id: pick(CLT_IDS) }),
  },

  // ── Normal pipeline – identity_verifier ────────────────────────────────────
  {
    agent: "identity_verifier", action: "tool_call", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 7,
    detail: () => ({ tool: "lookup_identity", claimant_id: pick(CLT_IDS), verified: true }),
  },
  {
    agent: "identity_verifier", action: "tool_call", label: "PERSONAL", severity: "ok", outcome: "ok", weight: 3,
    detail: () => ({ tool: "verify_document", doc_type: pick(["passport","drivers_license","national_id"]) }),
  },

  // ── Normal pipeline – claims_processor ─────────────────────────────────────
  {
    agent: "claims_processor", action: "tool_call", label: "CONFIDENTIAL", severity: "ok", outcome: "ok", weight: 7,
    detail: () => ({ tool: "check_policy", policy_id: pick(POLICY_IDS), coverage_valid: true }),
  },
  {
    agent: "claims_processor", action: "tool_call", label: "CONFIDENTIAL", severity: "ok", outcome: "ok", weight: 4,
    detail: () => ({ tool: "flag_anomaly", result: "CLEAN", confidence: (rand(82, 99) / 100).toFixed(2) }),
  },

  // ── Normal pipeline – settlement_actor ─────────────────────────────────────
  {
    agent: "settlement_actor", action: "tool_call", label: "CONFIDENTIAL", severity: "ok", outcome: "ok", weight: 4,
    detail: () => ({ tool: "create_settlement", claim_id: pick(CLAIM_IDS), amount_usd: rand(200, 15000) }),
  },
  {
    agent: "settlement_actor", action: "tool_call", label: "CONFIDENTIAL", severity: "ok", outcome: "ok", weight: 3,
    detail: () => ({ tool: "notify_claimant", channel: "email", claimant_id: pick(CLT_IDS) }),
  },

  // ── Normal pipeline – tool_registry ────────────────────────────────────────
  {
    agent: "tool_registry", action: "capability_check", label: "PERSONAL", severity: "ok", outcome: "verified", weight: 10,
    detail: () => ({ token_valid: true, scope_ok: true, agent: pick(["intake_actor","identity_verifier"]) }),
  },
  {
    agent: "tool_registry", action: "capability_check", label: "CONFIDENTIAL", severity: "ok", outcome: "verified", weight: 7,
    detail: () => ({ token_valid: true, scope_ok: true, agent: pick(["claims_processor","settlement_actor"]) }),
  },

  // ── Normal pipeline – data_layer & egress ──────────────────────────────────
  {
    agent: "data_layer", action: "rls_query", label: "CONFIDENTIAL", severity: "ok", outcome: "ok", weight: 8,
    detail: () => ({ rows: rand(1, 5), policy: "user_owns_claim", label_ceiling: "CONFIDENTIAL" }),
  },
  {
    agent: "egress_filter", action: "label_check", label: "PERSONAL", severity: "ok", outcome: "passed", weight: 6,
    detail: () => ({ ceiling: "PERSONAL", max_observed: "PERSONAL", redacted_fields: 0 }),
  },

  // ── Security / defence events (warn) ───────────────────────────────────────
  {
    agent: "tool_registry", action: "capability_check", label: "CONFIDENTIAL", severity: "warn",
    outcome: "denied(scope_mismatch)", weight: 3,
    detail: () => ({ token_valid: true, scope_ok: false, requested: "create_settlement", permitted: "check_policy", agent: "claims_processor" }),
  },
  {
    agent: "orchestrator", action: "budget_warning", label: null, severity: "warn", outcome: "warn", weight: 1,
    detail: () => ({ pct: rand(80, 95), used_usd: (rand(80, 95) / 100).toFixed(2), cap_usd: "1.00" }),
  },
  {
    agent: "egress_filter", action: "label_escalation_blocked", label: "SECRET", severity: "warn",
    outcome: "blocked", weight: 2,
    detail: () => ({ observed_label: "SECRET", ceiling: "PERSONAL", fields_redacted: rand(1, 3) }),
  },
  {
    agent: "orchestrator", action: "invalid_transition_rejected", label: null, severity: "warn",
    outcome: "rejected", weight: 2,
    detail: () => ({ attempted: pick(["SETTLEMENT","PROCESSING"]), current_state: "INTAKE", reason: "precondition_failed" }),
  },

  // ── Attack / alert events ───────────────────────────────────────────────────
  {
    agent: "ingress", action: "injection_detected", label: "UNTRUSTED", severity: "alert",
    outcome: "blocked", weight: 2,
    detail: () => ({ pattern: "ignore_prev_instructions", confidence: (rand(94, 99) / 100).toFixed(2), attack_id: pick([1, 2, 7]) }),
  },
  {
    agent: "tool_registry", action: "capability_check", label: null, severity: "alert",
    outcome: "denied(forged_token)", weight: 1,
    detail: () => ({ token_valid: false, sig_valid: false, agent: "claims_processor", attack_id: pick([29, 38, 39]) }),
  },
  {
    agent: "adversarial_agent", action: "probe_endpoint", label: "UNTRUSTED", severity: "alert",
    outcome: "blocked", weight: 2,
    detail: () => ({ endpoint: pick(["/api/claims","/api/settle","/api/policy"]), attack_id: pick([1, 20, 29, 66]) }),
  },
];

// Build weighted selection table.
const WEIGHTED: Template[] = TEMPLATES.flatMap((t) => Array(t.weight).fill(t) as Template[]);

function generateEvent(traceId: string): AuditRow {
  const tmpl = pick(WEIGHTED);
  return {
    id: uid(),
    ts: new Date().toISOString(),
    traceId,
    agent: tmpl.agent,
    action: tmpl.action,
    label: tmpl.label,
    severity: tmpl.severity,
    outcome: tmpl.outcome,
    detail: tmpl.detail(traceId),
  };
}

// ── Route handler ─────────────────────────────────────────────────────────────

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const SSE_HEADERS = {
  "Content-Type":      "text/event-stream",
  "Cache-Control":     "no-cache, no-transform",
  "X-Accel-Buffering": "no",
  "Connection":        "keep-alive",
};

function simulatedStream(): Response {
  const encoder = new TextEncoder();
  let cancelled = false;

  const stream = new ReadableStream({
    async start(controller) {
      try {
        while (!cancelled) {
          const traceId = pick(TRACE_POOL);
          const sessionLen = rand(4, 9);

          for (let i = 0; i < sessionLen && !cancelled; i++) {
            const row = generateEvent(traceId);
            const line = `event: audit_row\ndata: ${JSON.stringify(row)}\n\n`;
            controller.enqueue(encoder.encode(line));
            await sleep(rand(300, 900));
          }
        }
      } catch {
        // client disconnected or controller closed
      }
      if (!cancelled) controller.close();
    },
    cancel() {
      cancelled = true;
    },
  });

  return new Response(stream, { headers: SSE_HEADERS });
}

export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_URL}/showcase/sse/audit`, {
      headers: { Accept: "text/event-stream", "Cache-Control": "no-cache" },
    });
    if (upstream.ok && upstream.body) {
      return new Response(upstream.body, { headers: SSE_HEADERS });
    }
  } catch {
    // backend not available — fall through to simulated stream
  }
  return simulatedStream();
}
