"use client";

import { useCallback } from "react";
import { Pause, Play, Trash2, Wifi, WifiOff, ShieldAlert, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdversarialStream } from "@/lib/hooks/use-adversarial-stream";
import type { AdversarialAttempt } from "@/lib/types/adversarial";

// ── Verdict styling ───────────────────────────────────────────────────────────

const VERDICT_BADGE: Record<string, string> = {
  BLOCKED_INGRESS: "bg-[#1E2632] text-[#4ADE80] border border-[#4ADE80]/30",
  EVADED_INGRESS:  "bg-[#3D1414] text-[#F25B5B] border border-[#F25B5B]/60",
  API_ERROR:       "bg-[#1E2632] text-[#F5B056] border border-[#F5B056]/30",
};

const VERDICT_LABEL: Record<string, string> = {
  BLOCKED_INGRESS: "BLOCKED",
  EVADED_INGRESS:  "BREACH",
  API_ERROR:       "ERROR",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toTimeString().slice(0, 8);
  } catch {
    return ts;
  }
}

function fmtRelative(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function BreachCounter({
  count,
  lastAt,
}: {
  count: number;
  lastAt: string | null;
}) {
  const isAlarm = count > 0;
  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-lg border px-6 py-4 font-mono",
        isAlarm
          ? "border-[#F25B5B]/40 bg-[#3D1414]"
          : "border-[#1E2632] bg-[#0A0E14]"
      )}
    >
      {isAlarm ? (
        <ShieldAlert className="h-8 w-8 shrink-0 text-[#F25B5B]" />
      ) : (
        <ShieldCheck className="h-8 w-8 shrink-0 text-[#4ADE80]" />
      )}
      <div>
        <div
          className={cn(
            "text-3xl font-bold tabular-nums",
            isAlarm ? "text-[#F25B5B]" : "text-[#4ADE80]"
          )}
        >
          {count}
        </div>
        <div className="text-xs text-[#8B96A8]">
          {isAlarm ? `last breach ${fmtRelative(lastAt)}` : "no breaches"}
        </div>
      </div>
      <div className="ml-4">
        <div className="text-sm font-semibold text-[#E8EDF2]">
          Successful Breaches
        </div>
        <div className="text-xs text-[#8B96A8]">
          payloads that evaded ingress sanitization
        </div>
      </div>
    </div>
  );
}

function AttemptRow({ attempt }: { attempt: AdversarialAttempt }) {
  const isBreach = attempt.verdict === "EVADED_INGRESS";
  return (
    <div
      className={cn(
        "flex items-start gap-3 border-b border-[#1E2632] px-4 py-2.5 font-mono text-xs transition-colors",
        isBreach && "bg-[#3D1414]/40"
      )}
    >
      <span className="w-20 shrink-0 text-[#8B96A8]">{fmtTime(attempt.timestamp)}</span>

      <span
        className={cn(
          "w-20 shrink-0 rounded px-1.5 py-0.5 text-center text-[10px] font-semibold uppercase tracking-wide",
          VERDICT_BADGE[attempt.verdict] ?? "bg-[#1E2632] text-[#8B96A8]"
        )}
      >
        {VERDICT_LABEL[attempt.verdict] ?? attempt.verdict}
      </span>

      <span className="w-6 shrink-0 text-[#8B96A8]">#{attempt.attack_id}</span>

      {attempt.sanitizer_detections.length > 0 ? (
        <span className="truncate text-[#8B96A8]">
          {attempt.sanitizer_detections.join(", ")}
        </span>
      ) : isBreach ? (
        <span className="text-[#F25B5B]">no patterns detected — evaded</span>
      ) : (
        <span className="text-[#5BB5F2]">clean pass</span>
      )}

      <span className="ml-auto shrink-0 text-[#8B96A8]">
        {attempt.trace_id.slice(0, 8)}
      </span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdversaryPage() {
  const {
    attempts,
    breachCount,
    lastBreachAt,
    connected,
    paused,
    togglePause,
    clear,
  } = useAdversarialStream();

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6 px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-lg font-semibold text-[#E8EDF2]">
            Adversarial Agent Dashboard
          </h1>
          <p className="mt-0.5 text-xs text-[#8B96A8]">
            Live feed of attack attempts against the ingress sanitizer
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="h-4 w-4 text-[#4ADE80]" />
          ) : (
            <WifiOff className="h-4 w-4 text-[#F25B5B]" />
          )}
          <span className="font-mono text-xs text-[#8B96A8]">
            {connected ? "live" : "disconnected"}
          </span>
        </div>
      </div>

      {/* Breach counter */}
      <BreachCounter count={breachCount} lastAt={lastBreachAt} />

      {/* Feed controls */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-[#8B96A8]">
          {attempts.length} attempts
        </span>
        <div className="ml-auto flex gap-2">
          <button
            onClick={togglePause}
            className="flex items-center gap-1 rounded border border-[#1E2632] bg-[#0A0E14] px-3 py-1.5 font-mono text-xs text-[#8B96A8] hover:text-[#E8EDF2]"
          >
            {paused ? (
              <><Play className="h-3 w-3" /> resume</>
            ) : (
              <><Pause className="h-3 w-3" /> pause</>
            )}
          </button>
          <button
            onClick={clear}
            className="flex items-center gap-1 rounded border border-[#1E2632] bg-[#0A0E14] px-3 py-1.5 font-mono text-xs text-[#8B96A8] hover:text-[#E8EDF2]"
          >
            <Trash2 className="h-3 w-3" /> clear
          </button>
        </div>
      </div>

      {/* Feed table header */}
      <div className="rounded-t-lg border border-b-0 border-[#1E2632] bg-[#0A0E14]">
        <div className="flex gap-3 border-b border-[#1E2632] px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">
          <span className="w-20">time</span>
          <span className="w-20">verdict</span>
          <span className="w-6">id</span>
          <span>detections / note</span>
          <span className="ml-auto">trace</span>
        </div>

        {/* Feed rows */}
        <div className="max-h-[60vh] overflow-y-auto">
          {attempts.length === 0 ? (
            <div className="px-4 py-8 text-center font-mono text-xs text-[#8B96A8]">
              {connected ? "waiting for attack attempts…" : "connecting…"}
            </div>
          ) : (
            attempts.map((a) => <AttemptRow key={a.trace_id} attempt={a} />)
          )}
        </div>
      </div>
    </div>
  );
}
