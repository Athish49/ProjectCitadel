import type { AdversarialAttempt, BreachCountEvent } from "@/lib/types/adversarial";

export const dynamic = "force-dynamic";

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
  return `adv${Date.now().toString(36)}${(++_seq).toString(36)}`;
}

// ── Attack category data ──────────────────────────────────────────────────────

const ATTACK_NAMES: Record<number, string> = {
  1:  "Direct Prompt Injection",
  3:  "Role-Play / Persona Override",
  7:  "Goal Hijacking",
  9:  "Indirect Prompt Injection",
  20: "Jailbreak via Hypothetical",
  21: "Token Smuggling",
  25: "Delimiter Confusion",
  26: "Nested Instruction Override",
  28: "Adversarial Suffix",
  29: "Context Window Flooding",
  37: "System Prompt Extraction",
  43: "Multi-turn Escalation",
  65: "Unicode Homoglyph Evasion",
  66: "Base64 / Encoding Bypass",
  78: "Markdown / HTML Injection",
};

const ATTACK_IDS = Object.keys(ATTACK_NAMES).map(Number);

const DETECTION_PATTERNS = [
  "ignore_instructions",
  "dan_mode",
  "jailbreak",
  "delimiter_abuse",
  "base64_encoded_instructions",
  "role_override",
  "system_prompt_leak",
  "unicode_homoglyph",
];

// ~10% EVADED_INGRESS rate to simulate realistic outcomes.
function randomVerdict(): "BLOCKED_INGRESS" | "EVADED_INGRESS" | "API_ERROR" {
  const r = Math.random();
  if (r < 0.10) return "EVADED_INGRESS";
  if (r < 0.12) return "API_ERROR";
  return "BLOCKED_INGRESS";
}

let _breachCount = 0;
let _lastBreachAt: string | null = null;
let _attemptNumber = 0;

function generateAttempt(): AdversarialAttempt {
  const attackId = pick(ATTACK_IDS);
  const verdict = randomVerdict();
  const isBreached = verdict === "EVADED_INGRESS";

  if (isBreached) {
    _breachCount++;
    _lastBreachAt = new Date().toISOString();
  }

  const detections =
    verdict === "BLOCKED_INGRESS"
      ? [pick(DETECTION_PATTERNS), ...(Math.random() < 0.3 ? [pick(DETECTION_PATTERNS)] : [])]
      : [];

  return {
    trace_id: uid(),
    session_id: `sess-${Math.floor(_attemptNumber / 15).toString(36)}`,
    attack_id: attackId,
    verdict,
    sanitizer_detections: detections,
    chars_stripped: verdict === "BLOCKED_INGRESS" ? rand(8, 120) : 0,
    is_breach: isBreached,
    breach_count: _breachCount,
    last_breach_at: _lastBreachAt,
    timestamp: new Date().toISOString(),
  };
}

// ── Route handler ─────────────────────────────────────────────────────────────

export async function GET() {
  const encoder = new TextEncoder();
  let cancelled = false;

  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Send initial breach_count event so the client has state immediately.
        const init: BreachCountEvent = {
          breach_count: _breachCount,
          last_breach_at: _lastBreachAt,
        };
        controller.enqueue(
          encoder.encode(`event: breach_count\ndata: ${JSON.stringify(init)}\n\n`)
        );

        while (!cancelled) {
          _attemptNumber++;
          const attempt = generateAttempt();
          controller.enqueue(
            encoder.encode(`event: attempt\ndata: ${JSON.stringify(attempt)}\n\n`)
          );

          // Emit updated breach_count after each breach.
          if (attempt.is_breach) {
            const stats: BreachCountEvent = {
              breach_count: _breachCount,
              last_breach_at: _lastBreachAt,
            };
            controller.enqueue(
              encoder.encode(`event: breach_count\ndata: ${JSON.stringify(stats)}\n\n`)
            );
          }

          await sleep(rand(800, 1800));
        }
      } catch {
        // client disconnected
      }
      if (!cancelled) controller.close();
    },
    cancel() {
      cancelled = true;
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type":      "text/event-stream",
      "Cache-Control":     "no-cache, no-transform",
      "X-Accel-Buffering": "no",
      "Connection":        "keep-alive",
    },
  });
}
