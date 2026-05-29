"use client";

import { useState, useMemo } from "react";
import { Pause, Play, Trash2, Wifi, WifiOff, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuditStream } from "@/lib/hooks/use-audit-stream";
import type { AuditRow, AuditAgent, AuditSeverity } from "@/lib/types/audit";

// ── Styling maps ──────────────────────────────────────────────────────────────

const SEV_DOT: Record<AuditSeverity, string> = {
  ok:    "bg-[#4ADE80]",
  info:  "bg-[#5BB5F2]",
  warn:  "bg-[#F5B056]",
  alert: "bg-[#F25B5B]",
};

const SEV_TEXT: Record<AuditSeverity, string> = {
  ok:    "text-[#4ADE80]",
  info:  "text-[#5BB5F2]",
  warn:  "text-[#F5B056]",
  alert: "text-[#F25B5B]",
};

const OUTCOME_COLOR: Record<string, string> = {
  ok:       "text-[#4ADE80]",
  verified: "text-[#4ADE80]",
  passed:   "text-[#4ADE80]",
  blocked:  "text-[#F25B5B]",
  rejected: "text-[#F25B5B]",
  warn:     "text-[#F5B056]",
};

const AGENTS: AuditAgent[] = [
  "ingress","parser","orchestrator","intake_actor","identity_verifier",
  "claims_processor","settlement_actor","tool_registry","data_layer",
  "egress_filter","adversarial_agent",
];

const SEVERITIES: AuditSeverity[] = ["ok","info","warn","alert"];

// ── Formatting helpers ────────────────────────────────────────────────────────

function fmtTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toTimeString().slice(0, 8) + "." + String(d.getMilliseconds()).padStart(3, "0");
  } catch {
    return ts;
  }
}

function outcomeColor(outcome: string): string {
  for (const [k, v] of Object.entries(OUTCOME_COLOR)) {
    if (outcome.startsWith(k)) return v;
  }
  if (outcome.startsWith("denied")) return "text-[#F25B5B]";
  return "text-[#8B96A8]";
}

// ── Row component ─────────────────────────────────────────────────────────────

function AuditRowItem({ row, initialTrace }: { row: AuditRow; initialTrace: string | null }) {
  const [expanded, setExpanded] = useState(false);
  const isHighlighted = initialTrace && row.traceId === initialTrace;

  return (
    <div
      className={cn(
        "border-b border-[#0F141B] font-mono",
        isHighlighted && "bg-[#5BB5F2]/5",
        row.severity === "alert" && "bg-[#F25B5B]/4",
      )}
    >
      {/* main row */}
      <div
        className="flex cursor-pointer items-center gap-0 px-4 py-1.5 hover:bg-[#0F141B] select-none"
        onClick={() => setExpanded((p) => !p)}
      >
        {/* expand icon */}
        <span className="mr-2 shrink-0 text-[#3A4452]">
          {expanded
            ? <ChevronDown className="h-2.5 w-2.5" />
            : <ChevronRight className="h-2.5 w-2.5" />
          }
        </span>

        {/* severity dot */}
        <span className={cn("mr-3 h-1.5 w-1.5 shrink-0 rounded-full", SEV_DOT[row.severity])} />

        {/* timestamp */}
        <span className="w-28 shrink-0 text-[10px] tabular-nums text-[#8B96A8]">
          {fmtTime(row.ts)}
        </span>

        {/* trace */}
        <span
          className="mr-4 w-24 shrink-0 truncate text-[10px] text-[#5BB5F2]/70"
          title={`trace=${row.traceId}`}
        >
          trace={row.traceId}
        </span>

        {/* agent */}
        <span className="mr-4 w-36 shrink-0 truncate text-[10px] text-[#A8B4C0]">
          {row.agent}
        </span>

        {/* action */}
        <span className="mr-4 min-w-0 flex-1 truncate text-[10px] text-[#E8EDF2]">
          {row.action}
        </span>

        {/* label */}
        {row.label && (
          <span className="mr-4 w-24 shrink-0 text-right text-[10px] text-[#8B96A8]">
            {row.label}
          </span>
        )}

        {/* outcome */}
        <span className={cn("w-32 shrink-0 text-right text-[10px] font-medium", outcomeColor(row.outcome))}>
          {row.outcome}
        </span>
      </div>

      {/* expanded detail */}
      {expanded && (
        <div className="border-t border-[#1E2632] bg-[#0A0E14] px-4 py-3">
          <div className="mb-1 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">
            Event detail — id={row.id}
          </div>
          <pre className="overflow-x-auto font-mono text-[10px] leading-relaxed text-[#A8B4C0]">
            {JSON.stringify({ ...row.detail, traceId: row.traceId, ts: row.ts }, null, 2)}
          </pre>
          <div className="mt-2 flex gap-3">
            <a
              href={`/playground?autorun=1`}
              className="font-mono text-[10px] text-[#5BB5F2] hover:text-[#A8D8F8]"
            >
              → Replay in playground
            </a>
            <a
              href={`/matrix`}
              className="font-mono text-[10px] text-[#5BB5F2] hover:text-[#A8D8F8]"
            >
              → Attack matrix
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface AuditFeedProps {
  initialAgent?:    AuditAgent | null;
  initialSeverity?: AuditSeverity | null;
  initialTrace?:    string | null;
}

export function AuditFeed({ initialAgent, initialSeverity, initialTrace }: AuditFeedProps) {
  const { rows, paused, connected, togglePause, clear } = useAuditStream();

  const [agentFilter,    setAgentFilter]    = useState<AuditAgent    | null>(initialAgent    ?? null);
  const [severityFilter, setSeverityFilter] = useState<AuditSeverity | null>(initialSeverity ?? null);
  const [traceFilter,    setTraceFilter]    = useState<string>(initialTrace ?? "");

  const filtered = useMemo(() => {
    let r = rows;
    if (agentFilter)                   r = r.filter((x) => x.agent === agentFilter);
    if (severityFilter)                r = r.filter((x) => x.severity === severityFilter);
    if (traceFilter.trim().length > 0) r = r.filter((x) => x.traceId.startsWith(traceFilter.trim()));
    return r;
  }, [rows, agentFilter, severityFilter, traceFilter]);

  // Counts for the stats bar
  const counts = useMemo(() => ({
    ok:    rows.filter((r) => r.severity === "ok").length,
    info:  rows.filter((r) => r.severity === "info").length,
    warn:  rows.filter((r) => r.severity === "warn").length,
    alert: rows.filter((r) => r.severity === "alert").length,
  }), [rows]);

  return (
    <div className="flex h-screen flex-col bg-[#0A0E14]">
      {/* page header */}
      <div className="shrink-0 border-b border-[#1E2632] px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-mono text-sm font-semibold text-[#E8EDF2]">Live Audit Feed</h1>
            <p className="mt-0.5 font-mono text-[10px] text-[#8B96A8]">
              Real-time defence events · last {rows.length} of max 150
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* connection indicator */}
            <div className="flex items-center gap-1.5">
              {connected
                ? <Wifi    className="h-3 w-3 text-[#4ADE80]" />
                : <WifiOff className="h-3 w-3 text-[#F25B5B]" />
              }
              <span className={cn("font-mono text-[10px]", connected ? "text-[#4ADE80]" : "text-[#F25B5B]")}>
                {connected ? "live" : "reconnecting…"}
              </span>
            </div>

            {/* pause / resume */}
            <button
              type="button"
              onClick={togglePause}
              className={cn(
                "flex items-center gap-1.5 rounded border px-2.5 py-1 font-mono text-[10px] transition-colors",
                paused
                  ? "border-[#F5B056]/50 bg-[#F5B056]/10 text-[#F5B056] hover:bg-[#F5B056]/15"
                  : "border-[#1E2632] text-[#8B96A8] hover:border-[#8B96A8]/40 hover:text-[#E8EDF2]"
              )}
            >
              {paused ? <Play className="h-2.5 w-2.5" /> : <Pause className="h-2.5 w-2.5" />}
              {paused ? "Resume" : "Pause"}
            </button>

            {/* clear */}
            <button
              type="button"
              onClick={clear}
              className="flex items-center gap-1.5 rounded border border-[#1E2632] px-2.5 py-1 font-mono text-[10px] text-[#8B96A8] transition-colors hover:border-[#8B96A8]/40 hover:text-[#E8EDF2]"
            >
              <Trash2 className="h-2.5 w-2.5" />
              Clear
            </button>
          </div>
        </div>

        {/* severity counters */}
        <div className="mt-3 flex gap-5">
          {(["ok","info","warn","alert"] as AuditSeverity[]).map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", SEV_DOT[s])} />
              <span className={cn("font-mono text-[10px] tabular-nums", SEV_TEXT[s])}>
                {counts[s]} {s}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* filter toolbar */}
      <div className="shrink-0 flex flex-wrap items-center gap-3 border-b border-[#1E2632] px-6 py-2.5">
        {/* severity chips */}
        <div className="flex items-center gap-1">
          <span className="mr-1 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">Severity</span>
          <button
            type="button"
            onClick={() => setSeverityFilter(null)}
            className={cn(
              "rounded border px-2 py-0.5 font-mono text-[9px] transition-colors",
              severityFilter === null
                ? "border-[#5BB5F2]/50 bg-[#5BB5F2]/10 text-[#5BB5F2]"
                : "border-[#1E2632] text-[#8B96A8] hover:border-[#8B96A8]/30"
            )}
          >all</button>
          {SEVERITIES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSeverityFilter((prev) => prev === s ? null : s)}
              className={cn(
                "rounded border px-2 py-0.5 font-mono text-[9px] transition-colors",
                severityFilter === s
                  ? cn("border-current/50", SEV_TEXT[s])
                  : "border-[#1E2632] text-[#8B96A8] hover:border-[#8B96A8]/30"
              )}
            >{s}</button>
          ))}
        </div>

        {/* agent select */}
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">Agent</span>
          <select
            value={agentFilter ?? ""}
            onChange={(e) => setAgentFilter((e.target.value || null) as AuditAgent | null)}
            className="rounded border border-[#1E2632] bg-[#0F141B] px-2 py-0.5 font-mono text-[10px] text-[#A8B4C0] focus:border-[#5BB5F2]/40 focus:outline-none"
          >
            <option value="">All agents</option>
            {AGENTS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>

        {/* trace filter */}
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">Trace</span>
          <input
            type="text"
            value={traceFilter}
            onChange={(e) => setTraceFilter(e.target.value)}
            placeholder="prefix…"
            className="w-24 rounded border border-[#1E2632] bg-[#0F141B] px-2 py-0.5 font-mono text-[10px] text-[#A8B4C0] placeholder-[#3A4452] focus:border-[#5BB5F2]/40 focus:outline-none"
          />
        </div>

        {/* clear filters */}
        {(agentFilter || severityFilter || traceFilter) && (
          <button
            type="button"
            onClick={() => { setAgentFilter(null); setSeverityFilter(null); setTraceFilter(""); }}
            className="font-mono text-[9px] text-[#8B96A8] underline underline-offset-2 hover:text-[#E8EDF2]"
          >
            clear filters
          </button>
        )}

        <span className="ml-auto font-mono text-[9px] text-[#3A4452]">
          {filtered.length} / {rows.length} events
        </span>
      </div>

      {/* column headers */}
      <div className="shrink-0 flex items-center gap-0 border-b border-[#1E2632] px-4 py-1">
        <span className="w-5 shrink-0" />
        <span className="mr-3 h-1.5 w-1.5 shrink-0" />
        <span className="w-28 shrink-0 font-mono text-[9px] uppercase tracking-widest text-[#3A4452]">Time</span>
        <span className="mr-4 w-24 shrink-0 font-mono text-[9px] uppercase tracking-widest text-[#3A4452]">Trace</span>
        <span className="mr-4 w-36 shrink-0 font-mono text-[9px] uppercase tracking-widest text-[#3A4452]">Agent</span>
        <span className="mr-4 flex-1 font-mono text-[9px] uppercase tracking-widest text-[#3A4452]">Action</span>
        <span className="mr-4 w-24 shrink-0 text-right font-mono text-[9px] uppercase tracking-widest text-[#3A4452]">Label</span>
        <span className="w-32 shrink-0 text-right font-mono text-[9px] uppercase tracking-widest text-[#3A4452]">Outcome</span>
      </div>

      {/* event rows */}
      <div className="flex-1 overflow-y-auto">
        {paused && (
          <div className="sticky top-0 z-10 border-b border-[#F5B056]/30 bg-[#F5B056]/10 px-4 py-1.5 text-center font-mono text-[10px] text-[#F5B056]">
            ⏸ Feed paused — {rows.length - filtered.length > 0 ? `${rows.length} events buffered` : "click Resume to continue"}
          </div>
        )}

        {filtered.length === 0 && rows.length === 0 && (
          <div className="flex items-center justify-center py-24 font-mono text-[11px] text-[#8B96A8]">
            Connecting to audit stream…
          </div>
        )}

        {filtered.length === 0 && rows.length > 0 && (
          <div className="flex items-center justify-center py-24 font-mono text-[11px] text-[#8B96A8]">
            No events match the active filters.
          </div>
        )}

        {filtered.map((row) => (
          <AuditRowItem key={row.id} row={row} initialTrace={initialTrace ?? null} />
        ))}
      </div>
    </div>
  );
}
