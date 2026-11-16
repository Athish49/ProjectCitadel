"use client";

import { useState } from "react";
import {
  MAP_W, MAP_H, MAP_ZONES, MAP_FLOW_LABELS, MAP_NODES,
  MAP_REPLY_BOX, MAP_REPLY_CAPTION, MAP_AUDIT_NODE, MAP_EDGES,
  NODE_INFO, NODE_DEFAULT,
} from "@/lib/data/architecture";
import { Seg } from "@/components/architecture/diagram-primitives";
import styles from "@/components/architecture/architecture.module.css";

const NODE_W = 128;
const NODE_H = 48;
const EDGE_COLOR = "rgba(255,255,255,0.38)";

export function TopologyDiagram() {
  const [selected, setSelected] = useState<string | null>(null);

  const info = selected ? NODE_INFO[selected] : NODE_DEFAULT;
  const metaParts = [info.zone, info.pattern ? `· PATTERN ${info.pattern}` : ""].filter(Boolean);
  const nodeMeta = metaParts.join(" ").toUpperCase();

  return (
    <div className="panel" style={{ marginTop: 0 }}>
      <div style={{ overflowX: "auto", padding: "24px 20px 26px" }}>
        <div style={{ position: "relative", width: MAP_W, height: MAP_H, margin: "0 auto" }}>
          {/* zone backgrounds */}
          {MAP_ZONES.map((z) => (
            <div
              key={z.label}
              style={{
                position: "absolute",
                left: z.x,
                top: 30,
                width: z.w,
                height: 480,
                boxSizing: "border-box",
                background: "rgba(255,255,255,0.025)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: "6px",
              }}
            />
          ))}

          {/* edges */}
          {MAP_EDGES.map((e, i) => (
            <Seg
              key={i}
              x={e.x} y={e.y} w={e.w} h={e.h} d={e.d}
              color={EDGE_COLOR}
              markerId={`arch-map-ah-${i}`}
              arrow={e.arrow}
              hidden={e.hidden}
              label={e.label}
            />
          ))}

          {/* zone labels + sub-labels */}
          {MAP_ZONES.map((z) => (
            <div key={`${z.label}-lbl`}>
              <div
                className="mono"
                style={{
                  position: "absolute", left: z.x + 6, top: 44, width: z.w - 12,
                  textAlign: "center", fontSize: 11, lineHeight: "16px",
                  color: "rgba(255,255,255,0.9)", letterSpacing: "0.1em", textTransform: "uppercase",
                }}
              >
                {z.label}
              </div>
              <div
                style={{
                  position: "absolute", left: z.x + 6, top: 64, width: z.w - 12,
                  textAlign: "center", fontSize: 12, lineHeight: "16px", color: z.subColor,
                }}
              >
                {z.sub}
              </div>
            </div>
          ))}

          {/* data-flow labels along the top */}
          {MAP_FLOW_LABELS.map((f) => (
            <div
              key={f.text}
              style={{
                position: "absolute", left: f.x, top: 6, width: f.w,
                textAlign: "center", fontSize: 12.5, lineHeight: "16px", color: "rgba(255,255,255,0.72)",
              }}
            >
              {f.text}
            </div>
          ))}

          {/* nodes */}
          {MAP_NODES.map((n) => {
            const on = selected === n.id;
            const bg = on ? "#f4f4f5" : "#101114";
            const bd = on ? "#f4f4f5" : "rgba(255,255,255,0.14)";
            const fg = on ? "#0a0b0c" : "rgba(255,255,255,0.92)";
            return (
              <button
                key={n.id}
                type="button"
                className={styles.node}
                aria-pressed={on}
                onClick={() => setSelected((prev) => (prev === n.id ? null : n.id))}
                style={{
                  position: "absolute", left: n.x, top: n.y, width: NODE_W, height: NODE_H,
                  boxSizing: "border-box", padding: "8px 10px",
                  display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center",
                  background: bg, border: `1px solid ${bd}`, borderRadius: "6px",
                  color: fg, fontSize: 13, lineHeight: 1.3,
                }}
              >
                <span>{n.name}</span>
              </button>
            );
          })}

          {/* reply-to-user (non-interactive) */}
          <div
            style={{
              position: "absolute", left: MAP_REPLY_BOX.x, top: MAP_REPLY_BOX.y,
              width: MAP_REPLY_BOX.w, height: MAP_REPLY_BOX.h,
              boxSizing: "border-box", padding: "8px 10px",
              display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center",
              background: "transparent", border: "1px solid rgba(255,255,255,0.14)", borderRadius: "6px",
              color: "rgba(255,255,255,0.8)", fontSize: 13, lineHeight: 1.3,
            }}
          >
            <span>{MAP_REPLY_BOX.label}</span>
          </div>
          <div
            style={{
              position: "absolute", left: MAP_REPLY_CAPTION.x, top: MAP_REPLY_CAPTION.y, width: MAP_REPLY_CAPTION.w,
              textAlign: "center", fontSize: 12.5, lineHeight: "16px", color: "rgba(255,255,255,0.72)",
            }}
          >
            {MAP_REPLY_CAPTION.text}
          </div>

          {/* audit log (full width, interactive) */}
          <button
            type="button"
            className={styles.node}
            aria-pressed={selected === MAP_AUDIT_NODE.id}
            onClick={() => setSelected((prev) => (prev === MAP_AUDIT_NODE.id ? null : MAP_AUDIT_NODE.id))}
            style={{
              position: "absolute", left: MAP_AUDIT_NODE.x, top: MAP_AUDIT_NODE.y,
              width: MAP_AUDIT_NODE.w, height: MAP_AUDIT_NODE.h,
              boxSizing: "border-box", padding: "8px 10px",
              display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center",
              background: selected === MAP_AUDIT_NODE.id ? "#f4f4f5" : "#101114",
              border: `1px solid ${selected === MAP_AUDIT_NODE.id ? "#f4f4f5" : "rgba(255,255,255,0.14)"}`,
              borderRadius: "6px",
              color: selected === MAP_AUDIT_NODE.id ? "#0a0b0c" : "rgba(255,255,255,0.92)",
              fontSize: 13, lineHeight: 1.3,
            }}
          >
            <span>{MAP_AUDIT_NODE.label}</span>
          </button>
        </div>
      </div>

      {/* inspector footer */}
      <div
        style={{
          padding: "22px 22px 24px", borderTop: "1px solid rgba(255,255,255,0.08)",
          display: "flex", flexWrap: "wrap", gap: "8px 32px", alignItems: "baseline", minHeight: "104px",
        }}
      >
        <div style={{ flex: "0 0 220px" }}>
          <div style={{ fontSize: 17, fontWeight: 500 }}>{info.name}</div>
          <div className="mono" style={{ marginTop: 6, fontSize: 11.5, letterSpacing: "0.08em", color: "rgba(255,255,255,0.58)" }}>
            {nodeMeta}
          </div>
        </div>
        <p style={{ margin: 0, flex: "1 1 420px", fontSize: 16.5, lineHeight: 1.45, maxWidth: 760 }}>
          {info.detail}
        </p>
      </div>
    </div>
  );
}
