"use client";

import { MATRIX_ROWS, ATTACK_NAMES } from "@/lib/data/matrix";
import type { AdversarialAttempt } from "@/lib/types/adversarial";
import type { AuditRow } from "@/lib/types/audit";

/** HH:MM:SS, 24h — matches the design prototype's own stamp() helper. */
export function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    const p = (n: number) => String(n).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

export function fmtRelative(iso: string | null): string {
  if (!iso) return "never";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function catNameFor(attackId: number): string | null {
  return MATRIX_ROWS.find((r) => r.id === attackId)?.catName ?? null;
}

/** Derives the source-table tag (AL / SE / CT / IA) from the audit row id's prefix. */
function sourceTag(id: string): string {
  if (id.startsWith("al-")) return "AL";
  if (id.startsWith("se-")) return "SE";
  if (id.startsWith("ct-")) return "CT";
  if (id.startsWith("ia-")) return "IA";
  return "—";
}

/** One row of the attacker's-view live feed, driven by a real AdversarialAttempt. */
export function AttemptFeedRow({ attempt }: { attempt: AdversarialAttempt }) {
  const isBreach = attempt.is_breach || attempt.pipeline_verdict === "BREACH";
  const isError = attempt.verdict === "API_ERROR" || attempt.pipeline_verdict === "ERROR";
  const pipelinePending = attempt.pipeline_verdict == null;
  const label = isBreach ? "BREACH" : isError ? "ERROR" : "BLOCKED";
  // Attacker's-view colour rule: red = the attack was detected and stopped
  // (BLOCKED), green = it evaded every layer (BREACH — a successful attack,
  // not flagged by the system), amber = error. (Intentionally the inverse of
  // the defender's-view AuditFeedRow below, which colours by severity.)
  const color = isBreach ? "var(--ok)" : isError ? "var(--warn)" : "var(--alert)";
  const name = ATTACK_NAMES[attempt.attack_id] ?? `Attack #${attempt.attack_id}`;
  const layer = attempt.blocked_by_layer
    ? `blocked at ${attempt.blocked_by_layer}`
    : isBreach
    ? "evaded all 7 layers"
    : pipelinePending
    ? "awaiting pipeline verdict"
    : "blocked at ingress";
  const det =
    attempt.sanitizer_detections.length > 0
      ? attempt.sanitizer_detections.join(", ")
      : isBreach
      ? "no defense triggered"
      : "no patterns matched";

  return (
    <div
      className="mono"
      style={{
        padding: "11px 18px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        fontSize: "12.5px",
        animation: "citadel-row-in 0.5s ease",
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "2px 16px", alignItems: "baseline" }}>
        <span style={{ color: "rgba(255,255,255,0.55)", width: "66px" }}>{fmtTime(attempt.timestamp)}</span>
        <span style={{ flex: "1 1 220px", color: "rgba(255,255,255,0.94)" }}>
          #{attempt.attack_id} {name}
        </span>
        <span style={{ letterSpacing: "0.08em", color }}>{label}</span>
      </div>
      <div style={{ marginTop: "2px", paddingLeft: "82px", fontSize: "11.5px", color: "rgba(255,255,255,0.58)" }}>
        {layer} · {det} · trace {attempt.trace_id.slice(0, 8)}
      </div>
    </div>
  );
}

/** One row of the defender's-view audit table, driven by a real AuditRow. */
export function AuditFeedRow({ row }: { row: AuditRow }) {
  // severity is the backend's own classification — map it straight to the
  // shared signal palette rather than re-deriving a colour from the outcome
  // string: ok -> defence held (green), info -> informational (blue),
  // warn -> flagged (amber), alert -> breach / broken integrity only (red).
  const color =
    row.severity === "alert"
      ? "var(--alert)"
      : row.severity === "warn"
      ? "var(--warn)"
      : row.severity === "info"
      ? "var(--blue)"
      : "var(--ok)";

  return (
    <div
      className="mono"
      style={{
        display: "grid",
        gridTemplateColumns: "80px 96px 48px 150px 1fr 90px",
        gap: "12px",
        padding: "10px 18px",
        fontSize: "12px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        animation: "citadel-row-in 0.5s ease",
      }}
    >
      <span style={{ color: "rgba(255,255,255,0.55)" }}>{fmtTime(row.ts)}</span>
      <span style={{ color: "rgba(255,255,255,0.62)" }}>{row.traceId.slice(0, 8)}</span>
      <span style={{ color: "rgba(255,255,255,0.62)" }}>{sourceTag(row.id)}</span>
      <span style={{ color: "rgba(255,255,255,0.88)" }}>{row.agent}</span>
      <span style={{ color: "rgba(255,255,255,0.88)" }}>
        {row.action}
        {row.label ? ` · ${row.label}` : ""}
      </span>
      <span style={{ textAlign: "right", color }}>{row.outcome}</span>
    </div>
  );
}
