"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { ChevronUp, ChevronDown, ChevronsUpDown, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import type { MatrixRow, MatrixClass, AttackCategory, PatternId, MatrixStatus, CIResults } from "@/lib/types/showcase";

// ── Derived status ────────────────────────────────────────────────────────────

function rowStatus(r: MatrixRow): MatrixStatus {
  if (r.class !== "LIVE") return "na";
  if (r.successfulCount > 0) return "alert";
  if (r.partialCount > 0) return "warn";
  return "ok";
}

// ── Design constants ──────────────────────────────────────────────────────────

const CLASS_STYLES: Record<MatrixClass, string> = {
  "LIVE":          "border-[#4ADE80]/40 text-[#4ADE80]  bg-[#4ADE80]/8",
  "ARCHITECTURAL": "border-[#5BB5F2]/40 text-[#5BB5F2]  bg-[#5BB5F2]/8",
  "OUT-OF-SCOPE":  "border-[#8B96A8]/30 text-[#8B96A8]  bg-transparent",
};

const STATUS_DOT: Record<MatrixStatus, string> = {
  ok:    "bg-[#4ADE80]",
  warn:  "bg-[#F5B056]",
  alert: "bg-[#F25B5B]",
  na:    "bg-[#3A4452]",
};

const STATUS_LABEL: Record<MatrixStatus, string> = {
  ok: "ok", warn: "warn", alert: "alert", na: "n/a",
};

const PATTERNS: PatternId[] = ["P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11","P12"];

const CATEGORIES: AttackCategory[] = [
  "Prompt/Input","Goal Hijack","Memory","Exfiltration","Tool","Identity",
  "Multi-Agent","Supply Chain","Training","Cascading","Trust","Infra","Weapon","Privacy",
];

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 60)  return `${m}m ago`;
  if (m < 1440) return `${Math.floor(m / 60)}h ago`;
  return `${Math.floor(m / 1440)}d ago`;
}

// ── Sort state ────────────────────────────────────────────────────────────────

type SortKey = "attackId" | "class" | "blockedCount" | "partialCount" | "lastTestedAt";

const CLASS_ORDER: Record<MatrixClass, number> = { "LIVE": 0, "ARCHITECTURAL": 1, "OUT-OF-SCOPE": 2 };

function sortRows(rows: MatrixRow[], key: SortKey, asc: boolean): MatrixRow[] {
  return [...rows].sort((a, b) => {
    let cmp = 0;
    if (key === "attackId")     cmp = a.attackId - b.attackId;
    else if (key === "class")   cmp = CLASS_ORDER[a.class] - CLASS_ORDER[b.class] || a.attackId - b.attackId;
    else if (key === "blockedCount") cmp = (b.blockedCount) - (a.blockedCount);
    else if (key === "partialCount") cmp = (b.partialCount) - (a.partialCount);
    else if (key === "lastTestedAt") {
      const ta = a.lastTestedAt ? new Date(a.lastTestedAt).getTime() : 0;
      const tb = b.lastTestedAt ? new Date(b.lastTestedAt).getTime() : 0;
      cmp = tb - ta;
    }
    return asc ? cmp : -cmp;
  });
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ChipGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly T[];
  value: T | null;
  onChange: (v: T | null) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">{label}</span>
      <button
        type="button"
        onClick={() => onChange(null)}
        className={cn(
          "rounded border px-2 py-0.5 font-mono text-[10px] transition-colors",
          value === null
            ? "border-[#5BB5F2]/60 bg-[#5BB5F2]/10 text-[#5BB5F2]"
            : "border-[#1E2632] text-[#8B96A8] hover:border-[#8B96A8]/40 hover:text-[#A8B4C0]"
        )}
      >
        All
      </button>
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(value === opt ? null : opt)}
          className={cn(
            "rounded border px-2 py-0.5 font-mono text-[10px] transition-colors",
            value === opt
              ? "border-[#5BB5F2]/60 bg-[#5BB5F2]/10 text-[#5BB5F2]"
              : "border-[#1E2632] text-[#8B96A8] hover:border-[#8B96A8]/40 hover:text-[#A8B4C0]"
          )}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

function SortHeader({
  label,
  sortKey,
  current,
  asc,
  onClick,
  className,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  asc: boolean;
  onClick: (k: SortKey) => void;
  className?: string;
}) {
  const active = current === sortKey;
  return (
    <th
      className={cn(
        "cursor-pointer select-none px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-[#8B96A8] transition-colors hover:text-[#A8B4C0]",
        className
      )}
      onClick={() => onClick(sortKey)}
    >
      <span className="flex items-center gap-1">
        {label}
        {active ? (
          asc ? <ChevronUp className="h-2.5 w-2.5" /> : <ChevronDown className="h-2.5 w-2.5" />
        ) : (
          <ChevronsUpDown className="h-2.5 w-2.5 opacity-30" />
        )}
      </span>
    </th>
  );
}

// ── CI Status Bar ─────────────────────────────────────────────────────────────

function CIStatusBar({ ci }: { ci: CIResults }) {
  const unitFailed = ci.unit.failed;
  const intFailed  = ci.integration?.failed ?? 0;
  const anyFailed  = unitFailed + intFailed > 0;

  const unitTotal  = ci.unit.total;
  const intTotal   = ci.integration?.total ?? null;

  const diff = Date.now() - new Date(ci.timestamp).getTime();
  const m = Math.floor(diff / 60_000);
  const ago =
    m < 2    ? "just now"
    : m < 60  ? `${m}m ago`
    : m < 1440 ? `${Math.floor(m / 60)}h ago`
    : `${Math.floor(m / 1440)}d ago`;

  const dotColor  = anyFailed ? "bg-[#F25B5B]" : "bg-[#4ADE80]";
  const textColor = anyFailed ? "text-[#F25B5B]" : "text-[#4ADE80]";
  const label     = anyFailed ? "failing" : "passing";

  const attacksCovered = Object.keys(ci.attack_coverage).length;

  return (
    <div className="flex items-center gap-3 rounded border border-[#1E2632] bg-[#0B1018] px-4 py-2 font-mono text-[10px]">
      <span className={cn("h-1.5 w-1.5 rounded-full flex-shrink-0", dotColor)} />
      <span className="text-[#8B96A8]">CI</span>
      <span className="text-[#E8EDF2]">{ci.branch}</span>
      <span className="text-[#3A4452]">·</span>
      <span className="text-[#8B96A8]">{ago}</span>
      <span className="text-[#3A4452]">·</span>
      <span className="tabular-nums text-[#A8B4C0]">
        {ci.unit.passed}/{unitTotal} unit
        {intTotal !== null && ` · ${ci.integration!.passed}/${intTotal} integration`}
      </span>
      <span className="text-[#3A4452]">·</span>
      <span className={cn("tabular-nums", textColor)}>{label}</span>
      <span className="text-[#3A4452]">·</span>
      <span className="text-[#8B96A8]">{attacksCovered} attack IDs covered</span>
      {ci.commit_short && (
        <>
          <span className="text-[#3A4452]">·</span>
          <span className="text-[#3A4452] tabular-nums">{ci.commit_short}</span>
        </>
      )}
      {ci.run_url && (
        <a
          href={ci.run_url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto flex items-center gap-1 text-[#5BB5F2] hover:text-[#7ECAF5] transition-colors"
        >
          view run <ExternalLink className="h-2.5 w-2.5" />
        </a>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface MatrixShellProps {
  rows: MatrixRow[];
  initialClass?:    MatrixClass    | null;
  initialPattern?:  PatternId      | null;
  initialCategory?: AttackCategory | null;
  ciResults?:       CIResults      | null;
}

export function MatrixShell({ rows, initialClass, initialPattern, initialCategory, ciResults }: MatrixShellProps) {
  const router = useRouter();

  const [classFilter,    setClassFilter]    = useState<MatrixClass    | null>(initialClass    ?? null);
  const [patternFilter,  setPatternFilter]  = useState<PatternId      | null>(initialPattern  ?? null);
  const [categoryFilter, setCategoryFilter] = useState<AttackCategory | null>(initialCategory ?? null);
  const [sortKey,        setSortKey]        = useState<SortKey>("class");
  const [sortAsc,        setSortAsc]        = useState(true);

  function handleSort(k: SortKey) {
    if (sortKey === k) setSortAsc((p) => !p);
    else { setSortKey(k); setSortAsc(true); }
  }

  const filtered = useMemo(() => {
    let r = rows;
    if (classFilter)    r = r.filter((x) => x.class    === classFilter);
    if (patternFilter)  r = r.filter((x) => x.patterns.includes(patternFilter));
    if (categoryFilter) r = r.filter((x) => x.category === categoryFilter);
    return sortRows(r, sortKey, sortAsc);
  }, [rows, classFilter, patternFilter, categoryFilter, sortKey, sortAsc]);

  // Summary stats
  const liveRows     = rows.filter((r) => r.class === "LIVE");
  const totalVariants = liveRows.reduce((s, r) => s + (r.variantCount ?? 0), 0);
  const totalBlocked  = liveRows.reduce((s, r) => s + r.blockedCount,        0);
  const defenseRate   = totalVariants > 0 ? ((totalBlocked / totalVariants) * 100).toFixed(1) : "0";

  return (
    <div className="flex min-h-screen flex-col bg-[#0A0E14]">
      {/* page header */}
      <div className="border-b border-[#1E2632] px-6 py-5">
        <h1 className="font-mono text-sm font-semibold text-[#E8EDF2]">Attack-Defense Matrix</h1>
        <p className="mt-1 font-mono text-[11px] text-[#8B96A8]">
          79 attack categories from the AI threat taxonomy — tested against 12 defense patterns.
        </p>

        {/* summary stats */}
        <div className="mt-4 flex flex-wrap gap-6">
          {[
            { label: "LIVE",           value: liveRows.length,                    color: "#4ADE80" },
            { label: "ARCHITECTURAL",  value: rows.filter(r => r.class === "ARCHITECTURAL").length,  color: "#5BB5F2" },
            { label: "OUT-OF-SCOPE",   value: rows.filter(r => r.class === "OUT-OF-SCOPE").length,   color: "#8B96A8" },
            { label: "DEFENSE RATE",   value: `${defenseRate}%`,                  color: "#4ADE80" },
            { label: "VARIANTS TESTED",value: totalVariants.toLocaleString(),     color: "#E8EDF2" },
          ].map((s) => (
            <div key={s.label}>
              <div className="font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">{s.label}</div>
              <div className="font-mono text-lg font-bold tabular-nums" style={{ color: s.color }}>{s.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* CI status bar */}
      {ciResults && (
        <div className="border-b border-[#1E2632] px-6 py-3">
          <CIStatusBar ci={ciResults} />
        </div>
      )}

      {/* filters */}
      <div className="space-y-2 border-b border-[#1E2632] px-6 py-4">
        <ChipGroup
          label="Class"
          options={["LIVE", "ARCHITECTURAL", "OUT-OF-SCOPE"] as const}
          value={classFilter}
          onChange={setClassFilter}
        />
        <ChipGroup
          label="Pattern"
          options={PATTERNS}
          value={patternFilter}
          onChange={setPatternFilter}
        />
        <ChipGroup
          label="Category"
          options={CATEGORIES}
          value={categoryFilter}
          onChange={setCategoryFilter}
        />
      </div>

      {/* results count */}
      <div className="px-6 py-2">
        <span className="font-mono text-[10px] text-[#8B96A8]">
          {filtered.length} of {rows.length} attacks
        </span>
      </div>

      {/* table */}
      <div className="flex-1 overflow-x-auto px-6 pb-8">
        <table className="w-full min-w-[720px] border-collapse">
          <thead>
            <tr className="border-b border-[#1E2632]">
              <SortHeader label="#"       sortKey="attackId"     current={sortKey} asc={sortAsc} onClick={handleSort} className="w-12" />
              <th className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Name</th>
              <SortHeader label="Class"   sortKey="class"        current={sortKey} asc={sortAsc} onClick={handleSort} className="w-36" />
              <th className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Patterns</th>
              <th className="px-3 py-2 text-right font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Var</th>
              <SortHeader label="Blocked" sortKey="blockedCount" current={sortKey} asc={sortAsc} onClick={handleSort} className="w-20 text-right" />
              <SortHeader label="Partial" sortKey="partialCount" current={sortKey} asc={sortAsc} onClick={handleSort} className="w-20 text-right" />
              <th className="px-3 py-2 text-right font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">False+</th>
              <SortHeader label="Last Run" sortKey="lastTestedAt" current={sortKey} asc={sortAsc} onClick={handleSort} className="w-24" />
              <th className="px-3 py-2 text-center font-mono text-[10px] uppercase tracking-widest text-[#8B96A8] w-16">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => {
              const status = rowStatus(row);
              return (
                <tr
                  key={row.attackId}
                  onClick={() => router.push(`/matrix/${row.attackId}`)}
                  className="cursor-pointer border-b border-[#0F141B] transition-colors hover:bg-[#0F141B]"
                >
                  <td className="px-3 py-2 font-mono text-[11px] tabular-nums text-[#8B96A8]">
                    {row.attackId}
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-mono text-[11px] text-[#E8EDF2]">{row.name}</div>
                    <div className="font-mono text-[9px] text-[#8B96A8]">{row.category}</div>
                  </td>
                  <td className="px-3 py-2">
                    <span className={cn("rounded border px-1.5 py-0.5 font-mono text-[9px]", CLASS_STYLES[row.class])}>
                      {row.class}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-0.5">
                      {row.patterns.length > 0
                        ? row.patterns.map((p) => (
                            <span key={p} className="rounded-sm border border-[#5BB5F2]/20 px-1 py-0.5 font-mono text-[9px] text-[#5BB5F2]/70">
                              {p}
                            </span>
                          ))
                        : <span className="font-mono text-[10px] text-[#3A4452]">—</span>
                      }
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11px] tabular-nums text-[#8B96A8]">
                    {row.variantCount ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11px] tabular-nums text-[#4ADE80]">
                    {row.class === "LIVE" ? row.blockedCount : "—"}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11px] tabular-nums text-[#F5B056]">
                    {row.class === "LIVE" ? (row.partialCount || "—") : "—"}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11px] tabular-nums text-[#8B96A8]">
                    {row.class === "LIVE" ? (row.falsePositiveCount || "—") : "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-[10px] text-[#8B96A8]">
                    {fmt(row.lastTestedAt)}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center justify-center gap-1">
                      <span className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[status])} />
                      <span className="font-mono text-[9px] text-[#8B96A8]">{STATUS_LABEL[status]}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div className="py-16 text-center font-mono text-sm text-[#8B96A8]">
            No attacks match the active filters.
          </div>
        )}
      </div>
    </div>
  );
}
