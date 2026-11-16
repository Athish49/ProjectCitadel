"use client";

import { useState } from "react";
import Link from "next/link";
import { PATTERNS, type Pattern } from "@/lib/data/patterns";
import { ATTACK_NAMES } from "@/lib/data/matrix";
import styles from "./patterns.module.css";

function PatternRow({
  p,
  active,
  onClick,
}: {
  p: Pattern;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={styles.patRow}
      style={{
        background: active ? "#131417" : "transparent",
        boxShadow: `inset 2px 0 0 ${active ? "#f4f4f5" : "transparent"}`,
      }}
    >
      <span className="mono" style={{ fontSize: "12px", color: "rgba(255,255,255,0.55)", width: "28px" }}>
        {p.id}
      </span>
      <span
        style={{
          flexGrow: 1,
          fontSize: "15px",
          fontWeight: 500,
          color: active ? "#ffffff" : "rgba(255,255,255,0.75)",
        }}
      >
        {p.name}
      </span>
      <span className="mono" style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.55)" }}>
        {p.defeats.length} ↓
      </span>
    </button>
  );
}

function DetailPanel({ p, flip }: { p: Pattern; flip: number }) {
  const defeatChips = p.defeats.map((id) => ({ id, name: ATTACK_NAMES[id] ?? "" }));

  return (
    <div
      key={flip}
      className={flip % 2 ? styles.swapA : styles.swapB}
      style={{
        flex: "2.2 1 520px",
        minWidth: 0,
        padding: "clamp(24px,3vw,40px)",
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", gap: "6px 16px" }}>
        <span className="mono" style={{ fontSize: "13px", color: "rgba(255,255,255,0.55)" }}>
          {p.id}
        </span>
        <h2
          style={{
            margin: 0,
            fontSize: "clamp(26px,3vw,38px)",
            lineHeight: 1.1,
            letterSpacing: "-0.03em",
            fontWeight: 600,
          }}
        >
          {p.name}
        </h2>
      </div>

      <div className="eb" style={{ marginTop: "30px", fontSize: "11px" }}>
        The problem
      </div>
      <p
        style={{
          margin: "10px 0 0",
          fontSize: "clamp(18px,1.7vw,21px)",
          lineHeight: 1.4,
          letterSpacing: "-0.01em",
          maxWidth: "680px",
        }}
      >
        {p.problem}
      </p>

      <div className="eb" style={{ marginTop: "28px", fontSize: "11px" }}>
        The shape
      </div>
      <p style={{ margin: "10px 0 0", fontSize: "15.5px", color: "rgba(255,255,255,0.75)", maxWidth: "680px" }}>
        {p.shape}
      </p>

      {p.code && (
        <pre
          className="mono"
          style={{
            margin: "18px 0 0",
            padding: "14px 16px",
            fontSize: "12.5px",
            lineHeight: 1.7,
            whiteSpace: "pre-wrap",
            background: "#08090a",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "4px",
            color: "rgba(255,255,255,0.85)",
          }}
        >
          {p.code}
        </pre>
      )}

      <div className="eb" style={{ marginTop: "28px", fontSize: "11px" }}>
        Defeats {p.defeats.length} attack classes
      </div>
      <div style={{ marginTop: "12px", display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {defeatChips.map(({ id, name }) => (
          <Link key={id} href={`/matrix#a${id}`} className={styles.patPill}>
            <span className="mono" style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.55)" }}>
              #{id}
            </span>
            {name}
          </Link>
        ))}
      </div>

      <div
        style={{
          marginTop: "32px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))",
          gap: "1px",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="cell" style={{ padding: "18px 18px 20px" }}>
          <div className="eb" style={{ fontSize: "11px" }}>
            Implementation
          </div>
          <div className="mono" style={{ marginTop: "10px", fontSize: "12.5px", color: "rgba(255,255,255,0.9)", overflowWrap: "anywhere" }}>
            {p.codeRef}
          </div>
          <div className="mono" style={{ marginTop: "6px", fontSize: "12px", color: "rgba(255,255,255,0.58)", overflowWrap: "anywhere" }}>
            {p.testRef}
          </div>
        </div>
        <div className="cell" style={{ padding: "18px 18px 20px" }}>
          <div className="eb" style={{ fontSize: "11px", color: "#e2a336" }}>
            Residual risk
          </div>
          <div style={{ marginTop: "10px", fontSize: "14px", color: "rgba(255,255,255,0.8)" }}>{p.risk}</div>
        </div>
      </div>
      <div className="mono" style={{ marginTop: "16px", fontSize: "12px", color: "rgba(255,255,255,0.58)" }}>
        {p.ref}
      </div>
    </div>
  );
}

export function PatternExplorer() {
  const [sel, setSel] = useState(0);
  const [flip, setFlip] = useState(0);
  const selected = PATTERNS[sel];

  return (
    <div data-rv className="panel" style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-start" }}>
      <div
        role="tablist"
        aria-label="Patterns"
        style={{ flex: "1 1 300px", minWidth: 0, borderRight: "1px solid rgba(255,255,255,0.08)" }}
      >
        {PATTERNS.map((p, i) => (
          <PatternRow
            key={p.id}
            p={p}
            active={i === sel}
            onClick={() => {
              setSel(i);
              setFlip((f) => f + 1);
            }}
          />
        ))}
      </div>

      <DetailPanel p={selected} flip={flip} />
    </div>
  );
}
