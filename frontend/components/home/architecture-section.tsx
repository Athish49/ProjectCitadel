"use client";

import { useEffect, useState } from "react";
import { SectionHeader } from "./section-header";
import { ARCH_STAGES } from "@/lib/data/home";

export function ArchitectureSection() {
  const [stage, setStage] = useState(0);
  const [pinned, setPinned] = useState(false);

  // Auto-rotate through stages every 3.6s until the visitor picks one.
  useEffect(() => {
    if (pinned) return;
    const id = setInterval(() => setStage((s) => (s + 1) % ARCH_STAGES.length), 3600);
    return () => clearInterval(id);
  }, [pinned]);

  function pick(i: number) {
    setStage(i);
    setPinned(true);
  }

  const current = ARCH_STAGES[stage];

  return (
    <section id="architecture" style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(88px,10vw,150px) 32px 0" }}>
      <SectionHeader
        eyebrow="01 — Architecture"
        title="Every layer assumes the last one failed."
        lead="Untrusted input is quarantined. Code decides the workflow. Privileged actions need a signed token no model can mint."
        more={{ label: "Full architecture", href: "/architecture" }}
      />

      <div data-rv className="panel" style={{ marginTop: "48px" }}>
        <div style={{ height: "2px", background: "rgba(255,255,255,0.06)" }}>
          <div
            style={{
              height: "2px",
              background: "#f4f4f5",
              width: `${((stage + 1) / ARCH_STAGES.length) * 100}%`,
              transition: "width .6s cubic-bezier(.2,.7,.2,1)",
            }}
          />
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))",
            gap: "1px",
            background: "rgba(255,255,255,0.08)",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {ARCH_STAGES.map((st, i) => {
            const active = i === stage;
            return (
              <button
                key={st.name}
                type="button"
                onClick={() => pick(i)}
                aria-pressed={active}
                style={{
                  appearance: "none",
                  font: "inherit",
                  color: "inherit",
                  textAlign: "left",
                  cursor: "pointer",
                  border: 0,
                  padding: "22px 20px 24px",
                  minHeight: "44px",
                  transition: "background .25s",
                  background: active ? "#131417" : "#0a0b0c",
                }}
              >
                <span
                  className="mono"
                  style={{
                    display: "block",
                    fontSize: "11px",
                    letterSpacing: "0.12em",
                    color: active ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.55)",
                  }}
                >
                  0{i + 1} · {st.tag}
                </span>
                <span
                  style={{
                    display: "block",
                    marginTop: "10px",
                    fontSize: "17px",
                    fontWeight: 500,
                    color: active ? "#ffffff" : "rgba(255,255,255,0.7)",
                  }}
                >
                  {st.name}
                </span>
              </button>
            );
          })}
        </div>

        <div
          style={{
            padding: "32px 28px 34px",
            display: "flex",
            flexWrap: "wrap",
            gap: "24px 56px",
            alignItems: "center",
            justifyContent: "space-between",
            minHeight: "132px",
          }}
        >
          <p
            style={{
              margin: 0,
              flex: "1 1 380px",
              fontSize: "clamp(18px,1.7vw,22px)",
              lineHeight: 1.4,
              letterSpacing: "-0.01em",
              maxWidth: "560px",
            }}
          >
            {current.line}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", flex: "1 1 340px", justifyContent: "flex-start" }}>
            {current.facts.map((f) => (
              <span
                key={f}
                className="mono"
                style={{
                  fontSize: "12px",
                  padding: "7px 11px",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: "4px",
                  color: "rgba(255,255,255,0.8)",
                }}
              >
                {f}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
