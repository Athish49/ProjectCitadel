"use client";

import { useState } from "react";

const EMAIL = "grathish49@gmail.com";

export function FooterEmail() {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(EMAIL);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable; fail silently.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={`Copy email address ${EMAIL} to clipboard`}
      className="nl"
      style={{
        fontSize: "13px",
        padding: 0,
        background: "none",
        border: "none",
        cursor: "pointer",
        color: copied ? "var(--ok)" : undefined,
      }}
    >
      {copied ? "Copied" : EMAIL}
    </button>
  );
}
