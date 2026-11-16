"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useAdversarialStream } from "@/lib/hooks/use-adversarial-stream";
import { PATTERNS } from "@/lib/data/patterns";

const fmt = (n: number) => Math.round(n).toLocaleString("en-US");
const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

// All 12 patterns in lib/data/patterns.ts are implemented — this is a
// static, always-true fact about the codebase, not a live metric.
const PATTERNS_ARMED = PATTERNS.length;
const PATTERNS_TOTAL = PATTERNS.length;

export function HeroSection() {
  const { totalAttempts, breachCount, connected, backendDown } = useAdversarialStream();

  // One-time count-up, eased over 1400ms — ported from Main.dc.html's
  // componentDidMount `up` interval, but now animates from 0 to the REAL
  // numbers once the SSE connection delivers its first real stats, instead
  // of to a hardcoded constant on mount.
  const [k, setK] = useState(0);
  const animStarted = useRef(false);

  useEffect(() => {
    if (animStarted.current || !connected) return;
    animStarted.current = true;
    const t0 = Date.now();
    const id = setInterval(() => {
      const t = Math.min(1, (Date.now() - t0) / 1400);
      setK(easeOutCubic(t));
      if (t >= 1) clearInterval(id);
    }, 40);
    return () => clearInterval(id);
  }, [connected]);

  const hasData = connected && !backendDown;
  const blocked = Math.max(0, totalAttempts - breachCount);

  const stats = [
    {
      label: "Attacks captured · all-time",
      value: hasData ? fmt(totalAttempts * k) : "—",
      sub: "Live users and the adversarial agent",
      color: "rgba(255,255,255,0.95)",
    },
    {
      // Detected and stopped as an attack — red.
      label: "Blocked · all-time",
      value: hasData ? fmt(blocked * k) : "—",
      sub: "Most often at the parser",
      color: "var(--alert)",
    },
    {
      // Evaded every layer, i.e. not flagged as an attack — green.
      label: "Breaches · all-time",
      value: hasData ? fmt(breachCount * k) : "—",
      sub: "Each patched and published",
      color: "var(--ok)",
    },
    {
      label: "Patterns armed",
      value: `${fmt(PATTERNS_ARMED * k)}/${PATTERNS_TOTAL}`,
      sub: "Dual-LLM to signed prompts",
      color: "var(--ok)",
    },
  ];

  return (
    <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(72px,11vw,150px) 32px 0" }}>
      <div data-rv style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span className="live-dot" />
        <span className="eb">System live · 12 of 12 defenses armed</span>
      </div>

      <h1
        data-rv
        style={{
          margin: "26px 0 0",
          fontSize: "clamp(46px,8.2vw,112px)",
          lineHeight: 0.98,
          letterSpacing: "-0.045em",
          fontWeight: 600,
          color: "rgba(255,255,255,0.97)",
          transitionDelay: "80ms",
        }}
      >
        Built to be attacked.
      </h1>

      <p
        data-rv
        style={{
          margin: "28px 0 0",
          maxWidth: "560px",
          fontSize: "clamp(17px,1.5vw,20px)",
          lineHeight: 1.5,
          color: "rgba(255,255,255,0.7)",
          transitionDelay: "160ms",
        }}
      >
        A security-first multi-agent system, tested live against 79 categories of agentic attack.
      </p>

      <div
        data-rv
        style={{ marginTop: "36px", display: "flex", flexWrap: "wrap", gap: "12px", transitionDelay: "240ms" }}
      >
        <Link href="/playground" className="btn btn-p">
          Launch the playground
        </Link>
        <Link href="/architecture" className="btn btn-g">
          Read the architecture
        </Link>
      </div>

      <div
        data-rv
        style={{
          marginTop: "clamp(64px,8vw,112px)",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))",
          gap: "1px",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {stats.map((s) => (
          <div key={s.label} className="cell hover:bg-[#101113] transition-colors" style={{ padding: "26px 24px 28px" }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              {s.label}
            </div>
            <div
              className="mono"
              style={{
                marginTop: "14px",
                fontSize: "38px",
                lineHeight: 1,
                fontWeight: 500,
                fontVariantNumeric: "tabular-nums",
                color: s.color,
              }}
            >
              {s.value}
            </div>
            <div style={{ marginTop: "12px", fontSize: "13px", color: "rgba(255,255,255,0.55)" }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div data-rv className="mono" style={{ padding: "14px 0 0", fontSize: "12px", color: "rgba(255,255,255,0.55)" }}>
        Aligned to OWASP AOS · NIST AI RMF · MITRE ATLAS · ATF
      </div>
    </section>
  );
}
