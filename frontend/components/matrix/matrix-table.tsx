"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import styles from "./matrix.module.css";
import {
  MATRIX_ROWS,
  CATEGORIES,
  PATTERN_NAMES,
  CLASS_TIP,
  TOTAL_COUNT,
  type MatrixRow,
  type AttackClass,
} from "@/lib/data/matrix";

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace" };

function Pill({
  name,
  tip,
  on,
  onClick,
}: {
  name: string;
  tip: string;
  on: boolean;
  onClick: () => void;
}) {
  return (
    <button
      className={`pick ${styles.pill}`}
      type="button"
      onClick={onClick}
      aria-pressed={on}
      title={tip}
      style={{
        background: on ? "#f4f4f5" : "transparent",
        color: on ? "#0a0b0c" : "rgba(255,255,255,0.85)",
        borderColor: on ? "#f4f4f5" : "rgba(255,255,255,0.12)",
      }}
    >
      {name}
    </button>
  );
}

function MatrixRowView({
  row,
  open,
  onToggle,
}: {
  row: MatrixRow;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      id={"a" + row.id}
      style={{
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        background: open ? "#101113" : "transparent",
      }}
    >
      <button
        className={styles.mrow}
        type="button"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.55)" }}>
          {row.num}
        </span>
        <span>
          <span style={{ display: "block", fontSize: "14.5px" }}>{row.name}</span>
          <span style={{ display: "block", fontSize: "12px", color: "rgba(255,255,255,0.55)" }}>
            {row.catName}
          </span>
          <span
            style={{
              display: "block",
              marginTop: "2px",
              fontSize: "12px",
              lineHeight: 1.4,
              color: "rgba(255,255,255,0.45)",
            }}
          >
            {row.description}
          </span>
        </span>
        <span
          style={{
            ...mono,
            fontSize: "11.5px",
            letterSpacing: "0.08em",
            color: row.clsColor,
          }}
        >
          {row.cls}
        </span>
        <span className={styles.colPatterns} style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.75)" }}>
          {row.patternsText}
        </span>
        <span
          className={styles.colTried}
          style={{
            ...mono,
            fontSize: "12.5px",
            textAlign: "right",
            fontVariantNumeric: "tabular-nums",
            color: "rgba(255,255,255,0.85)",
          }}
        >
          {row.tried}
        </span>
        <span
          className={styles.colBlocked}
          style={{
            ...mono,
            fontSize: "12.5px",
            textAlign: "right",
            fontVariantNumeric: "tabular-nums",
            color: "rgba(255,255,255,0.85)",
          }}
        >
          {row.blocked}
        </span>
        <span
          className={styles.colPartial}
          style={{
            ...mono,
            fontSize: "12.5px",
            textAlign: "right",
            fontVariantNumeric: "tabular-nums",
            color: row.partialColor,
          }}
        >
          {row.partial}
        </span>
      </button>

      {open && (
        <div className={styles.openPanel}>
          <div>
            <div className="eb" style={{ fontSize: "11px" }}>What it is</div>
            <div style={{ marginTop: "8px", fontSize: "14px", color: "rgba(255,255,255,0.75)" }}>
              {row.description}
            </div>
            <div className="eb" style={{ marginTop: "18px", fontSize: "11px" }}>Defenses</div>
            <div style={{ marginTop: "8px", fontSize: "14px" }}>{row.defs}</div>
            <div className="eb" style={{ marginTop: "18px", fontSize: "11px" }}>Run</div>
            <div style={{ marginTop: "8px", fontSize: "14px", color: "rgba(255,255,255,0.75)" }}>
              {row.run}
            </div>
            <div
              style={{
                ...mono,
                marginTop: "10px",
                fontSize: "12px",
                color: "rgba(255,255,255,0.58)",
                overflowWrap: "anywhere",
              }}
            >
              {row.test}
            </div>
          </div>
          <div>
            <div className="eb" style={{ fontSize: "11px" }}>{row.panelTitle}</div>
            <div
              style={{
                ...mono,
                marginTop: "8px",
                padding: "12px 14px",
                fontSize: "12.5px",
                lineHeight: 1.6,
                background: "#08090a",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "4px",
                color: "rgba(255,255,255,0.85)",
              }}
            >
              {row.panelText}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function MatrixTable() {
  const [cls, setCls] = useState<"ALL" | AttackClass>("ALL");
  const [pat, setPat] = useState<string>("");
  const [cat, setCat] = useState<string>("");
  const [q, setQ] = useState<string>("");
  const [open, setOpen] = useState<number>(-1);
  const hashHandled = useRef(false);

  // Deep-link support: /matrix#a{id} (linked from the Patterns page) opens
  // and scrolls to the matching row. Runs once on mount, after any filters
  // reset to their defaults, so the row is never hidden by a stale filter.
  useEffect(() => {
    if (hashHandled.current) return;
    hashHandled.current = true;
    const match = window.location.hash.match(/^#a(\d+)$/);
    if (!match) return;
    const id = Number(match[1]);
    if (!MATRIX_ROWS.some((r) => r.id === id)) return;
    setCls("ALL");
    setPat("");
    setCat("");
    setQ("");
    setOpen(id);
  }, []);

  useEffect(() => {
    if (open === -1) return;
    const match = window.location.hash.match(/^#a(\d+)$/);
    if (!match || Number(match[1]) !== open) return;
    const timer = window.setTimeout(() => {
      document.getElementById("a" + open)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 60);
    return () => window.clearTimeout(timer);
  }, [open]);

  const query = q.trim().toLowerCase();

  const rows = useMemo(() => {
    return MATRIX_ROWS.filter((r) => {
      if (cls !== "ALL" && r.cls !== cls) return false;
      if (pat && !r.patterns.includes("P" + pat)) return false;
      if (cat && r.cat !== +cat) return false;
      if (query && !r.name.toLowerCase().includes(query) && String(r.id) !== query) return false;
      return true;
    });
  }, [cls, pat, cat, query]);

  const filtered = cls !== "ALL" || !!pat || !!cat || !!q;

  function clear() {
    setCls("ALL");
    setPat("");
    setCat("");
    setQ("");
    setOpen(-1);
  }

  function toggle(id: number) {
    setOpen((prev) => (prev === id ? -1 : id));
  }

  return (
    <>
      {/* Filter bar */}
      <div className="panel" style={{ padding: "22px 22px 20px", display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 20px", alignItems: "flex-start" }}>
          <span className="eb" style={{ flex: "0 0 84px", fontSize: "11px", lineHeight: "44px" }}>Class</span>
          <div style={{ flex: "1 1 300px", minWidth: 0, display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {(["ALL", "LIVE", "ARCH", "OOS"] as const).map((c) => (
              <Pill key={c} name={c} tip={CLASS_TIP[c]} on={cls === c} onClick={() => { setCls(c); setOpen(-1); }} />
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 20px", alignItems: "flex-start" }}>
          <span className="eb" style={{ flex: "0 0 84px", fontSize: "11px", lineHeight: "44px" }}>Pattern</span>
          <div style={{ flex: "1 1 300px", minWidth: 0, display: "flex", flexWrap: "wrap", gap: "8px" }}>
            <Pill name="ALL" tip="All patterns" on={!pat} onClick={() => { setPat(""); setOpen(-1); }} />
            {PATTERN_NAMES.map((n, i) => (
              <Pill
                key={i}
                name={"P" + (i + 1)}
                tip={n}
                on={pat === String(i + 1)}
                onClick={() => { setPat(String(i + 1)); setOpen(-1); }}
              />
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 20px", alignItems: "flex-start" }}>
          <span className="eb" style={{ flex: "0 0 84px", fontSize: "11px", lineHeight: "44px" }}>Category</span>
          <div style={{ flex: "1 1 300px", minWidth: 0, display: "flex", flexWrap: "wrap", gap: "8px" }}>
            <Pill name="All" tip="All categories" on={!cat} onClick={() => { setCat(""); setOpen(-1); }} />
            {CATEGORIES.map((c) => (
              <Pill
                key={c.n}
                name={c.short}
                tip={c.name}
                on={cat === String(c.n)}
                onClick={() => { setCat(String(c.n)); setOpen(-1); }}
              />
            ))}
          </div>
        </div>

        <div
          style={{
            marginTop: "8px",
            paddingTop: "18px",
            borderTop: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            flexWrap: "wrap",
            gap: "10px 16px",
            alignItems: "center",
          }}
        >
          <label style={{ flex: "0 1 340px", display: "flex" }}>
            <span style={{ position: "absolute", left: "-9999px" }}>Search attacks</span>
            <input
              className={`${styles.fld} mono`}
              type="search"
              placeholder="Search attacks…"
              value={q}
              onChange={(e) => { setQ(e.target.value); setOpen(-1); }}
              style={{ width: "100%", fontSize: "13px" }}
            />
          </label>
          {filtered && (
            <button className={`pick ${styles.pill}`} type="button" onClick={clear} style={{ color: "rgba(255,255,255,0.85)" }}>
              Clear filters
            </button>
          )}
          <span style={{ ...mono, marginLeft: "auto", fontSize: "13px", color: "rgba(255,255,255,0.62)" }}>
            {rows.length} / {TOTAL_COUNT} attacks
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="panel" style={{ marginTop: "-1px", overflowX: "auto" }}>
        <div style={{ minWidth: "820px" }}>
          <div className={`eb ${styles.headerGrid}`}>
            <span>#</span>
            <span>Attack</span>
            <span>Class</span>
            <span className={styles.colPatterns}>Patterns</span>
            <span className={styles.colTried} style={{ textAlign: "right" }}>Tried</span>
            <span className={styles.colBlocked} style={{ textAlign: "right" }}>Blocked</span>
            <span className={styles.colPartial} style={{ textAlign: "right" }}>Partial</span>
          </div>

          {rows.map((r) => (
            <MatrixRowView key={r.id} row={r} open={open === r.id} onToggle={() => toggle(r.id)} />
          ))}

          {rows.length === 0 && (
            <div style={{ ...mono, padding: "28px 18px", fontSize: "13px", color: "rgba(255,255,255,0.6)" }}>
              No attacks match the current filters.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
