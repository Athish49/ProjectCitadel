"use client";

import { Reveal } from "./reveal";
import { ARCH_STAGES, DATA_LABELS, AGENTS } from "@/lib/data/home";

export function ArchitectureSection() {
  return (
    <section
      id="architecture"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        1.0 — ARCHITECTURE
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
        <span style={{ color: "rgba(255,255,255,0.97)" }}>
          There is no LLM in the orchestrator.
        </span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}Untrusted input is quarantined, workflow decisions are plain code, and every privileged action requires a signed capability token the model cannot mint.
        </span>
      </Reveal>

      {/* pipeline diagram */}
      <Reveal
        style={{
          marginTop: "56px",
          border: "1px solid rgba(255,255,255,0.09)",
          background: "#0C0D0F",
          padding: "34px 30px 30px",
          overflowX: "auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "stretch", gap: 0, minWidth: "1080px" }}>
          {ARCH_STAGES.map((st) => (
            <div
              key={st.label}
              style={{ display: "flex", alignItems: "stretch", flex: st.flex }}
            >
              <div
                style={{
                  flex: 1,
                  border: `1px solid ${st.border}`,
                  background: "rgba(255,255,255,0.015)",
                  padding: "16px 16px 14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "10.5px", letterSpacing: "0.1em",
                    textTransform: "uppercase", color: st.labelColor,
                  }}
                >
                  {st.label}
                </div>
                <div
                  style={{
                    fontSize: "14.5px", fontWeight: 600,
                    color: "rgba(255,255,255,0.92)", lineHeight: 1.3,
                  }}
                >
                  {st.title}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  {st.items.map((it) => (
                    <div
                      key={it}
                      style={{
                        fontFamily: "var(--font-geist-mono), monospace",
                        fontSize: "11.5px", color: "rgba(255,255,255,0.5)", lineHeight: 1.45,
                      }}
                    >
                      {it}
                    </div>
                  ))}
                </div>
                <div
                  style={{
                    marginTop: "auto",
                    fontSize: "11.5px",
                    color: st.noteColor,
                    fontFamily: "var(--font-geist-mono), monospace",
                  }}
                >
                  {st.note}
                </div>
              </div>
              {st.arrow && (
                <div
                  style={{
                    display: "flex", alignItems: "center",
                    padding: "0 8px",
                    color: "rgba(62,207,142,0.7)",
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "14px",
                  }}
                >
                  {st.arrow}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* data label legend */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: "22px",
            marginTop: "26px", paddingTop: "20px",
            borderTop: "1px solid rgba(255,255,255,0.07)",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11px", letterSpacing: "0.1em",
              color: "rgba(255,255,255,0.4)",
            }}
          >
            DATA LABELS
          </span>
          {DATA_LABELS.map((dl) => (
            <span
              key={dl.name}
              style={{
                display: "inline-flex", alignItems: "center", gap: "7px",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12px", color: "rgba(255,255,255,0.6)",
              }}
            >
              <span style={{ width: "8px", height: "8px", background: dl.color, flexShrink: 0 }} />
              <span>{dl.name}</span>
              <span style={{ color: "rgba(255,255,255,0.28)" }}>{dl.note}</span>
            </span>
          ))}
        </div>
      </Reveal>

      {/* agent spec cards */}
      <Reveal
        data-agents-grid
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "1px",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.08)",
          marginTop: "20px",
        }}
      >
        {AGENTS.map((ag) => (
          <div
            key={ag.name}
            style={{
              background: "#0B0C0E",
              padding: "22px 22px 20px",
              display: "flex",
              flexDirection: "column",
              gap: "11px",
            }}
          >
            <div
              style={{
                display: "flex", alignItems: "baseline",
                justifyContent: "space-between", gap: "8px",
              }}
            >
              <div style={{ fontSize: "15px", fontWeight: 600, color: "rgba(255,255,255,0.94)" }}>
                {ag.name}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "10.5px", color: "rgba(255,255,255,0.38)",
                }}
              >
                {ag.model}
              </div>
            </div>
            <div style={{ fontSize: "13px", lineHeight: 1.55, color: "rgba(255,255,255,0.55)" }}>
              {ag.role}
            </div>
            <div
              style={{
                marginTop: "auto", paddingTop: "10px",
                borderTop: "1px solid rgba(255,255,255,0.06)",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11.5px", lineHeight: 1.6,
              }}
            >
              <div style={{ color: "rgba(255,255,255,0.45)" }}>{ag.access}</div>
              <div style={{ color: "#E5484D" }}>{ag.cannot}</div>
            </div>
          </div>
        ))}
      </Reveal>

      <Reveal
        style={{
          marginTop: "14px",
          fontSize: "13px",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        The quarantined parser is the most important single defense: it has{" "}
        <span
          style={{
            fontFamily: "var(--font-geist-mono), monospace",
            color: "rgba(255,255,255,0.7)",
          }}
        >
          zero tools
        </span>
        , emits only schema-validated JSON, and sees no data worth stealing. Actor LLMs never receive raw user text.
      </Reveal>
    </section>
  );
}
