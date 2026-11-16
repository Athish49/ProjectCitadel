"use client";

import { useEffect, useRef, useState } from "react";
import { GATES, DEFENSE_SCENARIOS } from "@/lib/data/architecture";
import styles from "@/components/architecture/architecture.module.css";

type GateStatus = "" | "PASSED" | "BLOCKED HERE" | "STOPPED HERE" | "WOULD ALSO CATCH" | "NOT REACHED" | "CHECKING…";

export function DefenseDepth() {
  const [scen, setScen] = useState(-1);
  const [sstep, setSstep] = useState(0);
  const [running, setRunning] = useState(false);

  const panelRef = useRef<HTMLDivElement>(null);
  const scenRef = useRef(scen);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  scenRef.current = scen;

  function run(i: number) {
    if (timerRef.current) clearInterval(timerRef.current);
    const sc = DEFENSE_SCENARIOS[i];
    const last = sc.stop < 0 ? 8 : sc.stop + 1;
    let step = 0;
    setScen(i);
    setSstep(0);
    setRunning(true);
    timerRef.current = setInterval(() => {
      step += 1;
      if (step >= last) {
        if (timerRef.current) clearInterval(timerRef.current);
        setSstep(last);
        setRunning(false);
        return;
      }
      setSstep(step);
    }, 420);
  }

  useEffect(() => {
    const el = panelRef.current;
    if (!el) return;
    try {
      const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!("IntersectionObserver" in window) || reduce) return;
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              io.unobserve(entry.target);
              if (scenRef.current < 0) run(1);
            }
          });
        },
        { threshold: 0.03 }
      );
      io.observe(el);
      return () => io.disconnect();
    } catch {
      /* no-op */
    }
  }, []);

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const sc = scen >= 0 ? DEFENSE_SCENARIOS[scen] : null;
  const stop = sc ? sc.stop : -2;
  const done = sc && !running;
  const blocked = !!done && stop >= 0;

  const defW = sc ? `${Math.min(100, (sstep / 8) * 100)}%` : "0%";
  // Colour rule: red = detected/stopped as an attack, green = clean request
  // that cleared every layer (not flagged).
  const defColor = !sc ? "rgba(255,255,255,0.58)" : blocked ? "#e5484d" : done ? "#3ecf8e" : "#ffffff";
  const defTag = !sc
    ? "IDLE"
    : running
    ? "IN FLIGHT"
    : stop < 0
    ? "CLEAN"
    : `${stop === 4 ? "STOPPED" : "BLOCKED"} AT LAYER ${stop + 1}`;
  const defText = !sc ? "" : running ? `Layer ${Math.min(8, sstep + 1)} of 8.` : sc.outcome;

  return (
    <div ref={panelRef} className="panel" style={{ marginTop: 0 }}>
      <div className="ph">
        <span className="eb" style={{ fontSize: 11 }}>Send</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {DEFENSE_SCENARIOS.map((s, i) => {
            const on = i === scen;
            return (
              <button
                key={s.name}
                type="button"
                className={`pick ${styles.pick}`}
                aria-pressed={on}
                onClick={() => run(i)}
                style={{
                  fontSize: 13.5, padding: "8px 14px", minHeight: 44,
                  background: on ? "#f4f4f5" : "#0a0b0c",
                  borderColor: on ? "#f4f4f5" : "rgba(255,255,255,0.12)",
                  color: on ? "#0a0b0c" : "rgba(255,255,255,0.95)",
                }}
              >
                {s.name}
              </button>
            );
          })}
        </div>
      </div>

      <div
        style={{
          padding: "18px 22px", borderBottom: "1px solid rgba(255,255,255,0.08)",
          display: "flex", flexWrap: "wrap", gap: "6px 20px", alignItems: "baseline",
        }}
      >
        <span className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", color: "rgba(255,255,255,0.58)" }}>REQUEST</span>
        <span style={{ fontSize: 16 }}>{sc ? sc.text : "Choose a request to send through the layers."}</span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(min(132px,100%),1fr))",
          gap: "1px", background: "rgba(255,255,255,0.08)",
        }}
      >
        {GATES.map((g, i) => {
          let status: GateStatus = "";
          let sfg = "rgba(255,255,255,0.58)";
          let bg = "#0c0d0f";
          let op = 1;
          if (sc) {
            const reached = i < sstep;
            if (reached && (stop < 0 || i < stop)) {
              // Not flagged as an attack at this layer — green.
              status = "PASSED"; sfg = "#3ecf8e";
            } else if (reached && i === stop) {
              // Detected and stopped here — red.
              status = stop === 4 ? "STOPPED HERE" : "BLOCKED HERE"; sfg = "#e5484d"; bg = "#1a0e0f";
            } else if (done && stop >= 0 && i > stop) {
              if (sc.alsoCatch.includes(i)) { status = "WOULD ALSO CATCH"; sfg = "#e5484d"; }
              else { status = "NOT REACHED"; op = 0.5; }
            } else if (running && i === sstep) {
              status = "CHECKING…"; sfg = "#ffffff"; bg = "#15171a";
            }
          }
          const llm = g.kind !== "CODE";
          const kbd = llm ? "rgba(183,159,214,0.5)" : "rgba(255,255,255,0.16)";
          const kfg = llm ? "#b79fd6" : "rgba(255,255,255,0.62)";
          return (
            <div
              key={g.name}
              className={styles.gate}
              style={{ background: bg, padding: "18px 14px 16px", display: "flex", flexDirection: "column", gap: "8px", minHeight: 168, opacity: op }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="mono" style={{ fontSize: 12, color: "rgba(255,255,255,0.58)" }}>{String(i + 1).padStart(2, "0")}</span>
                <span className="mono" style={{ fontSize: 10.5, letterSpacing: "0.08em", padding: "2px 6px", borderRadius: "3px", border: `1px solid ${kbd}`, color: kfg }}>
                  {g.kind}
                </span>
              </div>
              <div style={{ fontSize: 14.5, fontWeight: 500, lineHeight: 1.25 }}>{g.name}</div>
              <div style={{ fontSize: 12.5, lineHeight: 1.4, color: "rgba(255,255,255,0.62)" }}>{g.what}</div>
              <div className="mono" style={{ marginTop: "auto", fontSize: 11, letterSpacing: "0.08em", color: sfg, minHeight: 16 }}>
                {status}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ height: 2, background: "rgba(255,255,255,0.06)" }}>
        <div style={{ height: "100%", width: defW, background: defColor, transition: "width 0.35s linear, background 0.3s" }} />
      </div>

      <div style={{ padding: "20px 22px 22px", display: "flex", flexWrap: "wrap", gap: "8px 28px", alignItems: "baseline", minHeight: 84 }}>
        <span className="mono" style={{ fontSize: 12, letterSpacing: "0.1em", color: defColor, flex: "0 0 auto" }}>{defTag}</span>
        <span style={{ fontSize: 16, flex: "1 1 420px", maxWidth: 820 }}>{defText}</span>
      </div>
    </div>
  );
}
