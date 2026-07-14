"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { Reveal } from "./reveal";
import { makeFeedRow, type FeedRow } from "@/lib/data/home";

function seedFeed(): FeedRow[] {
  const rows: FeedRow[] = [];
  for (let i = 7; i >= 0; i--) {
    rows.push(makeFeedRow(Date.now() - i * 3200));
  }
  return rows;
}

export function AdversarySection() {
  const [feed, setFeed] = useState<FeedRow[]>([]);
  const [advTotal, setAdvTotal] = useState(48317);
  const [advSpend, setAdvSpend] = useState(12.41);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // Seed only on the client to avoid SSR/hydration mismatch
    const now = Date.now();
    const seed: FeedRow[] = [];
    for (let i = 7; i >= 0; i--) seed.push(makeFeedRow(now - i * 3200));
    setFeed(seed);

    timerRef.current = setInterval(() => {
      const row = makeFeedRow(Date.now());
      setFeed((prev) => [row, ...prev].slice(0, 8));
      setAdvTotal((n) => n + 1);
      setAdvSpend((n) => Math.min(50, n + 0.0007));
    }, 2600 + Math.random() * 1200);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  const advSpendPct = ((advSpend / 50) * 100).toFixed(1) + "%";

  return (
    <section
      id="adversary"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        5.0 — ADVERSARIAL AGENT
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
        <span style={{ color: "rgba(255,255,255,0.97)" }}>An autonomous attacker is running right now.</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}A sandboxed agent rotates through the taxonomy, mutates payloads on feedback, and streams every attempt here — including any that breach all 7 defense layers.
        </span>
      </Reveal>

      <Reveal
        data-adv-grid
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 360px",
          gap: "20px",
          marginTop: "56px",
          alignItems: "stretch",
        }}
      >
        {/* live feed */}
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.09)",
            background: "#0C0D0F",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              LIVE FEED — /sse/adversarial
            </span>
            <span
              style={{
                display: "inline-flex", alignItems: "center", gap: "7px",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", color: "#3ECF8E",
              }}
            >
              <span
                style={{
                  width: "6px", height: "6px", borderRadius: "50%",
                  background: "#3ECF8E",
                  animation: "citadel-pulse 2.2s ease-in-out infinite",
                }}
              />
              STREAMING
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", minHeight: "372px" }}>
            {feed.map((f, i) => (
              <div
                key={f.key}
                style={{
                  display: "grid",
                  gridTemplateColumns: "76px 1fr 190px 92px",
                  gap: "14px",
                  padding: "12px 18px",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12px",
                  alignItems: "baseline",
                  opacity: i === 0 ? 1 : 1 - i * 0.09,
                  transition: "opacity 0.5s ease",
                }}
              >
                <span style={{ color: "rgba(255,255,255,0.32)" }}>{f.time}</span>
                <span style={{ color: "rgba(255,255,255,0.72)" }}>{f.attack}</span>
                <span style={{ color: "rgba(255,255,255,0.4)" }}>{f.layer}</span>
                <span style={{ textAlign: "right", color: f.color }}>{f.outcome}</span>
              </div>
            ))}
          </div>
        </div>

        {/* counters */}
        <div
          style={{
            display: "flex", flexDirection: "column",
            gap: "1px",
            background: "rgba(255,255,255,0.08)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {/* attempts counter */}
          <div style={{ background: "#0B0C0E", padding: "20px 22px", flex: 1 }}>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              ATTEMPTS · ALL-TIME
            </div>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "32px", fontWeight: 600,
                color: "rgba(255,255,255,0.95)",
                marginTop: "8px",
              }}
            >
              {advTotal.toLocaleString("en-US")}
            </div>
          </div>

          {/* breaches */}
          <div style={{ background: "#0B0C0E", padding: "20px 22px", flex: 1 }}>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              SUCCESSFUL BREACHES
            </div>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "32px", fontWeight: 600,
                color: "#E5484D",
                marginTop: "8px",
              }}
            >
              3
            </div>
            <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.45)", marginTop: "6px", lineHeight: 1.5 }}>
              Each one is documented in the breach register. This counter is never edited.
            </div>
          </div>

          {/* budget */}
          <div style={{ background: "#0B0C0E", padding: "20px 22px", flex: 1 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "11px", letterSpacing: "0.1em",
                  color: "rgba(255,255,255,0.4)",
                }}
              >
                MONTHLY BUDGET
              </div>
              <div
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12px", color: "rgba(255,255,255,0.6)",
                }}
              >
                ${advSpend.toFixed(2)} / $50.00
              </div>
            </div>
            <div
              style={{
                marginTop: "12px", height: "4px",
                background: "rgba(255,255,255,0.08)", overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: advSpendPct,
                  background: "rgba(255,255,255,0.7)",
                  transition: "width 1s ease",
                }}
              />
            </div>
            <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.45)", marginTop: "10px", lineHeight: 1.5 }}>
              Hard cap. Separate container, sandboxed instance only. The attack strategy is open-source and displayed verbatim.
            </div>
          </div>
        </div>
      </Reveal>

      <Reveal style={{ marginTop: "14px", fontSize: "13px", color: "rgba(255,255,255,0.4)" }}>
        This teaser simulates the feed.{" "}
        <Link href="/adversary" className="link-dim">
          Open the full adversary console →
        </Link>
        {" "}for category-by-category coverage, the cost gauge, and the honest breach log.
      </Reveal>
    </section>
  );
}
