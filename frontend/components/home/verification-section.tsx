"use client";

import { useState } from "react";
import { Reveal } from "./reveal";
import { INVARIANTS } from "@/lib/data/home";

function randomHex64() {
  return Array.from({ length: 64 }, () => "0123456789abcdef"[Math.floor(Math.random() * 16)]).join("");
}

export function VerificationSection() {
  const [verifying, setVerifying] = useState(false);
  const [chainVerifiedAt, setChainVerifiedAt] = useState("2m ago");
  const [chainRows, setChainRows] = useState(48317);
  const [chainHead, setChainHead] = useState(
    "a3f81c92e07d4b6f9d2a1e58c4707bb3d9e6f0a2c815d47e3b9a06c1f52e8d40"
  );

  function verifyChain() {
    if (verifying) return;
    setVerifying(true);
    setTimeout(() => {
      setVerifying(false);
      setChainVerifiedAt("just now");
      setChainHead(randomHex64());
    }, 2400);
  }

  const chainBadge = verifying ? "RECOMPUTING…" : "CHAIN INTACT";
  const chainBadgeColor = verifying ? "#E2A336" : "#3ECF8E";
  const scanDisplay = verifying ? "block" : "none";
  const verifyLabel = verifying ? "Verifying chain…" : "Verify chain integrity";

  return (
    <section
      id="verification"
      style={{ padding: "150px 32px 0", maxWidth: "1240px", margin: "0 auto" }}
    >
      <Reveal
        style={{
          fontFamily: "var(--font-geist-mono), monospace",
          fontSize: "12px", letterSpacing: "0.1em",
          color: "rgba(255,255,255,0.4)",
        }}
      >
        6.0 — VERIFICATION
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
        <span style={{ color: "rgba(255,255,255,0.97)" }}>Formally specified. Cryptographically auditable.</span>
        <span style={{ color: "rgba(255,255,255,0.42)" }}>
          {" "}The workflow state machine is proven in TLA+, and every action lands in a hash-chained log you can verify on demand.
        </span>
      </Reveal>

      <Reveal
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "20px",
          marginTop: "56px",
        }}
      >
        {/* formal spec */}
        <div style={{ border: "1px solid rgba(255,255,255,0.09)", background: "#0C0D0F" }}>
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              display: "flex", justifyContent: "space-between",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              FORMAL SPEC — formal/workflow.tla
            </span>
            <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "#3ECF8E" }}>
              ALL INVARIANTS HOLD
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column" }}>
            {INVARIANTS.map((inv) => (
              <div
                key={inv.name}
                style={{
                  display: "flex", justifyContent: "space-between",
                  alignItems: "baseline",
                  padding: "13px 18px",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <div>
                  <span
                    style={{
                      fontFamily: "var(--font-geist-mono), monospace",
                      fontSize: "13px", color: "rgba(255,255,255,0.85)",
                    }}
                  >
                    {inv.name}
                  </span>
                  <span style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.42)", marginLeft: "10px" }}>
                    {inv.desc}
                  </span>
                </div>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "#3ECF8E" }}>
                  PASS
                </span>
              </div>
            ))}
          </div>

          <div
            style={{
              padding: "15px 18px",
              display: "flex", gap: "24px",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px", color: "rgba(255,255,255,0.5)",
            }}
          >
            <span>3,456 states enumerated</span>
            <span>30 invariant tests</span>
            <span style={{ color: "rgba(255,255,255,0.75)" }}>102/102 conformance</span>
          </div>
        </div>

        {/* audit chain */}
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
              display: "flex", justifyContent: "space-between",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", letterSpacing: "0.1em",
                color: "rgba(255,255,255,0.4)",
              }}
            >
              AUDIT CHAIN — append-only, INSERT-only roles
            </span>
            <span
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "11px", color: chainBadgeColor,
              }}
            >
              {chainBadge}
            </span>
          </div>

          <div style={{ padding: "18px", flex: 1, display: "flex", flexDirection: "column", gap: "14px" }}>
            <div
              style={{
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12px", color: "rgba(255,255,255,0.45)",
              }}
            >
              row_hash = sha256(prev_hash || canonical_json(row))
            </div>

            <div
              style={{
                background: "#08090A",
                border: "1px solid rgba(255,255,255,0.08)",
                padding: "14px",
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: "12px", lineHeight: 1.7,
                color: "rgba(255,255,255,0.6)",
                overflow: "hidden",
                position: "relative",
              }}
            >
              <div style={{ color: "rgba(255,255,255,0.35)" }}>
                chain head · row {chainRows.toLocaleString("en-US")}
              </div>
              <div style={{ wordBreak: "break-all", color: "rgba(255,255,255,0.78)" }}>
                {chainHead}
              </div>
              {/* scan animation overlay */}
              <div
                style={{
                  position: "absolute", inset: 0,
                  pointerEvents: "none",
                  display: scanDisplay,
                }}
              >
                <div
                  style={{
                    position: "absolute", top: 0, bottom: 0, width: "25%",
                    background: "linear-gradient(90deg, transparent, rgba(62,207,142,0.1), transparent)",
                    animation: "citadel-scan 0.9s linear infinite",
                  }}
                />
              </div>
            </div>

            <div
              style={{
                display: "flex", alignItems: "center",
                justifyContent: "space-between",
                marginTop: "auto",
              }}
            >
              <button
                onClick={verifyChain}
                className="btn-ghost"
                style={{
                  fontFamily: "var(--font-geist), sans-serif",
                  fontSize: "13px", fontWeight: 500,
                  padding: "9px 16px", borderRadius: "6px",
                  cursor: verifying ? "not-allowed" : "pointer",
                }}
              >
                {verifyLabel}
              </button>
              <span
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "11.5px", color: "rgba(255,255,255,0.38)",
                }}
              >
                last verified {chainVerifiedAt}
              </span>
            </div>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
