"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Pause, Play, Trash2, Wifi, WifiOff, ShieldAlert, ShieldCheck, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAdversarialStream } from "@/lib/hooks/use-adversarial-stream";
import type { AdversarialAttempt } from "@/lib/types/adversarial";

// ── Seeded demo data ──────────────────────────────────────────────────────────

const BASELINE_TOTAL = 1247;
const MONTHLY_CAP = 50;
const SYSTEM_START_ISO = "2026-05-01T00:00:00.000Z";

// Attempt counts by hour-of-day (index 0 = midnight UTC)
const BASELINE_HOURLY = [2, 1, 0, 0, 1, 2, 0, 0, 0, 0, 1, 3, 4, 6, 9, 12, 15, 18, 14, 11, 8, 5, 3, 2];

// 6 days of prior API spend (USD)
const SEED_DAILY_COST = [0.42, 0.61, 0.58, 0.73, 0.81, 0.65];

// Cost per live attempt (estimated)
const COST_PER_ATTEMPT = 0.0028;

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
    return new Date(ts).toTimeString().slice(0, 8);
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

function fmtElapsed(ms: number): string {
  const totalMin = Math.floor(ms / 60_000);
  const d = Math.floor(totalMin / 1440);
  const h = Math.floor((totalMin % 1440) / 60);
  const m = totalMin % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

// ── HoursSinceBreachCard ──────────────────────────────────────────────────────

function HoursSinceBreachCard({ lastBreachAt }: { lastBreachAt: string | null }) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const startMs = lastBreachAt
    ? new Date(lastBreachAt).getTime()
    : new Date(SYSTEM_START_ISO).getTime();

  const elapsed = now - startMs;
  const label = lastBreachAt ? "since last breach" : "breach-free";

  return (
    <div className="flex flex-col gap-1 rounded border border-[#1E2632] bg-[#0A0E14] px-4 py-3">
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">
        <Clock className="h-3 w-3" />
        {label}
      </div>
      <div className="font-mono text-xl font-bold tabular-nums text-[#4ADE80]">
        {fmtElapsed(elapsed)}
      </div>
      <div className="font-mono text-[10px] text-[#8B96A8]">
        {lastBreachAt ? `last: ${fmtRelative(lastBreachAt)}` : `since ${new Date(SYSTEM_START_ISO).toLocaleDateString()}`}
      </div>
    </div>
  );
}

// ── StatCard ──────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="flex flex-col gap-1 rounded border border-[#1E2632] bg-[#0A0E14] px-4 py-3">
      <div className="font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">{label}</div>
      <div className={cn("font-mono text-xl font-bold tabular-nums", color ?? "text-[#E8EDF2]")}>
        {value}
      </div>
      {sub && <div className="font-mono text-[10px] text-[#8B96A8]">{sub}</div>}
    </div>
  );
}

// ── AttemptHistogram ──────────────────────────────────────────────────────────

function AttemptHistogram({ attempts }: { attempts: AdversarialAttempt[] }) {
  const W = 480;
  const H = 120;
  const PAD = { top: 8, right: 8, bottom: 24, left: 28 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  // bucket live attempts into hour-of-day bins
  const liveBuckets = new Array<number>(24).fill(0);
  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  for (const a of attempts) {
    const t = new Date(a.timestamp).getTime();
    if (t >= cutoff) {
      const h = new Date(a.timestamp).getUTCHours();
      liveBuckets[h]++;
    }
  }

  const combined = BASELINE_HOURLY.map((b, i) => b + liveBuckets[i]);
  const maxVal = Math.max(...combined, 1);
  const barW = innerW / 24;
  const nowHour = new Date().getUTCHours();

  return (
    <div className="rounded border border-[#1E2632] bg-[#0A0E14] p-4">
      <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">
        Attempts · last 24 h (by UTC hour)
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
        {/* Y gridlines */}
        {[0.25, 0.5, 0.75, 1].map((f) => {
          const y = PAD.top + innerH * (1 - f);
          return (
            <g key={f}>
              <line x1={PAD.left} y1={y} x2={PAD.left + innerW} y2={y} stroke="#1E2632" strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 3} textAnchor="end" fill="#8B96A8" fontSize={8} fontFamily="monospace">
                {Math.round(maxVal * f)}
              </text>
            </g>
          );
        })}

        {/* Bars */}
        {combined.map((val, i) => {
          const barH = (val / maxVal) * innerH;
          const x = PAD.left + i * barW + 1;
          const y = PAD.top + innerH - barH;
          const isCurrent = i === nowHour;
          return (
            <motion.rect
              key={i}
              x={x}
              width={barW - 2}
              initial={{ y: PAD.top + innerH, height: 0 }}
              animate={{ y, height: barH }}
              transition={{ duration: 0.6, delay: i * 0.015, ease: "easeOut" }}
              fill={isCurrent ? "#5BB5F2" : "#1E3A5F"}
              rx={1}
            />
          );
        })}

        {/* X axis labels (every 6h) */}
        {[0, 6, 12, 18].map((h) => (
          <text
            key={h}
            x={PAD.left + h * barW + barW / 2}
            y={H - 4}
            textAnchor="middle"
            fill="#8B96A8"
            fontSize={8}
            fontFamily="monospace"
          >
            {String(h).padStart(2, "0")}:00
          </text>
        ))}
      </svg>
    </div>
  );
}

// ── CostGraph ─────────────────────────────────────────────────────────────────

function CostGraph({ totalAttempts }: { totalAttempts: number }) {
  const W = 480;
  const H = 120;
  const PAD = { top: 12, right: 16, bottom: 24, left: 40 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const liveSpend = +(totalAttempts * COST_PER_ATTEMPT).toFixed(2);
  const data = [...SEED_DAILY_COST, liveSpend];
  const total7d = data.reduce((s, v) => s + v, 0);
  const capPct = Math.min((total7d / MONTHLY_CAP) * 100, 100).toFixed(1);

  const maxVal = Math.max(...data, 0.1);
  const pts = data.map((v, i) => {
    const x = PAD.left + (i / (data.length - 1)) * innerW;
    const y = PAD.top + innerH * (1 - v / maxVal);
    return { x, y };
  });

  const linePath = pts
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" ");

  const areaPath =
    `M${pts[0].x.toFixed(1)},${(PAD.top + innerH).toFixed(1)} ` +
    pts.map((p) => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ") +
    ` L${pts[pts.length - 1].x.toFixed(1)},${(PAD.top + innerH).toFixed(1)} Z`;

  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Today"];

  return (
    <div className="rounded border border-[#1E2632] bg-[#0A0E14] p-4">
      <div className="mb-1 flex items-baseline justify-between">
        <div className="font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">
          Est. spend · last 7 days
        </div>
        <div className="font-mono text-[10px] text-[#8B96A8]">
          ${total7d.toFixed(2)} / ${MONTHLY_CAP} cap ({capPct}%)
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }}>
        {/* Y gridlines */}
        {[0.5, 1].map((f) => {
          const y = PAD.top + innerH * (1 - f);
          return (
            <g key={f}>
              <line x1={PAD.left} y1={y} x2={PAD.left + innerW} y2={y} stroke="#1E2632" strokeWidth={1} />
              <text x={PAD.left - 4} y={y + 3} textAnchor="end" fill="#8B96A8" fontSize={8} fontFamily="monospace">
                ${(maxVal * f).toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* Area fill */}
        <motion.path
          d={areaPath}
          fill="#5BB5F2"
          fillOpacity={0.08}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
        />

        {/* Line */}
        <motion.path
          d={linePath}
          fill="none"
          stroke="#5BB5F2"
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, ease: "easeOut" }}
        />

        {/* Dots */}
        {pts.map((p, i) => (
          <motion.circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={2.5}
            fill={i === pts.length - 1 ? "#5BB5F2" : "#1E3A5F"}
            stroke="#5BB5F2"
            strokeWidth={1}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 + i * 0.05 }}
          />
        ))}

        {/* X axis labels */}
        {pts.map((p, i) => (
          <text
            key={i}
            x={p.x}
            y={H - 4}
            textAnchor="middle"
            fill={i === pts.length - 1 ? "#5BB5F2" : "#8B96A8"}
            fontSize={8}
            fontFamily="monospace"
          >
            {days[i] ?? ""}
          </text>
        ))}
      </svg>
    </div>
  );
}

// ── BreachCounter (kept for backward compat, used inline below) ───────────────

function BreachCounter({ count, lastAt }: { count: number; lastAt: string | null }) {
  const isAlarm = count > 0;
  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-lg border px-6 py-4 font-mono",
        isAlarm ? "border-[#F25B5B]/40 bg-[#3D1414]" : "border-[#1E2632] bg-[#0A0E14]"
      )}
    >
      {isAlarm ? (
        <ShieldAlert className="h-8 w-8 shrink-0 text-[#F25B5B]" />
      ) : (
        <ShieldCheck className="h-8 w-8 shrink-0 text-[#4ADE80]" />
      )}
      <div>
        <div className={cn("text-3xl font-bold tabular-nums", isAlarm ? "text-[#F25B5B]" : "text-[#4ADE80]")}>
          {count}
        </div>
        <div className="text-xs text-[#8B96A8]">
          {isAlarm ? `last breach ${fmtRelative(lastAt)}` : "no breaches"}
        </div>
      </div>
      <div className="ml-4">
        <div className="text-sm font-semibold text-[#E8EDF2]">Successful Breaches</div>
        <div className="text-xs text-[#8B96A8]">payloads that evaded ingress sanitization</div>
      </div>
    </div>
  );
}

// ── AttemptRow ────────────────────────────────────────────────────────────────

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
        <span className="truncate text-[#8B96A8]">{attempt.sanitizer_detections.join(", ")}</span>
      ) : isBreach ? (
        <span className="text-[#F25B5B]">no patterns detected — evaded</span>
      ) : (
        <span className="text-[#5BB5F2]">clean pass</span>
      )}
      <span className="ml-auto shrink-0 text-[#8B96A8]">{attempt.trace_id.slice(0, 8)}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdversaryPage() {
  const { attempts, breachCount, lastBreachAt, connected, paused, togglePause, clear, totalAttempts } =
    useAdversarialStream();

  const liveSpend = +(totalAttempts * COST_PER_ATTEMPT).toFixed(2);
  const seed7dTotal = SEED_DAILY_COST.reduce((s, v) => s + v, 0);
  const totalSpend = seed7dTotal + liveSpend;

  return (
    <div className="mx-auto max-w-screen-2xl space-y-6 px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono text-lg font-semibold text-[#E8EDF2]">Adversarial Agent Dashboard</h1>
          <p className="mt-0.5 text-xs text-[#8B96A8]">Live feed of attack attempts against the ingress sanitizer</p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <Wifi className="h-4 w-4 text-[#4ADE80]" />
          ) : (
            <WifiOff className="h-4 w-4 text-[#F25B5B]" />
          )}
          <span className="font-mono text-xs text-[#8B96A8]">{connected ? "live" : "disconnected"}</span>
        </div>
      </div>

      {/* Stat strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <HoursSinceBreachCard lastBreachAt={lastBreachAt} />
        <StatCard
          label="Total attempts"
          value={(BASELINE_TOTAL + totalAttempts).toLocaleString()}
          sub={`+${totalAttempts} this session`}
        />
        <StatCard
          label="Successful breaches"
          value={breachCount}
          sub={breachCount > 0 ? `last: ${fmtRelative(lastBreachAt)}` : "none detected"}
          color={breachCount > 0 ? "text-[#F25B5B]" : "text-[#4ADE80]"}
        />
        <StatCard
          label="Est. spend (last 7d)"
          value={`$${totalSpend.toFixed(2)}`}
          sub={`of $${MONTHLY_CAP} cap`}
          color="text-[#E8EDF2]"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <AttemptHistogram attempts={attempts} />
        <CostGraph totalAttempts={totalAttempts} />
      </div>

      {/* Breach counter */}
      <BreachCounter count={breachCount} lastAt={lastBreachAt} />

      {/* Feed controls */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-[#8B96A8]">{attempts.length} attempts</span>
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

      {/* Feed table */}
      <div className="rounded-t-lg border border-b-0 border-[#1E2632] bg-[#0A0E14]">
        <div className="flex gap-3 border-b border-[#1E2632] px-4 py-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">
          <span className="w-20">time</span>
          <span className="w-20">verdict</span>
          <span className="w-6">id</span>
          <span>detections / note</span>
          <span className="ml-auto">trace</span>
        </div>
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
