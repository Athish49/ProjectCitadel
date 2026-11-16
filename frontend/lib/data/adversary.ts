/**
 * Static copy for the /adversary page — lifted verbatim from the approved
 * redesign prototype (Adversary.dc.html). Only the copy lives here; every
 * number on the page itself comes from the real SSE-backed hooks
 * (use-adversarial-stream / use-audit-stream), never from this file.
 */

export const ADVERSARY_HERO = {
  eyebrow: "Adversarial agent",
  headline: "A red team, attacking right now.",
  lead:
    "An autonomous agent attacks a sandboxed copy of the pipeline. Every attempt streams here, breaches included.",
  sandboxNote: "Sandboxed instance only. Never the live showcase.",
};

export const ADVERSARY_SECTIONS = {
  attacker: {
    eyebrow: "Attacker’s view",
    heading: "Every attempt, blocked or breached.",
  },
  defender: {
    eyebrow: "Defender’s view",
    heading: "The audit trail, as it is written.",
    lead: "Every agent action, tool call and security event across the pipeline.",
  },
};

export const ADVERSARY_COST_COPY = {
  label: "Monthly cost",
  cap: 50,
  costPerAttempt: 0.006,
  note:
    "Hard cap enforced by P11. A circuit breaker halts the agent on exhaustion. About $0.006 per attempt.",
};

export const ADVERSARY_PROFILE = {
  heading: "Agent profile",
  rows: [
    { label: "Model", value: "Claude Sonnet 4.6" },
    { label: "Isolation", value: "Separate container, sandboxed" },
    { label: "Reaches", value: "Adversarial-test API only" },
    { label: "Coverage", value: "79 attacks, 14 categories" },
  ],
  codeRefLabel: "adversarial/strategy.py →",
  codeRefHref:
    "https://github.com/Athish49/ProjectCitadel/blob/main/backend/adversarial_agent/strategy.py",
};

export const ADVERSARY_AUDIT_LEGEND =
  "AL audit log · SE security event · CT capability token";

export const ADVERSARY_CTA = {
  heading: "Every attempt traces to a pattern and a row.",
  primary: { label: "See the 79-row matrix", href: "/matrix" },
  secondary: { label: "Read the 12 patterns", href: "/patterns" },
};
