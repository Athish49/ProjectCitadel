"use client";

import { useState, useRef, useEffect } from "react";
import { CHECK_STEPS } from "@/lib/data/formal";

interface LogEntry {
  t: string;
  msg: string;
  status: string;
  color: string;
}

export function SpecCheck() {
  const [checking, setChecking] = useState(false);
  const [checkLog, setCheckLog] = useState<LogEntry[]>([]);
  const [lastRun, setLastRun] = useState("4 minutes ago");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, []);

  function runCheck() {
    if (checking) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    setChecking(true);
    setCheckLog([]);

    const t0 = Date.now();
    const step = (i: number) => {
      if (i >= CHECK_STEPS.length) {
        setChecking(false);
        setLastRun("just now");
        return;
      }
      const elapsed = ((Date.now() - t0) / 1000).toFixed(2) + "s";
      const s = CHECK_STEPS[i];
      setCheckLog((prev) => [...prev, { t: elapsed, msg: s.msg, status: s.status, color: s.color }]);
      timerRef.current = setTimeout(() => step(i + 1), 480);
    };
    step(0);
  }

  const hint =
    checkLog.length === 0
      ? "click re-run to replay the exhaustive check"
      : checking
      ? ""
      : "all invariants hold · all conformance tests pass";

  return (
    <>
      {/* sidebar status values exposed via a hidden span so the sidebar can show lastRun */}
      <div
        style={{
          marginTop: "26px",
          border: "1px solid rgba(255,255,255,0.08)",
          background: "#0C0D0F",
        }}
      >
        {/* panel header */}
        <div
          style={{
            padding: "14px 20px",
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px",
              letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            check_spec.py — RE-RUN
          </span>
          <button
            onClick={runCheck}
            disabled={checking}
            className="btn-outline"
            style={{
              background: "transparent",
              fontFamily: "var(--font-geist), sans-serif",
              fontSize: "12px",
              fontWeight: 500,
              padding: "6px 13px",
              borderRadius: "6px",
              cursor: checking ? "not-allowed" : "pointer",
              opacity: checking ? 0.6 : 1,
            }}
          >
            {checking ? "running…" : "Re-run verification"}
          </button>
        </div>

        {/* log output */}
        <div style={{ padding: "16px 20px", minHeight: "168px", display: "flex", flexDirection: "column", gap: "2px" }}>
          {checkLog.map((cl, i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "60px 1fr auto",
                gap: "12px",
                padding: "6px 0",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12px",
                alignItems: "baseline",
              }}
            >
              <span style={{ color: "rgba(255,255,255,0.3)" }}>{cl.t}</span>
              <span style={{ color: "rgba(255,255,255,0.6)" }}>{cl.msg}</span>
              <span style={{ color: cl.color }}>{cl.status}</span>
            </div>
          ))}
          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px",
              color: "rgba(255,255,255,0.3)",
              paddingTop: "6px",
            }}
          >
            {hint}
          </div>
        </div>
      </div>

      {/* expose lastRun for the sidebar — rendered as an invisible data element */}
      <span id="formal-last-run" data-last-run={lastRun} style={{ display: "none" }} />
    </>
  );
}
