"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { PATTERNS, type Pattern } from "@/lib/data/patterns";
import { ATTACK_NAMES } from "@/lib/data/matrix";

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace" };

function PatternListCard({
  p,
  active,
  onClick,
}: {
  p: Pattern;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div
      id={p.id}
      className="pattern-card"
      onClick={onClick}
      style={{
        border: `1px solid ${active ? "rgba(62,207,142,0.5)" : "rgba(255,255,255,0.09)"}`,
        background: active ? "rgba(62,207,142,0.07)" : "#0B0C0E",
        padding: "16px 18px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "10px",
        transition: "border-color 0.15s ease, background 0.15s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", gap: "12px", minWidth: 0 }}>
        <span
          style={{
            ...mono,
            fontSize: "12.5px",
            fontWeight: 600,
            color: active ? "#3ECF8E" : "rgba(255,255,255,0.42)",
            flexShrink: 0,
          }}
        >
          {p.id}
        </span>
        <span
          style={{
            fontSize: "14.5px",
            fontWeight: 600,
            color: "rgba(255,255,255,0.92)",
            letterSpacing: "-0.005em",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {p.name}
        </span>
      </div>
      <span style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.35)", flexShrink: 0 }}>
        {p.defeats.length}↓
      </span>
    </div>
  );
}

function DetailPanel({ p }: { p: Pattern }) {
  const defeatChips = p.defeats.map((id) => ({
    id,
    name: ATTACK_NAMES[id] ?? `Attack #${id}`,
  }));

  const references = p.citation.split(";").map((c) => c.trim());

  return (
    <div
      style={{
        border: "1px solid rgba(62,207,142,0.3)",
        background: "#0C0D0F",
        padding: "36px 38px",
        display: "flex",
        flexDirection: "column",
        gap: "22px",
      }}
    >
      {/* Header */}
      <div>
        <div style={{ display: "flex", alignItems: "baseline", gap: "14px" }}>
          <span style={{ ...mono, fontSize: "22px", fontWeight: 700, color: "#3ECF8E" }}>
            {p.id}
          </span>
          <span
            style={{
              fontSize: "24px",
              fontWeight: 600,
              color: "rgba(255,255,255,0.97)",
              letterSpacing: "-0.015em",
            }}
          >
            {p.name}
          </span>
        </div>
        <div
          style={{
            marginTop: "12px",
            fontSize: "15px",
            lineHeight: 1.6,
            color: "rgba(255,255,255,0.6)",
            maxWidth: "760px",
          }}
        >
          {p.problem}
        </div>
      </div>

      {/* Key insight */}
      <div
        style={{
          border: "1px solid rgba(62,207,142,0.28)",
          background: "rgba(62,207,142,0.05)",
          padding: "18px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div
          style={{
            ...mono,
            fontSize: "10.5px",
            letterSpacing: "0.1em",
            color: "#3ECF8E",
          }}
        >
          THE KEY INSIGHT
        </div>
        <div style={{ fontSize: "14px", lineHeight: 1.65, color: "rgba(255,255,255,0.82)" }}>
          {p.shape}
        </div>
      </div>

      {/* What it defeats */}
      <div>
        <div
          style={{
            ...mono,
            fontSize: "10.5px",
            letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.4)",
            marginBottom: "10px",
          }}
        >
          WHAT IT DEFEATS · {p.defeats.length} ATTACK CLASSES
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {defeatChips.map(({ id, name }) => (
            <Link
              key={id}
              href={`/matrix#a${id}`}
              style={{
                ...mono,
                fontSize: "12px",
                color: "rgba(255,255,255,0.7)",
                border: "1px solid rgba(255,255,255,0.14)",
                padding: "6px 12px",
                borderRadius: "999px",
                whiteSpace: "nowrap",
                textDecoration: "none",
                transition: "border-color 0.12s, color 0.12s",
              }}
              className="defeat-chip"
            >
              <span style={{ color: "#3ECF8E" }}>#{id}</span> {name}
            </Link>
          ))}
        </div>
      </div>

      {/* Implementation + Residual */}
      <div
        data-impl-grid=""
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}
      >
        {/* Implementation */}
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.1)",
            padding: "16px 18px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div
            style={{
              ...mono,
              fontSize: "10.5px",
              letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            IMPLEMENTATION
          </div>
          {p.snippet && (
            <div
              style={{
                background: "#08090A",
                border: "1px solid rgba(255,255,255,0.08)",
                padding: "12px",
                ...mono,
                fontSize: "11.5px",
                lineHeight: 1.6,
                color: "rgba(255,255,255,0.6)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {p.snippet}
            </div>
          )}
          <div style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.55)" }}>
            <span style={{ color: "rgba(255,255,255,0.35)" }}>code </span>
            {p.codeRef}
          </div>
          <div style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.55)" }}>
            <span style={{ color: "rgba(255,255,255,0.35)" }}>test </span>
            {p.testRef}
          </div>
        </div>

        {/* Residual risk */}
        <div
          style={{
            border: "1px solid rgba(226,163,54,0.3)",
            padding: "16px 18px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div
            style={{
              ...mono,
              fontSize: "10.5px",
              letterSpacing: "0.1em",
              color: "#E2A336",
            }}
          >
            RESIDUAL RISK · HONEST
          </div>
          <div style={{ fontSize: "13.5px", lineHeight: 1.6, color: "rgba(255,255,255,0.72)" }}>
            {p.residual}
          </div>
        </div>
      </div>

      {/* References */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "18px" }}>
        <div
          style={{
            ...mono,
            fontSize: "10.5px",
            letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.4)",
            marginBottom: "10px",
          }}
        >
          REFERENCES
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {references.map((ref, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: "8px",
                fontSize: "13px",
                color: "rgba(255,255,255,0.55)",
              }}
            >
              <span style={{ color: "#3ECF8E", fontSize: "11px" }}>▸</span>
              {ref}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function PatternExplorer() {
  const [selectedId, setSelectedId] = useState("P1");

  /* URL hash deep-link on mount */
  useEffect(() => {
    const m = /^#(P\d+)$/.exec(window.location.hash);
    if (m && PATTERNS.some((p) => p.id === m[1])) {
      setSelectedId(m[1]);
      setTimeout(() => {
        const el = document.getElementById(m[1]);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 80);
    }
  }, []);

  const selected = PATTERNS.find((p) => p.id === selectedId) ?? PATTERNS[0];

  return (
    <div
      data-pattern-explorer=""
      style={{
        display: "grid",
        gridTemplateColumns: "320px 1fr",
        gap: "20px",
        alignItems: "start",
      }}
    >
      {/* Pattern list */}
      <div
        data-pattern-list=""
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          position: "sticky",
          top: "76px",
        }}
      >
        {PATTERNS.map((p) => (
          <PatternListCard
            key={p.id}
            p={p}
            active={p.id === selectedId}
            onClick={() => setSelectedId(p.id)}
          />
        ))}
      </div>

      {/* Detail panel */}
      <DetailPanel p={selected} />
    </div>
  );
}
