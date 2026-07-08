"use client";

import { Reveal } from "./reveal";
import { RISKS, STANDARDS } from "@/lib/data/home";

export function RisksSection() {
  return (
    <section
      id="risks"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        7.0 — RESIDUAL RISK
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
        <span style={{ color: "rgba(255,255,255,0.97)" }}>What still doesn't work.</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}Thirteen named limitations with root causes, published in full. Honesty is a stronger credential than a perfect score.
        </span>
      </Reveal>

      <Reveal style={{ borderTop: "1px solid rgba(255,255,255,0.09)", marginTop: "56px" }}>
        {RISKS.map((rr) => (
          <div
            key={rr.id}
            style={{
              display: "grid",
              gridTemplateColumns: "90px 340px 1fr",
              gap: "24px",
              padding: "20px 4px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              alignItems: "baseline",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12.5px", color: "rgba(255,255,255,0.38)",
              }}
            >
              {rr.id}
            </span>
            <span style={{ fontSize: "15px", fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>
              {rr.name}
            </span>
            <span style={{ fontSize: "13.5px", lineHeight: 1.6, color: "rgba(255,255,255,0.5)" }}>
              {rr.cause}
            </span>
          </div>
        ))}
        <div style={{ padding: "16px 4px", fontSize: "13px", color: "rgba(255,255,255,0.4)" }}>
          5 of 13 shown — the full register ships with the repo, with a root cause and status for each.
        </div>
      </Reveal>

      <Reveal
        style={{
          display: "flex", alignItems: "center", gap: "12px",
          marginTop: "44px", flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: "11px", letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.4)", marginRight: "8px",
          }}
        >
          TAXONOMY SYNTHESISED FROM
        </span>
        {STANDARDS.map((std) => (
          <span
            key={std}
            style={{
              border: "1px solid rgba(255,255,255,0.12)",
              padding: "7px 14px",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px", color: "rgba(255,255,255,0.65)",
            }}
          >
            {std}
          </span>
        ))}
      </Reveal>
    </section>
  );
}
