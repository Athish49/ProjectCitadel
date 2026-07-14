"use client";

import { useState } from "react";

export function Footer() {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText("grathish49@gmail.com");
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  }

  return (
    <footer style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}>
      <div
        style={{
          maxWidth: "1240px",
          margin: "0 auto",
          padding: "18px 32px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "nowrap",
          gap: "24px",
        }}
      >
        {/* Left */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: "10px",
            minWidth: 0, overflow: "hidden",
          }}
        >
          <span
            style={{
              display: "inline-flex", flexShrink: 0,
              width: "18px", height: "18px",
              border: "1.5px solid rgba(255,255,255,0.35)",
              alignItems: "center", justifyContent: "center",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "9px", color: "rgba(255,255,255,0.5)",
            }}
          >
            C
          </span>
          <span
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px",
              color: "rgba(255,255,255,0.42)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            Project Citadel · Enterprise agentic AI, hardened by design
          </span>
        </div>

        {/* Right */}
        <div
          style={{
            display: "flex", alignItems: "center", gap: "10px",
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: "12px", color: "rgba(255,255,255,0.42)",
            flexShrink: 0, whiteSpace: "nowrap",
          }}
        >
          <span>Built by Athish Gopal Rajesh</span>
          <span style={{ color: "rgba(255,255,255,0.18)" }}>|</span>
          <a
            href="https://athishgopalrajesh.com"
            target="_blank" rel="noopener noreferrer"
            className="link-dim" style={{ fontSize: "12px" }}
          >
            Portfolio &amp; about
          </a>
          <span style={{ color: "rgba(255,255,255,0.18)" }}>·</span>
          <a
            href="https://linkedin.com/in/athish-gopal-rajesh"
            target="_blank" rel="noopener noreferrer"
            className="link-dim" style={{ fontSize: "12px" }}
          >
            LinkedIn
          </a>
          <span style={{ color: "rgba(255,255,255,0.18)" }}>·</span>
          <button
            onClick={copy}
            className="link-dim"
            style={{
              background: "none", border: "none", padding: 0,
              cursor: "pointer",
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px",
            }}
          >
            grathish49@gmail.com
          </button>
          <button
            onClick={copy}
            title={copied ? "Copied!" : "Copy email"}
            style={{
              background: "none", border: "none", padding: 0,
              cursor: "pointer", display: "inline-flex", alignItems: "center",
              color: copied ? "#3ECF8E" : "rgba(255,255,255,0.35)",
              transition: "color 0.15s",
            }}
          >
            {copied ? (
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <path d="M3 8l3.5 3.5L13 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <rect x="5" y="5" width="9" height="9" rx="1.2" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M11 5V3.2A1.2 1.2 0 0 0 9.8 2H3.2A1.2 1.2 0 0 0 2 3.2v6.6A1.2 1.2 0 0 0 3.2 11H5" stroke="currentColor" strokeWidth="1.3"/>
              </svg>
            )}
          </button>
        </div>
      </div>
    </footer>
  );
}
