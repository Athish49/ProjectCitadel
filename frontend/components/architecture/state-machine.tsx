"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { SCENARIOS, MAIN_STATES, BRANCH_STATES, GUARDS, LIMITS } from "@/lib/data/architecture";
import { Reveal } from "@/components/home/reveal";

interface LogEntry {
  time: string;
  tag: string;
  tagColor: string;
  msg: string;
}

function chipStyle(lit: string | undefined, isWhite?: boolean): React.CSSProperties {
  const base: React.CSSProperties = {
    display: "inline-flex",
    padding: "9px 14px",
    fontFamily: "var(--font-geist-mono), monospace",
    fontSize: "12px",
    letterSpacing: "0.04em",
    whiteSpace: "nowrap",
    transition: "all 0.3s ease",
  };
  if (lit) {
    return {
      ...base,
      border: `1px solid ${lit}`,
      color: lit === "rgba(255,255,255,0.6)" ? "rgba(255,255,255,0.9)" : lit,
      background: "rgba(255,255,255,0.03)",
    };
  }
  return {
    ...base,
    border: "1px solid rgba(255,255,255,0.14)",
    color: "rgba(255,255,255,0.5)",
    background: "transparent",
  };
}

export function StateMachine() {
  const [activeScenario, setActiveScenario] = useState(-1);
  const [litStates, setLitStates] = useState<Record<string, string>>({});
  const [log, setLog] = useState<LogEntry[]>([]);
  const [running, setRunning] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function runScenario(i: number) {
    if (timerRef.current) clearTimeout(timerRef.current);
    const sc = SCENARIOS[i];
    setActiveScenario(i);
    setLitStates({});
    setLog([]);
    setRunning(true);

    const t0 = Date.now();

    const step = (j: number) => {
      if (j >= sc.steps.length) {
        setRunning(false);
        return;
      }
      const st = sc.steps[j];
      const elapsed = ((Date.now() - t0) / 1000).toFixed(2) + "s";
      setLitStates((prev) => ({ ...prev, [st.state]: st.tagColor }));
      setLog((prev) => [...prev, { time: elapsed, tag: st.tag, tagColor: st.tagColor, msg: st.msg }]);
      timerRef.current = setTimeout(() => step(j + 1), 750);
    };
    step(0);
  }

  const logHint =
    activeScenario === -1
      ? "select a scenario above — every step below is a real audit row shape"
      : running
      ? "…"
      : "scenario complete · state machine is read-only from here — no backward transitions exist";

  return (
    <>
      {/* interactive state machine panel */}
      <div
        style={{
          marginTop: "52px",
          border: "1px solid rgba(255,255,255,0.09)",
          background: "#0C0D0F",
        }}
      >
        {/* scenario picker */}
        <div
          style={{
            padding: "14px 20px",
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            display: "flex", justifyContent: "space-between",
            alignItems: "center", flexWrap: "wrap", gap: "12px",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px", letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            CLAIM WORKFLOW — RUN A SCENARIO
          </span>
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {SCENARIOS.map((sc, i) => (
              <button
                key={sc.name}
                onClick={() => runScenario(i)}
                className="btn-outline"
                style={{
                  background: activeScenario === i ? "rgba(255,255,255,0.95)" : "transparent",
                  color: activeScenario === i ? "#0A0B0C" : "rgba(255,255,255,0.75)",
                  border: `1px solid ${activeScenario === i ? "transparent" : "rgba(255,255,255,0.18)"}`,
                  fontFamily: "var(--font-geist), sans-serif",
                  fontSize: "12.5px", fontWeight: 500,
                  padding: "7px 14px", borderRadius: "6px",
                  cursor: "pointer", transition: "all 0.2s ease",
                }}
              >
                {sc.name}
              </button>
            ))}
          </div>
        </div>

        {/* state chips */}
        <div style={{ padding: "30px 20px 8px", overflowX: "auto" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 0, minWidth: "980px" }}>
            {MAIN_STATES.map((name) => (
              <div key={name} style={{ display: "flex", alignItems: "center" }}>
                <span style={chipStyle(litStates[name])}>{name}</span>
                <span
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    color: "rgba(255,255,255,0.3)", padding: "0 10px",
                  }}
                >
                  →
                </span>
              </div>
            ))}

            {/* branch states column */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {BRANCH_STATES.map((bs) => (
                <div key={bs.name} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span style={chipStyle(litStates[bs.name])}>{bs.name}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-geist-mono), monospace",
                      fontSize: "11px", color: "rgba(255,255,255,0.35)",
                    }}
                  >
                    {bs.guard}
                  </span>
                </div>
              ))}
            </div>

            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                color: "rgba(255,255,255,0.3)", padding: "0 10px",
              }}
            >
              →
            </span>
            <span style={chipStyle(litStates["CLOSED"] || litStates["LOCKED"])}>CLOSED</span>
          </div>

          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px", color: "rgba(255,255,255,0.35)",
              padding: "18px 2px 12px", minWidth: "980px",
            }}
          >
            no backward transitions · no stage skipping · any attempt → transition_violation audit row
          </div>
        </div>

        {/* event log */}
        <div
          style={{
            borderTop: "1px solid rgba(255,255,255,0.07)",
            minHeight: "208px",
            display: "flex", flexDirection: "column",
          }}
        >
          {log.map((lg, i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "76px 130px 1fr",
                gap: "14px",
                padding: "10px 20px",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12px",
                alignItems: "baseline",
              }}
            >
              <span style={{ color: "rgba(255,255,255,0.3)" }}>{lg.time}</span>
              <span style={{ color: lg.tagColor }}>{lg.tag}</span>
              <span style={{ color: "rgba(255,255,255,0.6)", lineHeight: 1.5 }}>{lg.msg}</span>
            </div>
          ))}
          <div
            style={{
              padding: "12px 20px",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px", color: "rgba(255,255,255,0.3)",
            }}
          >
            {logHint}
          </div>
        </div>
      </div>

      {/* guards + limits */}
      <Reveal
        data-two-col
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "20px",
          marginTop: "20px",
        }}
      >
        {/* transition guards */}
        <div style={{ border: "1px solid rgba(255,255,255,0.09)", background: "#0C0D0F" }}>
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px", letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            TRANSITION GUARDS — ENFORCED IN CODE
          </div>
          {GUARDS.map((gd) => (
            <div
              key={gd.edge}
              style={{
                display: "grid",
                gridTemplateColumns: "240px 1fr",
                gap: "14px",
                padding: "12px 18px",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                fontSize: "12.5px", alignItems: "baseline",
              }}
            >
              <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11.5px", color: "rgba(255,255,255,0.75)" }}>
                {gd.edge}
              </span>
              <span style={{ color: "rgba(255,255,255,0.48)", lineHeight: 1.5 }}>{gd.req}</span>
            </div>
          ))}
        </div>

        {/* runtime limits */}
        <div style={{ border: "1px solid rgba(255,255,255,0.09)", background: "#0C0D0F", display: "flex", flexDirection: "column" }}>
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px", letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            RUNTIME LIMITS
          </div>
          {LIMITS.map((lm) => (
            <div
              key={lm.name}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "baseline",
                padding: "13px 18px",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
              }}
            >
              <span style={{ fontSize: "13.5px", color: "rgba(255,255,255,0.8)" }}>{lm.name}</span>
              <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "12px", color: "rgba(255,255,255,0.5)" }}>
                {lm.value}
              </span>
            </div>
          ))}
          <div
            style={{
              padding: "16px 18px",
              fontSize: "12.5px", color: "rgba(255,255,255,0.4)",
              lineHeight: 1.6, marginTop: "auto",
            }}
          >
            The state machine is formally specified in TLA+ and conformance-tested: all 11 valid edges accepted, all 70 invalid pairs rejected.{" "}
            <Link href="/#verification" className="link-dim">See verification →</Link>
          </div>
        </div>
      </Reveal>
    </>
  );
}
