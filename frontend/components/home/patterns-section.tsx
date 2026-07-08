"use client";

import Link from "next/link";
import { Reveal } from "./reveal";
import { PATTERNS } from "@/lib/data/home";

export function PatternsSection() {
  return (
    <section
      id="patterns"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        3.0 — DEFENSE PATTERNS
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
        <span style={{ color: "rgba(255,255,255,0.97)" }}>
          Twelve named patterns, not a pile of checks.
        </span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}Every defense in the system maps to a reusable architectural shape with a citation, an implementation, and a test.
        </span>
      </Reveal>

      <Reveal
        data-patterns-grid
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "1px",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.08)",
          marginTop: "56px",
        }}
      >
        {PATTERNS.map((p) => (
          <Link
            key={p.id}
            href="/patterns"
            className="card-hover"
            style={{
              background: "#0B0C0E",
              padding: "22px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              minHeight: "158px",
              color: "inherit",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12px", color: "rgba(255,255,255,0.42)",
                }}
              >
                {p.id}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "10.5px", color: "rgba(255,255,255,0.3)",
                }}
              >
                defeats {p.defeats}
              </span>
            </div>
            <div
              style={{
                fontSize: "15px", fontWeight: 600,
                color: "rgba(255,255,255,0.94)",
                letterSpacing: "-0.01em",
              }}
            >
              {p.name}
            </div>
            <div style={{ fontSize: "12.5px", lineHeight: 1.55, color: "rgba(255,255,255,0.52)" }}>
              {p.desc}
            </div>
            <div
              style={{
                marginTop: "auto",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "10.5px", color: "rgba(255,255,255,0.32)",
              }}
            >
              {p.cite}
            </div>
          </Link>
        ))}
      </Reveal>
    </section>
  );
}
