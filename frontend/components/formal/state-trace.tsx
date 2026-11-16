"use client";

import { useEffect, useRef, useState } from "react";
import { EDGES, NODE_POS, STATES, TRACE_PATHS } from "@/lib/data/formal";

const mono = { fontFamily: "var(--font-geist-mono), ui-monospace, monospace" } as const;
const CANVAS_W = 1152;
const CANVAS_H = 432;
const NODE_W = 132;
const NODE_H = 56;
const RANKS = [0, 170, 340, 510, 680, 850, 1020];

function edgeIndex(from: number, to: number): number {
  return EDGES.findIndex(([f, t]) => f === from && t === to);
}

/** Section 02 — "Trace a claim". Interactive rank diagram ported from the
 *  design file's own S()/E()/P() state machine; auto-plays the first path
 *  once scrolled into view, mirroring the design's componentDidMount. */
export function StateTrace() {
  const [path, setPath] = useState(-1);
  const [step, setStep] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoRef = useRef(false);

  function play(i: number) {
    if (timerRef.current) clearInterval(timerRef.current);
    const seq = TRACE_PATHS[i].seq;
    setPath(i);
    setStep(0);
    let s = 0;
    timerRef.current = setInterval(() => {
      s += 1;
      if (s >= seq.length) {
        if (timerRef.current) clearInterval(timerRef.current);
        return;
      }
      setStep(s);
    }, 850);
  }

  useEffect(() => {
    const el = containerRef.current;
    const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!el || reduce || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && !autoRef.current) {
          autoRef.current = true;
          play(0);
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.2 });
    io.observe(el);
    return () => {
      io.disconnect();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const seq = path >= 0 ? TRACE_PATHS[path].seq : [];
  const cur = seq.length ? seq[step] : -1;
  const seen = new Set(seq.slice(0, step));
  const usedEdges = new Set<number>();
  let curEdgeIdx = -1;
  for (let k = 1; k <= step && k < seq.length; k++) {
    const idx = edgeIndex(seq[k - 1], seq[k]);
    if (idx >= 0) {
      usedEdges.add(idx);
      if (k === step) curEdgeIdx = idx;
    }
  }

  const stepTag = cur < 0 ? "NO TRACE" : step === 0 ? "START" : `TRANSITION ${curEdgeIdx + 1}`;
  const stepText =
    cur < 0
      ? "Choose a path to follow a claim through the machine."
      : step === 0
      ? "A new claim always starts at INTAKE."
      : `${STATES[seq[step - 1]]} → ${STATES[cur]}. ${EDGES[curEdgeIdx][2]}.`;

  return (
    <div ref={containerRef} className="panel" style={{ marginTop: "44px" }}>
      <div className="ph">
        <span className="eb" style={{ fontSize: "11px" }}>Trace a claim</span>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {TRACE_PATHS.map((p, i) => {
            const on = i === path;
            return (
              <button
                key={p.name}
                type="button"
                className="pick"
                aria-pressed={on}
                onClick={() => play(i)}
                style={{
                  fontSize: "13.5px", padding: "8px 14px",
                  background: on ? "#f4f4f5" : "#0a0b0c",
                  borderColor: on ? "#f4f4f5" : "rgba(255,255,255,0.12)",
                  color: on ? "#0a0b0c" : "rgba(255,255,255,0.95)",
                }}
              >
                {p.name}
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ overflowX: "auto", padding: "24px 22px 28px" }}>
        <div style={{ position: "relative", width: `${CANVAS_W}px`, height: `${CANVAS_H}px`, margin: "0 auto" }}>
          {/* rank background columns */}
          {RANKS.map((x) => (
            <div
              key={x}
              style={{
                position: "absolute", left: `${x}px`, top: "24px",
                width: `${NODE_W}px`, height: "400px",
                background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)",
                borderRadius: "6px",
              }}
            />
          ))}

          {/* edges */}
          <svg width={CANVAS_W} height={CANVAS_H} style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}>
            <defs>
              <marker id="trace-arrow" orient="auto" markerWidth="6" markerHeight="6" refX="3" refY="3">
                <path d="M0 0 L5 3 L0 6 Z" fill="context-stroke" />
              </marker>
            </defs>
            {EDGES.map(([from, to], i) => {
              const a = NODE_POS[from];
              const b = NODE_POS[to];
              const active = usedEdges.has(i);
              const color = active ? "#f4f4f5" : "rgba(255,255,255,0.3)";
              const x1 = a.x + NODE_W, y1 = a.y + NODE_H / 2;
              const x2 = b.x, y2 = b.y + NODE_H / 2;
              return (
                <line
                  key={i}
                  x1={x1} y1={y1} x2={x2} y2={y2}
                  stroke={color} strokeWidth={1.5} strokeLinecap="round"
                  markerEnd="url(#trace-arrow)"
                />
              );
            })}
          </svg>

          {/* nodes */}
          {STATES.map((name, i) => {
            const pos = NODE_POS[i];
            const isCur = i === cur;
            const isSeen = seen.has(i);
            const bg = isCur ? "#f4f4f5" : isSeen ? "#15171a" : "#101114";
            const bd = isCur ? "#f4f4f5" : isSeen ? "rgba(255,255,255,0.55)" : "rgba(255,255,255,0.14)";
            const fg = isCur ? "#0a0b0c" : isSeen ? "#ffffff" : "rgba(255,255,255,0.72)";
            return (
              <div
                key={name}
                style={{
                  position: "absolute", left: `${pos.x}px`, top: `${pos.y}px`,
                  width: `${NODE_W}px`, height: `${NODE_H}px`,
                  boxSizing: "border-box", padding: "8px 10px",
                  display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center",
                  background: bg, border: `1px solid ${bd}`, borderRadius: "6px", color: fg,
                  fontSize: "11.5px", lineHeight: 1.3,
                  ...mono, letterSpacing: "0.02em",
                  transition: "background .35s,border-color .35s,color .35s",
                }}
              >
                <span>{name.replace(/_/g, "_​")}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ padding: "18px 22px", borderTop: "1px solid rgba(255,255,255,0.08)", display: "flex", flexWrap: "wrap", gap: "6px 28px", alignItems: "baseline", minHeight: "62px" }}>
        <span className="mono" style={{ fontSize: "12px", letterSpacing: "0.08em", color: "rgba(255,255,255,0.58)", flex: "0 0 auto" }}>{stepTag}</span>
        <span style={{ fontSize: "16px", flex: "1 1 420px" }}>{stepText}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(330px,100%),1fr))", gap: "1px", background: "rgba(255,255,255,0.08)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        {EDGES.map(([, , rule], i) => (
          <div key={i} style={{ background: curEdgeIdx === i ? "#1a1c20" : "#0c0d0f", padding: "12px 18px", display: "flex", gap: "14px", alignItems: "baseline", transition: "background .3s,border-color .3s,color .3s,opacity .3s" }}>
            <span className="mono" style={{ flex: "0 0 20px", fontSize: "12px", color: "rgba(255,255,255,0.58)" }}>{i + 1}</span>
            <span style={{ fontSize: "13.5px", color: "rgba(255,255,255,0.78)" }}>{rule}</span>
          </div>
        ))}
        <div style={{ background: "#0c0d0f", padding: "12px 18px", fontSize: "13px", color: "rgba(255,255,255,0.58)" }}>
          Guards read database state only. No LLM output can satisfy one.
        </div>
      </div>
    </div>
  );
}
