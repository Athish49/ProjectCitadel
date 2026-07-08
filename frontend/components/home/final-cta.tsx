"use client";

import Link from "next/link";

export function FinalCTA() {
  return (
    <section
      style={{
        marginTop: "160px",
        borderTop: "1px solid rgba(255,255,255,0.09)",
        background: "#0B0C0E",
      }}
    >
      <div
        style={{
          maxWidth: "1240px",
          margin: "0 auto",
          padding: "110px 32px",
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: "28px",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: "12px", letterSpacing: "0.1em",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          SYSTEM: LIVE — 48,317 ATTEMPTS LOGGED · CHAIN INTACT
        </div>

        <div
          style={{
            fontSize: "clamp(36px, 4vw, 56px)",
            fontWeight: 600,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
            color: "rgba(255,255,255,0.97)",
          }}
        >
          Try to break it.
        </div>

        <div
          style={{
            fontSize: "16px",
            color: "rgba(255,255,255,0.5)",
            maxWidth: "560px",
            lineHeight: 1.6,
          }}
        >
          Every payload you fire runs the production pipeline and writes real audit rows. If you find something the adversarial agent hasn't, it becomes a GitHub issue with your trace attached.
        </div>

        <div style={{ display: "flex", gap: "14px" }}>
          <Link
            href="/playground"
            className="btn-primary"
            style={{
              fontSize: "14.5px", fontWeight: 600,
              padding: "13px 24px", borderRadius: "7px",
            }}
          >
            Launch the playground
          </Link>
          <a
            href="https://github.com/Athish49/ProjectCitadel"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-outline"
            style={{
              fontSize: "14.5px", fontWeight: 500,
              padding: "13px 24px", borderRadius: "7px",
              fontFamily: "var(--font-geist-mono), monospace",
            }}
          >
            View source on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}
