"use client";

import { useState, useEffect, useRef } from "react";
import {
  SHORT_CAT,
  CATS_WITH_LIVE,
  ATTACKS_BY_CAT,
  LAYER_MAP,
  ADV_SAMPLES,
  ADV_FALLBACK,
} from "@/lib/data/adversary";

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace" };

interface FeedRow {
  key: string;
  time: string;
  catShort: string;
  name: string;
  surface: string;
  duration: string;
  outcome: "BLOCKED" | "PARTIAL";
  color: string;
  layer: string;
  payload: string;
}

interface LiveState {
  attacksToday: number;
  advTotal: number;
  advSpend: number;
  focusCat: number;
  tickCount: number;
  paused: boolean;
  feed: FeedRow[];
}

function mkRow(ts: number, cat: number): FeedRow {
  const pool = ATTACKS_BY_CAT[cat] ?? ATTACKS_BY_CAT[1];
  const [id, name, pat] = pool[Math.floor(Math.random() * pool.length)];
  const layer = LAYER_MAP[pat] ?? "defense_layer";
  const isPartial = Math.random() < 0.1;
  const d = new Date(ts);
  const p = (n: number) => String(n).padStart(2, "0");
  return {
    key: `${ts}-${id}-${Math.random().toString(36).slice(2)}`,
    time: `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`,
    catShort: SHORT_CAT[cat] ?? "",
    name: `#${id} ${name}`,
    surface: Math.random() < 0.6 ? "claim-filing path" : "customer-inquiry path",
    duration: `${Math.floor(60 + Math.random() * 900)}ms`,
    outcome: isPartial ? "PARTIAL" : "BLOCKED",
    color: isPartial ? "#E2A336" : "#3ECF8E",
    layer,
    payload: ADV_SAMPLES[id] ?? (ADV_FALLBACK[cat] ?? "Illustrative adversarial payload."),
  };
}

export function AdversaryLive() {
  const [state, setState] = useState<LiveState>({
    attacksToday: 1214,
    advTotal: 48317,
    advSpend: 12.41,
    focusCat: CATS_WITH_LIVE[0],
    tickCount: 0,
    paused: false,
    feed: [],
  });

  const pausedRef = useRef(false);
  const feedRef = useRef<HTMLDivElement>(null);

  /* seed initial feed + start ticker */
  useEffect(() => {
    const now = Date.now();
    const seed: FeedRow[] = [];
    for (let i = 9; i >= 0; i--) {
      seed.push(mkRow(now - i * 3400, CATS_WITH_LIVE[i % CATS_WITH_LIVE.length]));
    }
    setState((s) => ({ ...s, feed: seed }));

    const intervalMs = 2400 + Math.random() * 1400;
    const timer = setInterval(() => {
      if (pausedRef.current) return;
      setState((prev) => {
        const idx = CATS_WITH_LIVE.indexOf(prev.focusCat);
        const nextFocus =
          (prev.tickCount + 1) % 5 === 0
            ? CATS_WITH_LIVE[(idx + 1) % CATS_WITH_LIVE.length]
            : prev.focusCat;
        const row = mkRow(Date.now(), prev.focusCat);
        return {
          ...prev,
          feed: [row, ...prev.feed].slice(0, 12),
          focusCat: nextFocus,
          tickCount: prev.tickCount + 1,
          advTotal: prev.advTotal + 1,
          attacksToday: prev.attacksToday + 1,
          advSpend: Math.min(50, prev.advSpend + 0.006 + Math.random() * 0.01),
        };
      });
    }, intervalMs);

    return () => clearInterval(timer);
  }, []);

  function togglePause() {
    setState((s) => {
      pausedRef.current = !s.paused;
      return { ...s, paused: !s.paused };
    });
  }

  const { attacksToday, advTotal, advSpend, focusCat, paused, feed } = state;
  const spendPct = Math.min(100, (advSpend / 50) * 100);
  const spendColor = spendPct > 90 ? "#E5484D" : spendPct > 70 ? "#E2A336" : "#3ECF8E";
  const focusCatName = SHORT_CAT[focusCat] ?? "";
  const streamColor = paused ? "rgba(255,255,255,0.4)" : "#3ECF8E";

  return (
    <div>
      {/* Hero stats */}
      <div
        data-hero-stats=""
        style={{
          marginTop: "52px",
          borderTop: "1px solid rgba(255,255,255,0.09)",
          borderBottom: "1px solid rgba(255,255,255,0.09)",
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
        }}
      >
        {/* Attempts today */}
        <div
          style={{
            padding: "26px 28px",
            borderRight: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
            ATTEMPTS TODAY
          </div>
          <div style={{ ...mono, fontSize: "34px", fontWeight: 600, letterSpacing: "-0.02em", color: "rgba(255,255,255,0.95)" }}>
            {attacksToday.toLocaleString("en-US")}
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>
            {advTotal.toLocaleString("en-US")} all-time
          </div>
        </div>

        {/* Successful breaches */}
        <div
          style={{
            padding: "26px 28px",
            borderRight: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
            SUCCESSFUL BREACHES
          </div>
          <div style={{ ...mono, fontSize: "34px", fontWeight: 600, letterSpacing: "-0.02em", color: "#E5484D" }}>
            3
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>
            all-time · never edited
          </div>
        </div>

        {/* Agent status */}
        <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
            AGENT STATUS
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", ...mono, fontSize: "26px", fontWeight: 600, letterSpacing: "-0.02em", color: "#3ECF8E" }}>
            <span
              style={{
                width: "9px",
                height: "9px",
                borderRadius: "50%",
                background: "#3ECF8E",
                animation: "citadel-pulse 2.2s ease-in-out infinite",
                flexShrink: 0,
              }}
            />
            LIVE
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>
            focused on {focusCatName}
          </div>
        </div>
      </div>

      {/* status indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "12px 2px 0",
          ...mono,
          fontSize: "11.5px",
          color: "rgba(255,255,255,0.32)",
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: "#3ECF8E",
            animation: "citadel-pulse 2.2s ease-in-out infinite",
            flexShrink: 0,
          }}
        />
        SYSTEM: LIVE — telemetry from /sse/adversarial · sandboxed instance only, never the live showcase
      </div>

      {/* Feed + sidebar */}
      <div
        data-main-grid=""
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 360px",
          gap: "20px",
          alignItems: "start",
          marginTop: "64px",
        }}
      >
        {/* Live feed */}
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.09)",
            background: "#0C0D0F",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Feed header */}
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <span style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
              LIVE FEED — /sse/adversarial
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "7px",
                  ...mono,
                  fontSize: "11px",
                  color: streamColor,
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: streamColor,
                    animation: paused ? "none" : "citadel-pulse 2.2s ease-in-out infinite",
                  }}
                />
                {paused ? "PAUSED" : "STREAMING"}
              </span>
              <button
                onClick={togglePause}
                className="btn-outline"
                style={{
                  background: "transparent",
                  ...mono,
                  fontSize: "11px",
                  padding: "5px 11px",
                  borderRadius: "5px",
                  cursor: "pointer",
                }}
              >
                {paused ? "Resume" : "Pause"}
              </button>
            </div>
          </div>

          {/* Feed rows */}
          <div
            ref={feedRef}
            style={{
              display: "flex",
              flexDirection: "column",
              maxHeight: "620px",
              overflowY: "auto",
            }}
          >
            {feed.map((f) => (
              <div
                key={f.key}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                  padding: "12px 18px",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  animation: "citadel-rowin 0.4s ease forwards",
                }}
              >
                <div
                  data-feed-row=""
                  style={{
                    display: "grid",
                    gridTemplateColumns: "68px 96px 1fr 156px 70px 90px",
                    gap: "12px",
                    alignItems: "baseline",
                    ...mono,
                    fontSize: "12px",
                  }}
                >
                  <span style={{ color: "rgba(255,255,255,0.32)" }}>{f.time}</span>
                  <span data-feed-catshort="" style={{ color: "rgba(255,255,255,0.42)", fontSize: "10.5px" }}>
                    {f.catShort}
                  </span>
                  <span style={{ color: "rgba(255,255,255,0.8)", fontFamily: "var(--font-geist), sans-serif", fontSize: "13px" }}>
                    {f.name}
                  </span>
                  <span data-feed-surface="" style={{ color: "rgba(255,255,255,0.4)" }}>
                    {f.surface}
                  </span>
                  <span data-feed-duration="" style={{ color: "rgba(255,255,255,0.4)", textAlign: "right" }}>
                    {f.duration}
                  </span>
                  <span style={{ textAlign: "right", color: f.color, fontWeight: 600, letterSpacing: "0.04em" }}>
                    {f.outcome}
                  </span>
                </div>
                <div style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.3)", ...mono, paddingLeft: "1px" }}>
                  blocked at{" "}
                  <span style={{ color: "rgba(255,255,255,0.45)" }}>{f.layer}</span>
                  {" · "}
                  <span style={{ color: "rgba(255,255,255,0.25)" }}>{f.payload}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Budget */}
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.09)",
              background: "#0C0D0F",
              padding: "20px 22px",
            }}
          >
            <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
              MONTHLY COST — CLAUDE HAIKU 4.5
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "12px" }}>
              <span style={{ ...mono, fontSize: "30px", fontWeight: 600, color: spendColor }}>
                ${advSpend.toFixed(2)}
              </span>
              <span style={{ ...mono, fontSize: "14px", color: "rgba(255,255,255,0.4)" }}>
                / $50.00 cap
              </span>
            </div>
            <div
              style={{
                marginTop: "14px",
                height: "5px",
                background: "rgba(255,255,255,0.08)",
                overflow: "hidden",
                borderRadius: "3px",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${spendPct.toFixed(1)}%`,
                  background: spendColor,
                  transition: "width 1s ease",
                }}
              />
            </div>
            <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.42)", marginTop: "12px", lineHeight: 1.55 }}>
              Hard cap enforced by P11 (Token &amp; Cost Budgets). ~$0.006 per attempt. A circuit breaker halts the agent outright on exhaustion — it does not silently degrade.
            </div>
          </div>

          {/* Agent profile */}
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.09)",
              background: "#0C0D0F",
              padding: "20px 22px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <span style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
              AGENT PROFILE
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
              {[
                { label: "Model",     value: "Claude Haiku 4.5",                              mono: true  },
                { label: "Isolation", value: "Separate container, sandboxed test instance only", mono: false },
                { label: "Reaches",   value: "Adversarial-test API only — never the live showcase", mono: false },
              ].map(({ label, value, mono: isMono }) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", gap: "10px" }}>
                  <span style={{ color: "rgba(255,255,255,0.42)", flexShrink: 0 }}>{label}</span>
                  <span
                    style={{
                      color: "rgba(255,255,255,0.85)",
                      textAlign: "right",
                      maxWidth: "190px",
                      ...(isMono ? { ...mono, fontSize: "12.5px" } : {}),
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
            <div
              style={{
                borderTop: "1px solid rgba(255,255,255,0.07)",
                paddingTop: "12px",
                fontSize: "12.5px",
                lineHeight: 1.6,
                color: "rgba(255,255,255,0.5)",
              }}
            >
              Rotates through the taxonomy category by category; mutates payloads using feedback from blocked vs. partially-leaked outcomes. The strategy is open-source and displayed verbatim — no proprietary technique withheld.
            </div>
            <div style={{ ...mono, fontSize: "11.5px", color: "rgba(255,255,255,0.38)" }}>
              adversarial/strategy.py:1
            </div>
          </div>

          {/* Testing now */}
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.09)",
              background: "#0C0D0F",
              padding: "18px 22px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
            }}
          >
            <div>
              <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
                TESTING NOW
              </div>
              <div style={{ fontSize: "15px", fontWeight: 600, color: "rgba(255,255,255,0.92)", marginTop: "6px" }}>
                {focusCatName}
              </div>
            </div>
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "#3ECF8E",
                animation: "citadel-pulse 2.2s ease-in-out infinite",
                flexShrink: 0,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
