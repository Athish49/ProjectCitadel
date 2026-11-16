"use client";

import { useState } from "react";
import { CONFORMANCE_STATS, MATRIX_ROWS, STATES, STATES_SHORT } from "@/lib/data/formal";

/** Section 05 — "81 stage pairs. 11 accepted, 70 refused." A 9×9 heatmap of
 *  every (from, to) pair the orchestrator's advance_stage() was driven
 *  through. This reflects the fixed state-machine topology (same 11 edges
 *  the live BFS checker explores) rather than a per-request backend call —
 *  clicking a cell just inspects that pair, it doesn't re-run the checker. */
export function ReachabilityMatrix() {
  const [pair, setPair] = useState<[number, number] | null>(null);

  const pairValid = pair ? MATRIX_ROWS[pair[0]].cells[pair[1]].valid : false;
  const pairText = pair
    ? `${STATES[pair[0]]} → ${STATES[pair[1]]} ${pairValid ? "· accepted" : "· refused"}`
    : "Select a cell to inspect a pair.";
  const pairColor = !pair ? "rgba(255,255,255,0.58)" : pairValid ? "#3ecf8e" : "rgba(255,255,255,0.85)";

  return (
    <div style={{ marginTop: "44px", display: "flex", flexWrap: "wrap", gap: "32px 56px", alignItems: "flex-start" }}>
      <style>{`
        .hc { appearance: none; border: 0; padding: 0; width: 100%; aspect-ratio: 1; min-height: 26px; border-radius: 2px; cursor: pointer; outline-offset: 1px; transition: transform .15s; }
        .hc:hover { transform: scale(1.12); }
      `}</style>

      <div className="panel" style={{ flex: "1.3 1 420px", minWidth: 0, padding: "20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "86px repeat(9,minmax(0,1fr))", gap: "4px", alignItems: "center" }}>
          <span />
          {STATES_SHORT.map((t) => (
            <span key={t} className="mono" style={{ fontSize: "10.5px", color: "rgba(255,255,255,0.58)", textAlign: "center" }}>{t}</span>
          ))}
        </div>

        {MATRIX_ROWS.map((row) => (
          <div key={row.from} style={{ marginTop: "4px", display: "grid", gridTemplateColumns: "86px repeat(9,minmax(0,1fr))", gap: "4px", alignItems: "center" }}>
            <span className="mono" style={{ fontSize: "10.5px", color: "rgba(255,255,255,0.58)" }}>{STATES_SHORT[row.from]}</span>
            {row.cells.map((cell) => {
              const isSelected = !!pair && pair[0] === row.from && pair[1] === cell.to;
              return (
                <button
                  key={cell.to}
                  type="button"
                  className="hc"
                  aria-label={`${STATES[row.from]} to ${STATES[cell.to]}, ${cell.valid ? "accepted" : "refused"}`}
                  onClick={() => setPair([row.from, cell.to])}
                  style={{
                    background: cell.valid ? "#3ecf8e" : "rgba(255,255,255,0.1)",
                    outline: isSelected ? "2px solid #ffffff" : "2px solid transparent",
                  }}
                />
              );
            })}
          </div>
        ))}

        <div className="mono" style={{ marginTop: "18px", fontSize: "12px", color: pairColor, minHeight: "20px" }}>{pairText}</div>
        <div className="mono" style={{ marginTop: "8px", display: "flex", flexWrap: "wrap", gap: "6px 20px", fontSize: "11.5px", color: "rgba(255,255,255,0.58)" }}>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "10px", height: "10px", background: "#3ecf8e", borderRadius: "2px" }} />accepted
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "10px", height: "10px", background: "rgba(255,255,255,0.1)", borderRadius: "2px" }} />refused
          </span>
          <span>rows = from · columns = to</span>
        </div>
      </div>

      <div style={{ flex: "1 1 300px", minWidth: 0 }}>
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}>
          {CONFORMANCE_STATS.map((cf) => (
            <div key={cf.label} style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "20px", padding: "18px 0", borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
              <span style={{ fontSize: "15px" }}>{cf.label}</span>
              <span className="mono" style={{ fontSize: "24px", fontWeight: 500, color: "#3ecf8e" }}>{cf.n}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
