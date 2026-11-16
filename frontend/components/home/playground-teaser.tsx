"use client";

import { useEffect, useRef, useState } from "react";
import { SectionHeader } from "./section-header";
import { PLAYGROUND_PAYLOADS } from "@/lib/data/home";
import { LAYER_DEFINITIONS } from "@/lib/types/playground";

// This teaser is a scripted mock — it never calls the backend. The real,
// backend-wired 7-layer pipeline runs on /playground; this is a fast,
// deterministic preview of a few representative outcomes.

export function PlaygroundTeaser() {
  const [sel, setSel] = useState(0);
  const [step, setStep] = useState(0);
  const [running, setRunning] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearInterval(timerRef.current);
    },
    []
  );

  const current = PLAYGROUND_PAYLOADS[sel];
  const done = !running && step > current.stopLayer;

  function pick(i: number) {
    if (timerRef.current) clearInterval(timerRef.current);
    setSel(i);
    setStep(0);
    setRunning(false);
  }

  function run() {
    if (running) return;
    const stop = current.stopLayer;
    setStep(0);
    setRunning(true);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setStep((prev) => {
        const next = prev + 1;
        if (next > stop) {
          if (timerRef.current) clearInterval(timerRef.current);
          setRunning(false);
          return stop + 1;
        }
        return next;
      });
    }, 420);
  }

  const runLabel = running ? "Running…" : done ? "Run again" : "Run attack";

  const traceState = running
    ? "RUNNING"
    : done
    ? current.stopKind === "held"
      ? "DEFENDED"
      : `BLOCKED AT LAYER ${String(current.stopLayer + 1).padStart(2, "0")}`
    : "IDLE";
  // Colour rule (flipped from the original green-for-defended convention):
  // red = detected/stopped as an attack (BLOCKED/HELD), green = not flagged.
  const traceColor = done ? "var(--alert)" : running ? "#ffffff" : "rgba(255,255,255,0.55)";

  const layers = LAYER_DEFINITIONS.map((def, i) => {
    const isStop = done && i === current.stopLayer;
    const isPassed = i < Math.min(step, current.stopLayer);
    const isActive = running && i === step;
    const isNotReached = done && i > current.stopLayer;

    let status = "—";
    let note = "";
    let color = "rgba(255,255,255,0.55)";
    let bg = "transparent";
    let opacity = 1;

    if (isStop) {
      status = current.stopKind === "held" ? "HELD" : "BLOCKED";
      color = "var(--alert)";
      bg = "rgba(229,72,77,0.09)";
      note = current.reason;
    } else if (isPassed) {
      status = "PASS";
      color = "var(--ok)";
    } else if (isActive) {
      status = "···";
      color = "#ffffff";
    } else if (isNotReached) {
      status = "NOT REACHED";
      opacity = 0.45;
    } else if (step > 0 || running) {
      opacity = 0.5;
    }

    return { name: def.name, num: String(i + 1).padStart(2, "0"), status, note, color, opacity, bg };
  });

  return (
    <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(88px,10vw,150px) 32px 0" }}>
      <SectionHeader
        eyebrow="02 — Attack playground"
        title="Fire a real attack."
        lead="Pick a payload and watch seven defense layers respond, one by one."
        more={{ label: "Open the full playground", href: "/playground" }}
      />

      <div data-rv className="panel" style={{ marginTop: "48px", display: "flex", flexWrap: "wrap" }}>
        {/* left: payload picker */}
        <div
          style={{
            flex: "1 1 340px",
            minWidth: 0,
            borderRight: "1px solid rgba(255,255,255,0.08)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div className="eb" style={{ fontSize: "11px", padding: "14px 16px", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
            Select payload
          </div>

          {PLAYGROUND_PAYLOADS.map((p, i) => {
            const active = i === sel;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => pick(i)}
                aria-pressed={active}
                disabled={running}
                style={{
                  appearance: "none",
                  font: "inherit",
                  color: "inherit",
                  textAlign: "left",
                  cursor: running ? "default" : "pointer",
                  border: 0,
                  borderBottom: "1px solid rgba(255,255,255,0.07)",
                  padding: "14px 16px",
                  minHeight: "48px",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "12px",
                  alignItems: "center",
                  width: "100%",
                  transition: "background .2s",
                  background: active ? "rgba(255,255,255,0.06)" : "transparent",
                  opacity: running && !active ? 0.5 : 1,
                }}
              >
                <span style={{ fontSize: "14.5px", color: active ? "#ffffff" : "rgba(255,255,255,0.7)" }}>{p.name}</span>
                <span className="mono" style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.55)" }}>
                  #{p.id}
                </span>
              </button>
            );
          })}

          <div style={{ padding: "18px 16px 20px", display: "flex", flexDirection: "column", gap: "16px", flexGrow: 1, justifyContent: "space-between" }}>
            <div
              className="mono"
              style={{
                fontSize: "12.5px",
                lineHeight: 1.6,
                color: "rgba(255,255,255,0.8)",
                background: "#08090a",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "4px",
                padding: "12px 14px",
                minHeight: "72px",
              }}
            >
              {current.text}
            </div>
            <button type="button" onClick={run} disabled={running} className="btn btn-p" style={{ alignSelf: "flex-start", opacity: running ? 0.6 : 1 }}>
              {runLabel}
            </button>
          </div>
        </div>

        {/* right: defense trace */}
        <div style={{ flex: "1.5 1 420px", minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <span className="eb" style={{ fontSize: "11px" }}>
              Defense trace
            </span>
            <span className="mono" style={{ fontSize: "11.5px", letterSpacing: "0.1em", color: traceColor }}>
              {traceState}
            </span>
          </div>

          {layers.map((l) => (
            <div
              key={l.name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "13px 18px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
                opacity: l.opacity,
                background: l.bg,
                transition: "opacity .3s, background .3s",
              }}
            >
              <span className="mono" style={{ fontSize: "12px", color: "rgba(255,255,255,0.55)", width: "20px" }}>
                {l.num}
              </span>
              <span style={{ flexGrow: 1, fontSize: "14.5px" }}>{l.name}</span>
              <span className="mono" style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.55)" }}>
                {l.note}
              </span>
              <span
                className="mono"
                style={{ fontSize: "11.5px", letterSpacing: "0.08em", width: "100px", textAlign: "right", color: l.color }}
              >
                {l.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
