"use client";

import { useState } from "react";
import {
  DIAG_NODES, DIAG_EDGES, DIAG_ZONES, DIAG_LEGEND,
  NODE_W, NODE_H, SVG_W, SVG_H,
} from "@/lib/data/architecture";

export function TopologyDiagram() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  function toggleNode(id: string) {
    setSelectedNode((prev) => (prev === id ? null : id));
  }
  function clearSelection() {
    setSelectedNode(null);
  }

  // Compute which node ids are neighbors of selected
  const neighborIds = new Set<string>();
  if (selectedNode) {
    DIAG_EDGES.forEach((e) => {
      if (e.from === selectedNode || e.to === selectedNode) {
        neighborIds.add(e.from);
        neighborIds.add(e.to);
      }
    });
  }

  // Inspector content
  const sel = selectedNode ? DIAG_NODES.find((n) => n.id === selectedNode) : null;
  const selZone = sel ? DIAG_ZONES.find((z) => z.id === sel.zone) : null;
  const inspectorLead = sel
    ? sel.sub
    : "Five trust zones, left to right. Each boundary is enforced by code, not convention.";
  const inspectorItems = sel && selZone
    ? [{ title: sel.name, body: sel.detail, color: selZone.color }]
    : DIAG_ZONES.map((z) => ({ title: z.label.toUpperCase(), body: z.desc, color: z.color }));

  return (
    <div style={{ border: "1px solid rgba(255,255,255,0.09)", background: "#0C0D0F" }}>
      {/* header */}
      <div
        style={{
          padding: "14px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.07)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          flexWrap: "wrap", gap: "12px",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: "11px", letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          TOPOLOGY · 14 NODES · 5 TRUST ZONES
        </span>
        <span
          style={{
            display: "flex", alignItems: "center", gap: "8px",
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
          LIVE TRAFFIC
        </span>
      </div>

      {/* body: diagram + inspector */}
      <div
        data-two-col
        style={{ display: "grid", gridTemplateColumns: "1.65fr 1fr" }}
      >
        {/* diagram */}
        <div
          style={{
            borderRight: "1px solid rgba(255,255,255,0.07)",
            padding: "26px",
            overflowX: "auto",
          }}
        >
          <div
            style={{
              position: "relative",
              width: "100%",
              minWidth: "560px",
              aspectRatio: `${SVG_W} / ${SVG_H}`,
            }}
          >
            {/* SVG edges + animated dots */}
            <svg
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              style={{
                position: "absolute", inset: 0,
                width: "100%", height: "100%",
                overflow: "visible",
              }}
            >
              <defs>
                <filter id="citadel-node-glow" x="-200%" y="-200%" width="500%" height="500%">
                  <feGaussianBlur stdDeviation="2.4" result="b" />
                  <feMerge>
                    <feMergeNode in="b" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {DIAG_EDGES.map((e, i) => {
                const isConnected = selectedNode && (e.from === selectedNode || e.to === selectedNode);
                const dim = selectedNode && !isConnected;
                const opacity = dim ? 0.08 : isConnected ? 0.9 : 0.4;
                const dotOpacity = dim ? 0.15 : 1;
                const strokeWidth = isConnected ? 2 : 1;
                const dur = 2.4 + (i % 5) * 0.5;
                const begin = -(i * 0.35);
                return (
                  <g key={e.id}>
                    <path
                      d={e.d}
                      fill="none"
                      stroke={e.color}
                      strokeWidth={strokeWidth}
                      opacity={opacity}
                    />
                    <circle r="3.2" fill={e.color} filter="url(#citadel-node-glow)" opacity={dotOpacity}>
                      <animateMotion
                        dur={`${dur}s`}
                        begin={`${begin}s`}
                        repeatCount="indefinite"
                        path={e.d}
                      />
                    </circle>
                  </g>
                );
              })}
            </svg>

            {/* zone labels */}
            {DIAG_ZONES.map((zn) => (
              <div
                key={zn.id}
                style={{
                  position: "absolute",
                  left: `${(zn.x / SVG_W) * 100}%`,
                  top: 0,
                  width: `calc(${(zn.w / SVG_W) * 100}% - 6px)`,
                  height: "30px",
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "9px", lineHeight: 1.35,
                  letterSpacing: "0.07em", textTransform: "uppercase",
                  color: zn.color,
                  pointerEvents: "none",
                }}
              >
                {zn.label}
              </div>
            ))}

            {/* nodes */}
            {DIAG_NODES.map((nd) => {
              const zone = DIAG_ZONES.find((z) => z.id === nd.zone)!;
              const isSel = selectedNode === nd.id;
              const isNeighbor = !!selectedNode && neighborIds.has(nd.id) && !isSel;
              const dim = !!selectedNode && !isSel && !isNeighbor;
              const borderColor = isSel || isNeighbor ? zone.color : "rgba(255,255,255,0.14)";
              return (
                <div
                  key={nd.id}
                  onClick={() => toggleNode(nd.id)}
                  style={{
                    position: "absolute",
                    left: `${(nd.x / SVG_W) * 100}%`,
                    top: `${(nd.y / SVG_H) * 100}%`,
                    width: `${(NODE_W / SVG_W) * 100}%`,
                    height: `${(NODE_H / SVG_H) * 100}%`,
                    border: `1px solid ${borderColor}`,
                    background: isSel ? "rgba(255,255,255,0.05)" : "#0A0B0C",
                    padding: "8px 10px",
                    boxSizing: "border-box",
                    cursor: "pointer",
                    transition: "all 0.25s ease",
                    opacity: dim ? 0.4 : 1,
                    boxShadow: isSel
                      ? `0 0 0 1px ${zone.color}, 0 0 18px -2px ${zone.color}`
                      : undefined,
                  }}
                  onMouseEnter={(e) => {
                    if (!isSel) (e.currentTarget as HTMLElement).style.borderColor = zone.color;
                    (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.035)";
                  }}
                  onMouseLeave={(ev) => {
                    if (!isSel) (ev.currentTarget as HTMLElement).style.borderColor = borderColor;
                    (ev.currentTarget as HTMLElement).style.background = isSel ? "rgba(255,255,255,0.05)" : "#0A0B0C";
                  }}
                >
                  <div
                    style={{
                      fontSize: "11.5px", fontWeight: 600,
                      color: "rgba(255,255,255,0.92)", lineHeight: 1.25,
                    }}
                  >
                    {nd.name}
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-geist-mono), monospace",
                      fontSize: "9px", letterSpacing: "0.03em",
                      color: zone.color, marginTop: "3px",
                    }}
                  >
                    {nd.sub}
                  </div>
                </div>
              );
            })}
          </div>

          {/* legend */}
          <div
            style={{
              display: "flex", gap: "22px",
              marginTop: "20px", flexWrap: "wrap",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px", color: "rgba(255,255,255,0.45)",
            }}
          >
            {DIAG_LEGEND.map((lg) => (
              <span key={lg.label} style={{ display: "inline-flex", alignItems: "center", gap: "7px" }}>
                <span
                  style={{
                    width: "14px", height: "1.5px",
                    background: lg.color, display: "inline-block",
                  }}
                />
                {lg.label}
              </span>
            ))}
          </div>
        </div>

        {/* inspector */}
        <div style={{ padding: "22px", display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              NODE INSPECTOR
            </span>
            {selectedNode && (
              <button
                onClick={clearSelection}
                className="btn-ghost"
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "10.5px", padding: "4px 9px", borderRadius: "5px",
                  cursor: "pointer",
                }}
              >
                ✕ clear
              </button>
            )}
          </div>

          <div style={{ fontSize: "13px", color: "rgba(255,255,255,0.42)", margin: "6px 0 10px", lineHeight: 1.6 }}>
            {inspectorLead}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {inspectorItems.map((ii) => (
              <div key={ii.title} style={{ borderLeft: `2px solid ${ii.color}`, paddingLeft: "14px" }}>
                <div
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "11.5px", fontWeight: 600,
                    letterSpacing: "0.04em", color: "rgba(255,255,255,0.9)",
                  }}
                >
                  {ii.title}
                </div>
                <div
                  style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.5)", lineHeight: 1.55, marginTop: "4px" }}
                >
                  {ii.body}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
