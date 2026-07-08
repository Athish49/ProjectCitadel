"use client";

import Link from "next/link";
import { Reveal } from "./reveal";
import { MATRIX_ROWS } from "@/lib/data/home";

export function MatrixSection() {
  return (
    <section
      id="matrix"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        4.0 — ATTACK–DEFENSE MATRIX
      </Reveal>

      <Reveal
        style={{
          margin: "18px 0 0",
          fontSize: "clamp(30px, 3vw, 42px)",
          lineHeight: 1.16,
          letterSpacing: "-0.028em",
          fontWeight: 600,
          maxWidth: "940px",
        }}
      >
        <span style={{ color: "rgba(255,255,255,0.97)" }}>79 attack classes. Numbers, never adjectives.</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}Every row links to the payloads tried, the code that blocked them, and the test that proves it.
        </span>
      </Reveal>

      {/* stats grid */}
      <Reveal
        data-mstats-grid
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "1px",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.08)",
          marginTop: "56px",
        }}
      >
        <div style={{ background: "#0B0C0E", padding: "20px 24px" }}>
          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "28px", fontWeight: 600,
              color: "rgba(255,255,255,0.95)",
            }}
          >
            43{" "}
            <span style={{ fontSize: "13px", color: "#3ECF8E" }}>LIVE</span>
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.45)", marginTop: "6px" }}>
            Automated suites with real payloads. Block rates, partial leaks and false positives published per run.
          </div>
        </div>
        <div style={{ background: "#0B0C0E", padding: "20px 24px" }}>
          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "28px", fontWeight: 600,
              color: "rgba(255,255,255,0.95)",
            }}
          >
            29{" "}
            <span style={{ fontSize: "13px", color: "rgba(255,255,255,0.55)" }}>ARCHITECTURAL</span>
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.45)", marginTop: "6px" }}>
            Inapplicable by construction. Each claim is named, cited, and verified by assertion tests in CI.
          </div>
        </div>
        <div style={{ background: "#0B0C0E", padding: "20px 24px" }}>
          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "28px", fontWeight: 600,
              color: "rgba(255,255,255,0.95)",
            }}
          >
            7{" "}
            <span style={{ fontSize: "13px", color: "rgba(255,255,255,0.38)" }}>OUT-OF-SCOPE</span>
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.45)", marginTop: "6px" }}>
            Honest scope statements with documented rationale — no model is trained here, so no training-data attacks.
          </div>
        </div>
      </Reveal>

      {/* ledger table */}
      <Reveal
        style={{
          border: "1px solid rgba(255,255,255,0.09)",
          borderTop: "none",
          overflowX: "auto",
        }}
      >
        <div style={{ minWidth: "960px" }}>
          {/* header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "52px 1fr 120px 110px 90px 90px 80px 130px",
              gap: "12px",
              padding: "12px 24px",
              background: "#0C0D0F",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "10.5px", letterSpacing: "0.08em",
              textTransform: "uppercase", color: "rgba(255,255,255,0.38)",
            }}
          >
            <span>#</span>
            <span>Attack</span>
            <span>Class</span>
            <span>Patterns</span>
            <span style={{ textAlign: "right" }}>Tried</span>
            <span style={{ textAlign: "right" }}>Blocked</span>
            <span style={{ textAlign: "right" }}>Partial</span>
            <span style={{ textAlign: "right" }}>Last run</span>
          </div>

          {/* rows */}
          {MATRIX_ROWS.map((r) => (
            <div
              key={r.id}
              className="card-hover"
              style={{
                display: "grid",
                gridTemplateColumns: "52px 1fr 120px 110px 90px 90px 80px 130px",
                gap: "12px",
                padding: "13px 24px",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                fontSize: "13px",
                alignItems: "baseline",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12px", color: "rgba(255,255,255,0.35)",
                }}
              >
                {r.id}
              </span>
              <span style={{ color: "rgba(255,255,255,0.85)", fontWeight: 500 }}>{r.name}</span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "11px", color: r.classColor,
                }}
              >
                {r.class}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "11.5px", color: "rgba(255,255,255,0.5)",
                }}
              >
                {r.patterns}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12.5px", color: "rgba(255,255,255,0.6)",
                  textAlign: "right",
                }}
              >
                {r.tried}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12.5px", color: r.blockedColor,
                  textAlign: "right",
                }}
              >
                {r.blocked}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12.5px", color: r.partialColor,
                  textAlign: "right",
                }}
              >
                {r.partial}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "11.5px", color: "rgba(255,255,255,0.38)",
                  textAlign: "right",
                }}
              >
                {r.lastRun}
              </span>
            </div>
          ))}

          {/* footer */}
          <div
            style={{
              padding: "14px 24px",
              display: "flex", justifyContent: "space-between", alignItems: "center",
              background: "#0C0D0F",
            }}
          >
            <span style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.4)" }}>
              Showing 10 of 79 — the full matrix is queryable per row via{" "}
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  color: "rgba(255,255,255,0.6)",
                }}
              >
                GET /showcase/matrix
              </span>
            </span>
            <Link href="/matrix" className="link-dim" style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "12.5px" }}>
              View all 79 rows →
            </Link>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
