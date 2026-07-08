"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  MATRIX_ROWS,
  CATEGORIES,
  PATTERN_META,
  type MatrixRow,
} from "@/lib/data/matrix";

const CLASS_FILTERS = ["ALL", "LIVE", "ARCH", "OOS"] as const;
const PATTERN_FILTERS = [
  "ALL", "P1", "P2", "P3", "P4", "P5", "P6",
  "P7", "P8", "P9", "P10", "P11", "P12",
] as const;

const CLS_COLOR: Record<string, string> = {
  LIVE: "#3ECF8E",
  ARCH: "#5FA8A0",
  OOS:  "rgba(255,255,255,0.35)",
};

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace" };

function Pill({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        ...mono,
        background: active ? "rgba(255,255,255,0.95)" : "transparent",
        color: active ? "#0A0B0C" : "rgba(255,255,255,0.6)",
        border: `1px solid ${active ? "transparent" : "rgba(255,255,255,0.14)"}`,
        fontSize: "11.5px",
        fontWeight: 600,
        padding: "6px 11px",
        borderRadius: "5px",
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "all 0.12s",
        flexShrink: 0,
      }}
    >
      {label}
    </button>
  );
}

function ClsBadge({ cls }: { cls: "LIVE" | "ARCH" | "OOS" }) {
  return (
    <span
      style={{
        ...mono,
        fontSize: "10.5px",
        fontWeight: 700,
        letterSpacing: "0.06em",
        color: CLS_COLOR[cls],
        border: `1px solid ${CLS_COLOR[cls]}`,
        borderRadius: "4px",
        padding: "2px 6px",
        opacity: cls === "OOS" ? 0.6 : 1,
      }}
    >
      {cls}
    </span>
  );
}

function PatternChip({ p }: { p: string }) {
  const meta = PATTERN_META[p];
  if (!meta) return null;
  return (
    <Link
      href={`/patterns#${p}`}
      style={{
        ...mono,
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        fontSize: "11px",
        padding: "4px 9px",
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.10)",
        borderRadius: "5px",
        color: "rgba(255,255,255,0.75)",
        textDecoration: "none",
        transition: "background 0.12s, color 0.12s",
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ color: "#5FA8A0", fontWeight: 700 }}>{p}</span>
      <span>·</span>
      <span>{meta.name}</span>
    </Link>
  );
}

function ExpandedPanel({ row }: { row: MatrixRow }) {
  return (
    <div
      style={{
        gridColumn: "1 / -1",
        padding: "18px 20px 22px",
        background: "rgba(255,255,255,0.018)",
        borderTop: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* top row: defenses + run + refs */}
      <div style={{ display: "flex", gap: "32px", flexWrap: "wrap", marginBottom: "18px" }}>
        {/* DEFENSES */}
        {row.patterns.length > 0 && (
          <div style={{ minWidth: "200px", flex: "1 1 200px" }}>
            <div
              style={{
                ...mono,
                fontSize: "10px",
                letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.35)",
                marginBottom: "8px",
              }}
            >
              DEFENSES
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {row.patterns.map((p) => (
                <PatternChip key={p} p={p} />
              ))}
            </div>
          </div>
        )}

        {/* RUN */}
        <div style={{ minWidth: "200px", flex: "1 1 240px" }}>
          <div
            style={{
              ...mono,
              fontSize: "10px",
              letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: "8px",
            }}
          >
            RUN
          </div>
          <div
            style={{
              ...mono,
              fontSize: "12px",
              color: "rgba(255,255,255,0.55)",
              lineHeight: 1.55,
            }}
          >
            {row.runSummary}
          </div>
        </div>

        {/* REFERENCES */}
        <div style={{ minWidth: "200px", flex: "1 1 200px" }}>
          <div
            style={{
              ...mono,
              fontSize: "10px",
              letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: "8px",
            }}
          >
            REFERENCES
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <div style={{ display: "flex", gap: "8px", alignItems: "baseline" }}>
              <span style={{ ...mono, fontSize: "10px", color: "rgba(255,255,255,0.3)", flexShrink: 0 }}>code</span>
              <span style={{ ...mono, fontSize: "12px", color: "#5FA8A0", wordBreak: "break-all" }}>{row.codeRef}</span>
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "baseline" }}>
              <span style={{ ...mono, fontSize: "10px", color: "rgba(255,255,255,0.3)", flexShrink: 0 }}>test</span>
              <span style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.5)", wordBreak: "break-all" }}>{row.testRef}</span>
            </div>
          </div>
        </div>
      </div>

      {/* sample payload */}
      <div>
        <div
          style={{
            ...mono,
            fontSize: "10px",
            letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.35)",
            marginBottom: "8px",
          }}
        >
          {row.sampleLabel}
        </div>
        <div
          style={{
            ...mono,
            fontSize: "12.5px",
            color: row.cls === "LIVE" ? "rgba(255,255,255,0.75)" : "rgba(255,255,255,0.45)",
            background: "rgba(0,0,0,0.25)",
            border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: "5px",
            padding: "12px 14px",
            lineHeight: 1.6,
          }}
        >
          {row.samplePayload}
        </div>
      </div>
    </div>
  );
}

function TableRow({
  row,
  expanded,
  onToggle,
}: {
  row: MatrixRow;
  expanded: boolean;
  onToggle: () => void;
}) {
  const numVal = (n: number | null, dash = "—") => (n === null ? dash : String(n));

  return (
    <>
      {/* main row */}
      <div
        id={`a${row.id}`}
        data-row-grid=""
        className="matrix-row"
        onClick={onToggle}
        style={{
          display: "grid",
          gridTemplateColumns: "44px 1fr 90px 100px 70px 78px 64px 92px",
          alignItems: "center",
          padding: "0 20px",
          minHeight: "52px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          cursor: "pointer",
          background: expanded ? "rgba(255,255,255,0.025)" : "transparent",
          transition: "background 0.1s",
        }}
      >
        {/* # */}
        <span
          style={{
            ...mono,
            fontSize: "12px",
            color: "rgba(255,255,255,0.28)",
          }}
        >
          {row.id}
        </span>

        {/* name + cat */}
        <div style={{ display: "flex", flexDirection: "column", gap: "2px", paddingRight: "12px" }}>
          <span style={{ fontSize: "13.5px", color: "rgba(255,255,255,0.88)", fontWeight: 450 }}>
            {row.name}
          </span>
          <span style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.32)" }}>
            {row.catShort}
          </span>
        </div>

        {/* class */}
        <span>
          <ClsBadge cls={row.cls} />
        </span>

        {/* patterns */}
        <span data-col-patterns="" style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
          {row.patterns.map((p) => (
            <span
              key={p}
              onClick={(e) => e.stopPropagation()}
            >
              <Link
                href={`/patterns#${p}`}
                style={{
                  ...mono,
                  fontSize: "10.5px",
                  color: "#5FA8A0",
                  padding: "2px 5px",
                  background: "rgba(95,168,160,0.08)",
                  borderRadius: "3px",
                  textDecoration: "none",
                }}
              >
                {p}
              </Link>
            </span>
          ))}
          {row.patterns.length === 0 && (
            <span style={{ ...mono, fontSize: "11px", color: "rgba(255,255,255,0.2)" }}>—</span>
          )}
        </span>

        {/* tried */}
        <span
          data-col-tried=""
          style={{
            ...mono,
            fontSize: "12.5px",
            color: row.cls === "LIVE" ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.2)",
            textAlign: "right",
          }}
        >
          {numVal(row.tried, row.cls === "LIVE" ? "—" : "n/a")}
        </span>

        {/* blocked */}
        <span
          style={{
            ...mono,
            fontSize: "12.5px",
            fontWeight: 600,
            color: row.cls === "LIVE" ? "#3ECF8E" : "rgba(255,255,255,0.2)",
            textAlign: "right",
          }}
        >
          {row.cls === "LIVE" ? numVal(row.blocked) : "n/a"}
        </span>

        {/* partial */}
        <span
          data-col-partial=""
          style={{
            ...mono,
            fontSize: "12.5px",
            color:
              row.cls === "LIVE" && (row.partial ?? 0) > 0
                ? "#E2A336"
                : "rgba(255,255,255,0.2)",
            textAlign: "right",
          }}
        >
          {row.cls === "LIVE" ? numVal(row.partial) : "n/a"}
        </span>

        {/* last run */}
        <span
          data-col-lastrun=""
          style={{
            ...mono,
            fontSize: "11px",
            color: "rgba(255,255,255,0.32)",
            textAlign: "right",
          }}
        >
          {row.cls === "LIVE" ? row.lastRun : "—"}
        </span>
      </div>

      {/* expanded panel */}
      {expanded && (
        <div
          style={{
            display: "grid",
            gridColumn: "1 / -1",
          }}
        >
          <ExpandedPanel row={row} />
        </div>
      )}
    </>
  );
}

export function MatrixTable() {
  const [classFilter, setClassFilter] = useState<"ALL" | "LIVE" | "ARCH" | "OOS">("ALL");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [patternFilter, setPatternFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  /* open row from URL hash on mount */
  useEffect(() => {
    const m = /^#a(\d+)$/.exec(window.location.hash);
    if (m) {
      const id = parseInt(m[1], 10);
      setExpandedId(id);
      setTimeout(() => {
        const el = document.getElementById(`a${id}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 80);
    }
  }, []);

  const q = search.trim().toLowerCase();

  const filtered = MATRIX_ROWS.filter((r) => {
    if (classFilter !== "ALL" && r.cls !== classFilter) return false;
    if (categoryFilter !== "all" && String(r.cat) !== categoryFilter) return false;
    if (patternFilter !== "ALL" && !r.patterns.includes(patternFilter)) return false;
    if (q && !r.name.toLowerCase().includes(q) && !String(r.id).includes(q)) return false;
    return true;
  });

  function toggle(id: number) {
    setExpandedId((prev) => (prev === id ? null : id));
    if (expandedId !== id) {
      setTimeout(() => {
        const el = document.getElementById(`a${id}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 60);
    }
  }

  return (
    <div style={{ marginTop: "28px" }}>
      {/* Filter bar */}
      <div
        data-filter-bar=""
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          padding: "18px 20px",
          background: "#0B0C0E",
          border: "1px solid rgba(255,255,255,0.07)",
          borderBottom: "none",
        }}
      >
        {/* CLASS row */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <span
            style={{
              ...mono,
              fontSize: "10px",
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.3)",
              width: "64px",
              flexShrink: 0,
            }}
          >
            CLASS
          </span>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {CLASS_FILTERS.map((f) => (
              <Pill
                key={f}
                label={f}
                active={classFilter === f}
                onClick={() => setClassFilter(f)}
              />
            ))}
          </div>
        </div>

        {/* PATTERN row */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <span
            style={{
              ...mono,
              fontSize: "10px",
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.3)",
              width: "64px",
              flexShrink: 0,
            }}
          >
            PATTERN
          </span>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {PATTERN_FILTERS.map((f) => (
              <Pill
                key={f}
                label={f}
                active={patternFilter === f}
                onClick={() => setPatternFilter(f)}
              />
            ))}
          </div>
        </div>

        {/* CATEGORY row */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <span
            style={{
              ...mono,
              fontSize: "10px",
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.3)",
              width: "64px",
              flexShrink: 0,
            }}
          >
            CATEGORY
          </span>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            <Pill
              label="All"
              active={categoryFilter === "all"}
              onClick={() => setCategoryFilter("all")}
            />
            {CATEGORIES.map((c) => (
              <Pill
                key={c.n}
                label={c.short}
                active={categoryFilter === String(c.n)}
                onClick={() => setCategoryFilter(String(c.n))}
              />
            ))}
          </div>
        </div>

        {/* search + result count */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
          <input
            type="text"
            placeholder="Search attacks…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              ...mono,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.10)",
              borderRadius: "5px",
              color: "rgba(255,255,255,0.85)",
              fontSize: "12.5px",
              padding: "7px 12px",
              width: "220px",
              outline: "none",
            }}
          />
          <span style={{ ...mono, fontSize: "11.5px", color: "rgba(255,255,255,0.35)" }}>
            {filtered.length} / {MATRIX_ROWS.length} attacks
          </span>
        </div>
      </div>

      {/* Table */}
      <div
        style={{
          border: "1px solid rgba(255,255,255,0.07)",
          overflow: "hidden",
        }}
      >
        {/* header */}
        <div
          data-row-grid=""
          style={{
            display: "grid",
            gridTemplateColumns: "44px 1fr 90px 100px 70px 78px 64px 92px",
            alignItems: "center",
            padding: "0 20px",
            height: "40px",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            background: "#0B0C0E",
          }}
        >
          <span style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em" }}>#</span>
          <span style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em" }}>ATTACK</span>
          <span style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em" }}>CLASS</span>
          <span data-col-patterns="" style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em" }}>PATTERNS</span>
          <span data-col-tried="" style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em", textAlign: "right" }}>TRIED</span>
          <span style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em", textAlign: "right" }}>BLOCKED</span>
          <span data-col-partial="" style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em", textAlign: "right" }}>PARTIAL</span>
          <span data-col-lastrun="" style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.3)", letterSpacing: "0.06em", textAlign: "right" }}>LAST RUN</span>
        </div>

        {/* rows */}
        {filtered.length === 0 ? (
          <div
            style={{
              padding: "48px 20px",
              textAlign: "center",
              ...mono,
              fontSize: "13px",
              color: "rgba(255,255,255,0.3)",
            }}
          >
            No attacks match the current filters.
          </div>
        ) : (
          filtered.map((row) => (
            <TableRow
              key={row.id}
              row={row}
              expanded={expandedId === row.id}
              onToggle={() => toggle(row.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
