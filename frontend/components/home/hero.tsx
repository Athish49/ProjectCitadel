"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { HERO_STATS, HERO_INITIAL_VALUES } from "@/lib/data/home";

export function HeroSection() {
  const [attacksToday, setAttacksToday] = useState(1214);
  const [blockedToday, setBlockedToday] = useState(1214);
  const [healthTick, setHealthTick] = useState("0s ago");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const schedule = () => {
      timerRef.current = setInterval(() => {
        setAttacksToday((n) => n + 1);
        setBlockedToday((n) => n + 1);
      }, 2600 + Math.random() * 1200);
    };
    schedule();
    tickRef.current = setInterval(() => {
      setHealthTick(`${Math.floor(Math.random() * 4) + 1}s ago`);
    }, 5000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, []);

  const liveValues = [
    attacksToday.toLocaleString("en-US"),
    blockedToday.toLocaleString("en-US"),
    HERO_INITIAL_VALUES[2],
    HERO_INITIAL_VALUES[3],
  ];

  return (
    <section
      id="top"
      style={{ padding: "172px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      {/* breadcrumb */}
      <div
        style={{
          display: "flex", alignItems: "center", gap: "10px",
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.08em",
          color: "rgba(255,255,255,0.45)", textTransform: "uppercase",
        }}
      >
        <span>Project Citadel</span>
        <span style={{ color: "rgba(255,255,255,0.2)" }}>/</span>
        <span>A multi-agent system engineered to be attacked</span>
      </div>

      {/* h1 */}
      <h1
        style={{
          margin: "28px 0 0",
          fontSize: "clamp(42px, 4.6vw, 68px)",
          lineHeight: 1.08,
          letterSpacing: "-0.032em",
          fontWeight: 600,
          maxWidth: "1060px",
        }}
      >
        <span style={{ color: "rgba(255,255,255,0.97)" }}>Built to be attacked.</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}A security-first multi-agent architecture, demonstrated live against 79 published categories of agentic attack.
        </span>
      </h1>

      {/* CTAs */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px", marginTop: "40px" }}>
        <Link
          href="/playground"
          className="btn-primary"
          style={{ fontSize: "14.5px", fontWeight: 600, padding: "12px 22px", borderRadius: "7px" }}
        >
          Launch the playground
        </Link>
        <a
          href="#architecture"
          className="btn-outline"
          style={{ fontSize: "14.5px", fontWeight: 500, padding: "12px 22px", borderRadius: "7px" }}
        >
          Read the architecture
        </a>
        <span
          style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: "12.5px",
            color: "rgba(255,255,255,0.35)",
            marginLeft: "10px",
          }}
        >
          OWASP AOS · NIST AI RMF · MITRE ATLAS · ATF
        </span>
      </div>

      {/* live ledger strip */}
      <div
        data-hero-stats
        style={{
          marginTop: "88px",
          borderTop: "1px solid rgba(255,255,255,0.09)",
          borderBottom: "1px solid rgba(255,255,255,0.09)",
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
        }}
      >
        {HERO_STATS.map((s, i) => (
          <div
            key={s.label}
            style={{
              padding: "26px 28px",
              borderRight: i < 3 ? "1px solid rgba(255,255,255,0.07)" : undefined,
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                textTransform: "uppercase", color: "rgba(255,255,255,0.4)",
              }}
            >
              {s.label}
            </div>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "34px", fontWeight: 600,
                letterSpacing: "-0.02em",
                color: s.color,
              }}
            >
              {liveValues[i]}
            </div>
            <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* health tick */}
      <div
        style={{
          display: "flex", alignItems: "center", gap: "8px",
          padding: "12px 2px 0",
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "11.5px", color: "rgba(255,255,255,0.32)",
        }}
      >
        <span
          style={{
            width: "6px", height: "6px", borderRadius: "50%",
            background: "#3ECF8E",
            animation: "citadel-pulse 2.2s ease-in-out infinite",
            flexShrink: 0,
          }}
        />
        <span>
          SYSTEM: LIVE — telemetry from /sse/health · updated {healthTick}
        </span>
      </div>
    </section>
  );
}
