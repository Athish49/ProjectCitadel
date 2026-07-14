"use client";

import Link from "next/link";
import { useState, useRef } from "react";
import { Reveal } from "./reveal";
import { ATTACK_TEMPLATES, LAYER_DEFS } from "@/lib/data/home";

interface LayerState {
  detail: string;
  kind: "pass" | "detect" | "block" | "";
}

interface Verdict {
  label: string;
  detail: string;
  audits: string;
}

export function PlaygroundTeaser() {
  const [selectedTpl, setSelectedTpl] = useState(0);
  const [payload, setPayload] = useState(ATTACK_TEMPLATES[0].payload);
  const [running, setRunning] = useState(false);
  const [layerStates, setLayerStates] = useState<LayerState[]>([]);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [traceId, setTraceId] = useState("—");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function selectTemplate(i: number) {
    if (timerRef.current) clearTimeout(timerRef.current);
    setSelectedTpl(i);
    setPayload(ATTACK_TEMPLATES[i].payload);
    setLayerStates([]);
    setVerdict(null);
    setRunning(false);
    setTraceId("—");
  }

  function runAttack() {
    if (running) return;
    const tpl = ATTACK_TEMPLATES[selectedTpl];
    const speed = 480;
    const id = "tr_" + Math.random().toString(36).slice(2, 10);
    setRunning(true);
    setLayerStates([]);
    setVerdict(null);
    setTraceId(id);

    const step = (i: number, current: LayerState[]) => {
      if (i >= 7 || (i > 0 && i >= tpl.blockAt)) {
        setRunning(false);
        setVerdict({
          label: "BLOCKED",
          detail: tpl.verdict,
          audits: `${tpl.audits} audit rows written`,
        });
        return;
      }
      const [detail, kind] = tpl.details[i];
      const next = [...current, { detail, kind }];
      setLayerStates(next);
      timerRef.current = setTimeout(() => step(i + 1, next), speed);
    };
    step(0, []);
  }

  // build layers display
  const layers = LAYER_DEFS.map((d, i) => {
    const ls = layerStates[i];
    const done = !!ls;
    const skipped = !!verdict && !done;
    let status = "—";
    let statusColor = "rgba(255,255,255,0.25)";
    let detail = d[2] ? `pattern ${d[2]}` : "";

    if (done) {
      detail = ls.detail;
      if (ls.kind === "pass") { status = "PASS"; statusColor = "rgba(255,255,255,0.55)"; }
      else if (ls.kind === "detect") { status = "DETECTED"; statusColor = "#E2A336"; }
      else if (ls.kind === "block") { status = "BLOCKED"; statusColor = "#E5484D"; }
    } else if (skipped) {
      status = "NOT REACHED"; statusColor = "rgba(255,255,255,0.22)"; detail = "—";
    } else if (running && i === layerStates.length) {
      status = "RUNNING"; statusColor = "#3ECF8E";
    }

    const opacity = done || skipped || running ? 1 : 0.55;
    return { num: d[0], name: d[1], detail, status, statusColor, opacity };
  });

  const traceStatus = running ? "STREAMING" : verdict ? "COMPLETE" : "IDLE";
  const traceStatusColor = running ? "#3ECF8E" : "rgba(255,255,255,0.4)";
  const verdictBg = verdict ? "rgba(229,72,77,0.07)" : "transparent";
  const verdictColor = verdict ? "#E5484D" : "rgba(255,255,255,0.35)";

  return (
    <section
      id="playground"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        2.0 — ATTACK PLAYGROUND
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
        <span style={{ color: "rgba(255,255,255,0.97)" }}>Fire a real attack.</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}Every submission runs the full production defense pipeline — seven layers, live, with the trace streamed back as each layer executes.
        </span>
      </Reveal>

      <Reveal
        data-pg-grid
        style={{
          display: "grid",
          gridTemplateColumns: "420px 1fr",
          gap: "20px",
          marginTop: "56px",
          alignItems: "start",
        }}
      >
        {/* left: attack picker */}
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
            SELECT PAYLOAD
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            {ATTACK_TEMPLATES.map((t, i) => (
              <div
                key={t.name}
                onClick={() => selectTemplate(i)}
                className="card-hover"
                style={{
                  padding: "13px 18px",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  cursor: "pointer",
                  borderLeft: `2px solid ${i === selectedTpl ? "rgba(255,255,255,0.9)" : "transparent"}`,
                  background: i === selectedTpl ? "rgba(255,255,255,0.045)" : "transparent",
                }}
              >
                <div
                  style={{
                    display: "flex", justifyContent: "space-between",
                    alignItems: "baseline", gap: "10px",
                  }}
                >
                  <span style={{ fontSize: "13.5px", fontWeight: 500, color: "rgba(255,255,255,0.9)" }}>
                    {t.name}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-geist-mono), monospace",
                      fontSize: "11px", color: "rgba(255,255,255,0.38)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {t.tax}
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ padding: "16px 18px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
                marginBottom: "10px",
              }}
            >
              PAYLOAD
            </div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              rows={5}
              style={{
                width: "100%",
                boxSizing: "border-box",
                background: "#08090A",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "rgba(255,255,255,0.85)",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12.5px",
                lineHeight: 1.6,
                padding: "12px",
                resize: "vertical",
                outline: "none",
              }}
            />
            <button
              onClick={runAttack}
              disabled={running}
              className="btn-primary"
              style={{
                marginTop: "12px",
                width: "100%",
                border: "none",
                fontFamily: "var(--font-geist), sans-serif",
                fontSize: "14px",
                fontWeight: 600,
                padding: "12px",
                borderRadius: "6px",
                cursor: running ? "not-allowed" : "pointer",
                opacity: running ? 0.5 : 1,
              }}
            >
              {running ? "Running…" : "Run attack"}
            </button>
          </div>
        </div>

        {/* right: 7-layer trace */}
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
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              DEFENSE TRACE — /sse/playground/{traceId}
            </span>
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", color: traceStatusColor,
              }}
            >
              {traceStatus}
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            {layers.map((ly) => (
              <div
                key={ly.num}
                style={{
                  display: "grid",
                  gridTemplateColumns: "44px 210px 1fr 110px",
                  gap: "14px",
                  alignItems: "center",
                  padding: "13px 18px",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  opacity: ly.opacity,
                  transition: "opacity 0.3s ease",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "12px", color: "rgba(255,255,255,0.35)",
                  }}
                >
                  {ly.num}
                </span>
                <span style={{ fontSize: "13.5px", fontWeight: 500, color: "rgba(255,255,255,0.88)" }}>
                  {ly.name}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "12px", color: "rgba(255,255,255,0.48)",
                    lineHeight: 1.5,
                  }}
                >
                  {ly.detail}
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "11px", letterSpacing: "0.06em",
                    textAlign: "right", color: ly.statusColor,
                  }}
                >
                  {ly.status}
                </span>
              </div>
            ))}
          </div>

          {/* verdict bar */}
          <div
            style={{
              padding: "18px",
              display: "flex", alignItems: "center",
              justifyContent: "space-between", gap: "16px",
              background: verdictBg,
              transition: "background 0.4s ease",
              minHeight: "46px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "13px", fontWeight: 600,
                  letterSpacing: "0.06em", color: verdictColor,
                }}
              >
                {verdict?.label ?? ""}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12px", color: "rgba(255,255,255,0.5)",
                }}
              >
                {verdict
                  ? verdict.detail
                  : running
                  ? ""
                  : "Select a payload and run the attack."}
              </span>
            </div>
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11.5px", color: "rgba(255,255,255,0.35)",
                whiteSpace: "nowrap",
              }}
            >
              {verdict?.audits ?? ""}
            </span>
          </div>
        </div>
      </Reveal>

      <Reveal
        style={{ marginTop: "14px", fontSize: "13px", color: "rgba(255,255,255,0.4)" }}
      >
        This teaser simulates the trace.{" "}
        <Link href="/playground" className="link-dim">
          Open the full playground →
        </Link>
        {" "}to chat with the assistant as a logged-in policyholder, fire adversarial PDFs and images, attempt impersonation, and watch every layer in real time.
      </Reveal>
    </section>
  );
}
