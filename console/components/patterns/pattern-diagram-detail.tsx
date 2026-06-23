"use client";

/**
 * Detail-page animated diagrams for P1–P12.
 * ViewBox: 0 0 560 200.  Play-once on mount; no Infinity loops.
 * Each marker id is suffixed with the pattern id (e.g. "p1d-ok") to avoid
 * document-scope SVG id collisions when multiple diagrams share a page.
 */

import type { ReactElement } from "react";
import { useReducedMotion, motion } from "framer-motion";
import type { PatternId } from "@/lib/types/showcase";

// ── Shared design tokens ───────────────────────────────────────────────────────
const C = {
  bg:     "#0A0E14",
  bg1:    "#0F141B",
  bg2:    "#161C24",
  bg3:    "#1E2632",
  fg0:    "#E6EDF3",
  fg1:    "#B0BAC6",
  fg2:    "#6E7B8C",
  fg3:    "#3D4856",
  ok:     "#4ADE80",
  warn:   "#F5B056",
  alert:  "#F25B5B",
  blue:   "#5BB5F2",
  purple: "#C879FF",
};

// ── Shared transition factory ──────────────────────────────────────────────────
function useTrans(base: number, reduced: boolean) {
  if (reduced) return (_delay: number) => ({ duration: 0 });
  return (delay: number) => ({ duration: base, delay, ease: "easeOut" as const });
}

function Arrow({ id, color }: { id: string; color: string }) {
  return (
    <defs>
      <marker id={id} markerWidth="5" markerHeight="5" refX="4" refY="2.5" orient="auto">
        <path d="M0,0 L0,5 L5,2.5 z" fill={color} />
      </marker>
    </defs>
  );
}

// ── P1 — Dual-LLM Separation ──────────────────────────────────────────────────
function P1Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.4, rm);

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Attack input */}
      <rect x="8" y="70" width="112" height="60" rx="3" fill={C.bg2} stroke={C.warn} strokeWidth="1.5" />
      <text x="64" y="90" textAnchor="middle" fill={C.warn} fontSize="7.5" fontFamily="monospace" fontWeight="600">ATTACK INPUT</text>
      <text x="64" y="104" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace">&quot;ignore all instructions&quot;</text>
      <text x="64" y="116" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">label: UNTRUSTED</text>

      {/* Arrow in */}
      <motion.path d="M120 100 L150 100" stroke={C.warn} strokeWidth="1.5" markerEnd="url(#p1d-warn)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(0.4)} />

      {/* Parser box */}
      <rect x="150" y="32" width="140" height="136" rx="4" fill={C.bg} stroke={C.alert} strokeWidth="1.5" strokeDasharray="6 3" />
      <text x="220" y="52" textAnchor="middle" fill={C.alert} fontSize="7" fontFamily="monospace" fontWeight="600">QUARANTINED PARSER</text>
      <text x="220" y="64" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">no tools · no DB access</text>
      <rect x="162" y="72" width="116" height="30" rx="2" fill={C.bg2} stroke={C.bg3} />
      <text x="220" y="86" textAnchor="middle" fill={C.fg1} fontSize="6" fontFamily="monospace">Claude Haiku 4.5</text>
      <text x="220" y="97" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">schema-enforced output only</text>
      <text x="220" y="148" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">raw text is never forwarded</text>

      {/* Trust boundary */}
      <line x1="304" y1="10" x2="304" y2="190" stroke={C.bg3} strokeWidth="1" strokeDasharray="5 3" />
      <text x="304" y="9" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">trust boundary</text>

      {/* Arrow out (JSON crosses boundary) */}
      <motion.path d="M290 100 L336 100" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p1d-ok)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.0)} />

      {/* JSON envelope */}
      <motion.rect x="336" y="62" width="136" height="76" rx="3"
        fill="#071407" stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.1)} />
      <motion.text x="404" y="82" textAnchor="middle" fill={C.ok} fontSize="7" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.2)}>STRUCTURED JSON</motion.text>
      <motion.text x="404" y="96" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.3)}>{`{ "intent": "policy_query",`}</motion.text>
      <motion.text x="404" y="108" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.35)}>{`  "fields": { ... } }`}</motion.text>
      <motion.text x="404" y="124" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.4)}>schema-validated · label: PERSONAL</motion.text>

      {/* Arrow → actor */}
      <motion.path d="M472 100 L506 100" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p1d-ok2)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.8)} />

      {/* Actor box */}
      <motion.rect x="506" y="70" width="46" height="60" rx="3"
        fill={C.bg2} stroke={C.blue} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)} />
      <motion.text x="529" y="95" textAnchor="middle" fill={C.blue} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>ACTOR</motion.text>
      <motion.text x="529" y="108" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>Sonnet</motion.text>
      <motion.text x="529" y="118" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>+ tools</motion.text>

      <text x="280" y="188" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">
        attack payload never reaches privileged LLM context
      </text>

      <Arrow id="p1d-warn" color={C.warn} />
      <Arrow id="p1d-ok"   color={C.ok}   />
      <Arrow id="p1d-ok2"  color={C.ok}   />
    </svg>
  );
}

// ── P2 — Deterministic Orchestration ──────────────────────────────────────────
function P2Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.3, rm);

  const stages = ["INTAKE", "IDENTITY", "PROCESSING", "DECIDED", "SETTLED"];
  const cx = [56, 168, 280, 392, 504];
  const colors = [C.blue, C.warn, C.warn, C.purple, C.ok];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* State nodes */}
      {stages.map((s, i) => (
        <motion.g key={s} initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }}
          style={{ transformOrigin: `${cx[i]}px 80px` }}
          transition={t(i * 0.25)}>
          <circle cx={cx[i]} cy="80" r="34" fill={C.bg2} stroke={colors[i]} strokeWidth="1.5" />
          <text x={cx[i]} y="76" textAnchor="middle" fill={colors[i]} fontSize="6.5" fontFamily="monospace" fontWeight="600">{s}</text>
          <text x={cx[i]} y="88" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">
            {["open", "pending", "active", "complete", "closed"][i]}
          </text>
        </motion.g>
      ))}

      {/* Transition arrows */}
      {[0, 1, 2, 3].map((i) => (
        <motion.path key={i}
          d={`M${cx[i] + 34} 80 L${cx[i + 1] - 34} 80`}
          stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p2d-ok)"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.4 + i * 0.3)}
        />
      ))}

      {/* Code-decides badges */}
      {[0, 1, 2].map((i) => (
        <motion.text key={i} x={(cx[i] + cx[i + 1]) / 2} y="54"
          textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6 + i * 0.3)}>
          code checks DB
        </motion.text>
      ))}

      {/* LLM-rejected arrow attempt */}
      <motion.path d="M392 44 Q448 8 504 44" stroke={C.alert} strokeWidth="1.5" strokeDasharray="5 3"
        fill="none" markerEnd="url(#p2d-alert)"
        initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.7 }} transition={t(2.5)} />
      <motion.text x="448" y="14" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.7)}>LLM: &quot;skip to SETTLED&quot;</motion.text>
      <motion.text x="448" y="26" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>→ REJECTED + audit row</motion.text>

      <text x="280" y="145" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">
        orchestrator is plain code — no LLM in the transition path
      </text>
      <text x="280" y="158" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">
        LLM may propose · code decides
      </text>

      {/* ESCALATED / DENIED branches */}
      <motion.path d="M392 114 L392 148 L450 148" stroke={C.alert} strokeWidth="1" markerEnd="url(#p2d-alert2)"
        initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.7 }} transition={t(3.2)} />
      <motion.text x="465" y="152" fill={C.alert} fontSize="6" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.3)}>ESCALATED / DENIED</motion.text>

      <Arrow id="p2d-ok"    color={C.ok}    />
      <Arrow id="p2d-alert"  color={C.alert} />
      <Arrow id="p2d-alert2" color={C.alert} />
    </svg>
  );
}

// ── P3 — Information Flow Control ─────────────────────────────────────────────
function P3Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.35, rm);

  const tiers = [
    { label: "SECRET",       color: C.purple, y: 24,  note: "fraud scores · SSN · bank details" },
    { label: "CONFIDENTIAL", color: C.alert,  y: 60,  note: "policy details · claim amounts" },
    { label: "PERSONAL",     color: C.warn,   y: 96,  note: "name · email · claim status" },
    { label: "PUBLIC",       color: C.ok,     y: 132, note: "FAQs · policy summaries" },
  ];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Label tier bars */}
      {tiers.map((tier, i) => (
        <motion.g key={tier.label} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
          transition={t(i * 0.2)}>
          <rect x="8" y={tier.y} width="200" height="28" rx="3" fill={C.bg2} stroke={tier.color} strokeWidth="1.5" />
          <text x="22" y={tier.y + 13} fill={tier.color} fontSize="7.5" fontFamily="monospace" fontWeight="600">{tier.label}</text>
          <text x="22" y={tier.y + 23} fill={C.fg3} fontSize="5" fontFamily="monospace">{tier.note}</text>
        </motion.g>
      ))}

      {/* Sensitivity arrow label */}
      <text x="3" y="100" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        transform="rotate(-90 3 100)">sensitivity ↑</text>

      {/* Vertical divider */}
      <line x1="220" y1="10" x2="220" y2="190" stroke={C.bg3} strokeWidth="1" strokeDasharray="4 2" />

      {/* Tool call example */}
      <motion.rect x="228" y="16" width="188" height="52" rx="3"
        fill={C.bg2} stroke={C.purple} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0)}>
      </motion.rect>
      <motion.text x="322" y="31" textAnchor="middle" fill={C.purple} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.1)}>score_fraud() returns</motion.text>
      <motion.text x="322" y="44" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.2)}>{`{ decision: "FLAG", score: 0.87 }`}</motion.text>
      <motion.text x="322" y="57" textAnchor="middle" fill={C.purple} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.2)}>label: SECRET</motion.text>

      {/* Strip arrow */}
      <motion.path d="M322 68 L322 94" stroke={C.fg3} strokeWidth="1.5" markerEnd="url(#p3d-fg)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.5)} />
      <motion.text x="340" y="84" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>actor runtime strips score</motion.text>

      {/* LLM context */}
      <motion.rect x="228" y="94" width="188" height="44" rx="3"
        fill={C.bg2} stroke={C.alert} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.7)}>
      </motion.rect>
      <motion.text x="322" y="110" textAnchor="middle" fill={C.alert} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.8)}>actor LLM sees</motion.text>
      <motion.text x="322" y="124" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>{`{ decision: "FLAG" }  label: CONFIDENTIAL`}</motion.text>

      {/* Egress kill */}
      <motion.rect x="228" y="148" width="188" height="36" rx="3"
        fill="#1a0505" stroke={C.alert} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.2)}>
      </motion.rect>
      <motion.text x="322" y="163" textAnchor="middle" fill={C.alert} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.3)}>EGRESS: SECRET → replace</motion.text>
      <motion.text x="322" y="176" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.4)}>SECRET content never reaches customer</motion.text>

      {/* Right: tool min-label annotations */}
      <motion.text x="430" y="50" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.6)}>tools declare min label</motion.text>
      <motion.text x="430" y="64" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.7)}>insufficient → denied</motion.text>

      <Arrow id="p3d-fg" color={C.fg3} />
    </svg>
  );
}

// ── P4 — Capability-Scoped Tools ──────────────────────────────────────────────
function P4Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.35, rm);

  const checks = [
    "① signature valid (Ed25519)",
    "② agent_id matches caller",
    "③ tool matches request",
    "④ scope matches params",
    "⑤ expires_at in future",
  ];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Orchestrator */}
      <rect x="8" y="64" width="88" height="72" rx="3" fill={C.bg2} stroke={C.blue} strokeWidth="1.5" />
      <text x="52" y="84" textAnchor="middle" fill={C.blue} fontSize="7" fontFamily="monospace" fontWeight="600">ORCH</text>
      <text x="52" y="96" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">mints token</text>
      <text x="52" y="108" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">signs Ed25519</text>

      {/* Token badge */}
      <motion.rect x="108" y="40" width="140" height="120" rx="3"
        fill="#0d0720" stroke={C.purple} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.5)}>
      </motion.rect>
      <motion.text x="178" y="57" textAnchor="middle" fill={C.purple} fontSize="7" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.6)}>CAPABILITY TOKEN</motion.text>
      {[
        "agent_id: claims_processor",
        "tool:     score_fraud",
        `scope:    { claim_id: "CLM-123" }`,
        "expires:  60s",
        "sig:      Ed25519(...)",
      ].map((line, i) => (
        <motion.text key={i} x="118" y={72 + i * 14} fill={i === 4 ? C.purple : C.fg2}
          fontSize="5.5" fontFamily="monospace"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.7 + i * 0.1)}>
          {line}
        </motion.text>
      ))}

      {/* Arrow token → registry */}
      <motion.path d="M248 100 L284 100" stroke={C.purple} strokeWidth="1.5" markerEnd="url(#p4d-pur)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.4)} />

      {/* Registry */}
      <motion.rect x="284" y="32" width="164" height="136" rx="3"
        fill={C.bg2} stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.5)}>
      </motion.rect>
      <motion.text x="366" y="50" textAnchor="middle" fill={C.ok} fontSize="7" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>REGISTRY (5 checks)</motion.text>
      {checks.map((c, i) => (
        <motion.text key={i} x="294" y={64 + i * 16} fill={C.fg1} fontSize="5.5" fontFamily="monospace"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.7 + i * 0.15)}>
          {c}
        </motion.text>
      ))}

      {/* → ALLOWED */}
      <motion.path d="M448 100 L492 100" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p4d-ok)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.6)} />
      <motion.rect x="492" y="76" width="60" height="48" rx="3"
        fill={C.bg2} stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.7)}>
      </motion.rect>
      <motion.text x="522" y="97" textAnchor="middle" fill={C.ok} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.8)}>TOOL</motion.text>
      <motion.text x="522" y="110" textAnchor="middle" fill={C.ok} fontSize="6" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.8)}>✓ ALLOWED</motion.text>

      {/* Bad token path */}
      <motion.text x="366" y="180" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.0)}>
        bad sig → DENIED + security_event audit row
      </motion.text>

      <Arrow id="p4d-pur" color={C.purple} />
      <Arrow id="p4d-ok"  color={C.ok}     />
    </svg>
  );
}

// ── P5 — Sandboxed File Processing ────────────────────────────────────────────
function P5Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.4, rm);

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Input files */}
      <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.2)}>
        <rect x="8" y="56" width="80" height="36" rx="3" fill={C.bg2} stroke={C.warn} strokeWidth="1.5" />
        <text x="48" y="72" textAnchor="middle" fill={C.warn} fontSize="6.5" fontFamily="monospace" fontWeight="600">PDF</text>
        <text x="48" y="83" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">adversarial</text>
      </motion.g>
      <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.35)}>
        <rect x="8" y="104" width="80" height="36" rx="3" fill={C.bg2} stroke={C.warn} strokeWidth="1.5" />
        <text x="48" y="120" textAnchor="middle" fill={C.warn} fontSize="6.5" fontFamily="monospace" fontWeight="600">IMAGE</text>
        <text x="48" y="131" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">untrusted</text>
      </motion.g>

      {/* Arrow → container */}
      <motion.path d="M88 74 L136 100 L88 126" stroke={C.warn} strokeWidth="1.5" fill="none" markerEnd="url(#p5d-warn)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(0.6)} />

      {/* Container boundary */}
      <motion.rect x="136" y="16" width="280" height="168" rx="5"
        fill={C.bg} stroke={C.alert} strokeWidth="2" strokeDasharray="8 4"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.8)}>
      </motion.rect>
      <motion.text x="276" y="34" textAnchor="middle" fill={C.alert} fontSize="7" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.9)}>SANDBOX CONTAINER</motion.text>

      {/* Isolation properties */}
      {[
        "--network=none",
        "read-only rootfs",
        "drop all capabilities",
        "ephemeral /tmp scratch",
      ].map((prop, i) => (
        <motion.text key={prop} x="154" y={50 + i * 16} fill={C.fg2} fontSize="5.5" fontFamily="monospace"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0 + i * 0.15)}>
          ✓ {prop}
        </motion.text>
      ))}

      {/* Parser process inside */}
      <motion.rect x="248" y="80" width="144" height="80" rx="3"
        fill={C.bg2} stroke={C.bg3} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.7)}>
      </motion.rect>
      <motion.text x="320" y="100" textAnchor="middle" fill={C.fg1} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.8)}>PARSER PROCESS</motion.text>
      <motion.text x="320" y="114" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>pdfplumber / pytesseract</motion.text>
      <motion.text x="320" y="126" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>JS/exec/form → REJECT</motion.text>
      <motion.text x="320" y="138" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>hidden text → flag + audit</motion.text>
      <motion.text x="320" y="150" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>extracted text → UNTRUSTED</motion.text>

      {/* Arrow out of container */}
      <motion.path d="M416 130 L468 130" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p5d-ok)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.4)} />
      <motion.text x="490" y="120" textAnchor="middle" fill={C.ok} fontSize="6" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.5)}>text out</motion.text>
      <motion.text x="490" y="132" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.5)}>→ P1 parser</motion.text>

      {/* No egress: crossed arrow */}
      <motion.path d="M416 60 L546 60" stroke={C.fg3} strokeWidth="1" strokeDasharray="4 2"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.6)} />
      <motion.line x1="536" y1="52" x2="546" y2="68" stroke={C.alert} strokeWidth="2"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.8)} />
      <motion.line x1="536" y1="68" x2="546" y2="52" stroke={C.alert} strokeWidth="2"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.9)} />
      <motion.text x="490" y="50" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.0)}>no network egress</motion.text>

      <Arrow id="p5d-warn" color={C.warn} />
      <Arrow id="p5d-ok"   color={C.ok}   />
    </svg>
  );
}

// ── P6 — Vision Pre-Redaction ─────────────────────────────────────────────────
function P6Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.35, rm);

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Original image */}
      <motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.2)}>
        <rect x="8" y="50" width="72" height="88" rx="3" fill={C.bg2} stroke={C.warn} strokeWidth="1.5" />
        <text x="44" y="70" textAnchor="middle" fill={C.warn} fontSize="6.5" fontFamily="monospace" fontWeight="600">IMAGE</text>
        {/* Fake image content */}
        {[76, 84, 92].map((y) => (
          <line key={y} x1="18" x2="72" y1={y} y2={y} stroke={C.fg3} strokeWidth="1" opacity="0.4" />
        ))}
        {/* Overlay text on image */}
        <rect x="16" y="100" width="54" height="10" rx="1" fill="none" stroke={C.alert} strokeWidth="1" strokeDasharray="3 1" />
        <text x="43" y="108" textAnchor="middle" fill={C.alert} fontSize="5" fontFamily="monospace">ignore instructions</text>
        <text x="44" y="130" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">embedded text</text>
      </motion.g>

      {/* Arrow → OCR */}
      <motion.path d="M80 94 L112 94" stroke={C.warn} strokeWidth="1.5" markerEnd="url(#p6d-warn)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(0.5)} />

      {/* OCR pass */}
      <motion.rect x="112" y="50" width="88" height="88" rx="3" fill={C.bg2} stroke={C.blue} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.6)} />
      <motion.text x="156" y="70" textAnchor="middle" fill={C.blue} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.7)}>OCR PASS</motion.text>
      <motion.text x="156" y="83" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.8)}>pytesseract</motion.text>
      <motion.text x="156" y="96" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.9)}>detect text</motion.text>
      <motion.text x="156" y="108" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.9)}>bounding boxes</motion.text>
      <motion.text x="156" y="120" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0)}>text → UNTRUSTED</motion.text>
      <motion.text x="156" y="132" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0)}>stream → P1</motion.text>

      {/* Arrow → Redact */}
      <motion.path d="M200 94 L232 94" stroke={C.blue} strokeWidth="1.5" markerEnd="url(#p6d-blue)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.3)} />

      {/* Pixel redact */}
      <motion.rect x="232" y="50" width="100" height="88" rx="3" fill={C.bg2} stroke={C.purple} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.4)} />
      <motion.text x="282" y="70" textAnchor="middle" fill={C.purple} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.5)}>PIXEL BLUR</motion.text>
      <motion.text x="282" y="83" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>bbox → opaque block</motion.text>
      {/* Redaction block visual */}
      <motion.rect x="244" y="94" width="76" height="14" rx="1" fill={C.alert} opacity="0.7"
        initial={{ scaleX: 0 }} animate={{ scaleX: 1 }}
        style={{ transformOrigin: "244px 101px" }}
        transition={t(1.8)} />
      <motion.text x="282" y="122" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>text region erased</motion.text>
      <motion.text x="282" y="133" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>before vision model</motion.text>

      {/* Arrow → Redacted image → Vision model */}
      <motion.path d="M332 94 L368 94" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p6d-ok)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.2)} />

      {/* Redacted image */}
      <motion.rect x="368" y="50" width="72" height="88" rx="3" fill={C.bg2} stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.3)} />
      <motion.text x="404" y="70" textAnchor="middle" fill={C.ok} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.4)}>REDACTED</motion.text>
      {[76, 84, 92].map((y) => (
        <motion.line key={y} x1="378" x2="432" y1={y} y2={y} stroke={C.fg3} strokeWidth="1" opacity="0.4"
          initial={{ opacity: 0 }} animate={{ opacity: 0.4 }} transition={t(2.4)} />
      ))}
      <motion.rect x="376" y="98" width="54" height="10" rx="1" fill={C.alert} opacity="0.8"
        initial={{ opacity: 0 }} animate={{ opacity: 0.8 }} transition={t(2.5)} />

      {/* Arrow → Vision model */}
      <motion.path d="M440 94 L476 94" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p6d-ok2)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.7)} />

      <motion.rect x="476" y="60" width="76" height="68" rx="3" fill={C.bg2} stroke={C.blue} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.8)} />
      <motion.text x="514" y="87" textAnchor="middle" fill={C.blue} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>VISION</motion.text>
      <motion.text x="514" y="99" textAnchor="middle" fill={C.blue} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>MODEL</motion.text>
      <motion.text x="514" y="114" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.0)}>clean image</motion.text>

      <text x="280" y="158" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">
        OCR text travels as UNTRUSTED through P1 · injected text is never seen by vision model
      </text>

      <Arrow id="p6d-warn" color={C.warn}   />
      <Arrow id="p6d-blue" color={C.blue}   />
      <Arrow id="p6d-ok"   color={C.ok}     />
      <Arrow id="p6d-ok2"  color={C.ok}     />
    </svg>
  );
}

// ── P7 — DB-Enforced Tenancy (RLS) ────────────────────────────────────────────
function P7Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.35, rm);

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Agent */}
      <rect x="8" y="72" width="80" height="56" rx="3" fill={C.bg2} stroke={C.blue} strokeWidth="1.5" />
      <text x="48" y="92" textAnchor="middle" fill={C.blue} fontSize="6.5" fontFamily="monospace" fontWeight="600">AGENT</text>
      <text x="48" y="104" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">role:</text>
      <text x="48" y="115" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">agent_claims</text>

      {/* Arrow → Postgres */}
      <motion.path d="M88 100 L132 100" stroke={C.blue} strokeWidth="1.5" markerEnd="url(#p7d-blue)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(0.4)} />
      <motion.text x="110" y="92" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.5)}>SELECT *</motion.text>
      <motion.text x="110" y="104" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.5)}>FROM claims</motion.text>

      {/* Postgres box */}
      <motion.rect x="132" y="24" width="220" height="152" rx="4"
        fill={C.bg2} stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.6)}>
      </motion.rect>
      <motion.text x="242" y="42" textAnchor="middle" fill={C.ok} fontSize="7.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.7)}>PostgreSQL + RLS</motion.text>

      {/* RLS policy */}
      <motion.rect x="144" y="50" width="196" height="36" rx="2" fill={C.bg} stroke={C.purple} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.9)}>
      </motion.rect>
      <motion.text x="242" y="63" textAnchor="middle" fill={C.purple} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0)}>POLICY: customer_scope</motion.text>
      <motion.text x="242" y="76" textAnchor="middle" fill={C.fg2} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.1)}>USING (customer_id = current_setting(&apos;app.customer_id&apos;))</motion.text>

      {/* Rows: customer A (visible) */}
      <motion.rect x="144" y="96" width="92" height="22" rx="2" fill="#081408" stroke={C.ok} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.3)}>
      </motion.rect>
      <motion.text x="190" y="107" textAnchor="middle" fill={C.ok} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.4)}>CLM-100 · customer_id=A</motion.text>
      <motion.text x="190" y="114" textAnchor="middle" fill={C.ok} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.4)}>✓ visible (session A)</motion.text>

      {/* Rows: customer B (hidden) */}
      <motion.rect x="244" y="96" width="92" height="22" rx="2" fill="#1a0505" stroke={C.alert} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.5)}>
      </motion.rect>
      <motion.text x="290" y="107" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>CLM-200 · customer_id=B</motion.text>
      <motion.text x="290" y="114" textAnchor="middle" fill={C.alert} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>✗ invisible (session A)</motion.text>

      <motion.text x="242" y="140" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.8)}>RLS applied at DB layer — independent of app code</motion.text>
      <motion.text x="242" y="153" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>bypass requires DB-role compromise, not app bug</motion.text>
      <motion.text x="242" y="166" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>pii_vault uses separate per-column encryption</motion.text>

      {/* Cross-customer probe attempt */}
      <motion.path d="M8 56 Q60 16 132 56" stroke={C.alert} strokeWidth="1.5" strokeDasharray="5 3"
        fill="none" markerEnd="url(#p7d-alert)"
        initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.7 }} transition={t(2.3)} />
      <motion.text x="68" y="18" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.5)}>cross-customer probe → 0 rows</motion.text>

      {/* Right: result */}
      <motion.rect x="364" y="56" width="188" height="88" rx="3"
        fill={C.bg2} stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.7)}>
      </motion.rect>
      <motion.text x="458" y="76" textAnchor="middle" fill={C.ok} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.8)}>RESULT SET (session A)</motion.text>
      <motion.text x="458" y="92" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>CLM-100  |  PROCESSING</motion.text>
      <motion.text x="458" y="106" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>CLM-101  |  SETTLED</motion.text>
      <motion.text x="458" y="124" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.0)}>0 rows from customer B</motion.text>
      <motion.text x="458" y="136" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.0)}>no error — just empty</motion.text>

      <motion.path d="M352 100 L364 100" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p7d-ok)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.6)} />

      <Arrow id="p7d-blue"  color={C.blue}  />
      <Arrow id="p7d-alert" color={C.alert} />
      <Arrow id="p7d-ok"    color={C.ok}    />
    </svg>
  );
}

// ── P8 — Per-Agent Asymmetric Identity ────────────────────────────────────────
function P8Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.3, rm);

  const agents = [
    { label: "ORCH",      color: C.blue,   x: 8 },
    { label: "INTAKE",    color: C.ok,     x: 114 },
    { label: "IDENTITY",  color: C.warn,   x: 220 },
    { label: "PROCESSOR", color: C.purple, x: 326 },
    { label: "SETTLEMENT",color: C.alert,  x: 432 },
  ];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Agent boxes with keypair badges */}
      {agents.map((a, i) => (
        <motion.g key={a.label} initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          transition={t(i * 0.2)}>
          <rect x={a.x} y="8" width="98" height="72" rx="3" fill={C.bg2} stroke={a.color} strokeWidth="1.5" />
          <text x={a.x + 49} y="28" textAnchor="middle" fill={a.color} fontSize="6" fontFamily="monospace" fontWeight="600">{a.label}</text>
          {/* Key icon */}
          <circle cx={a.x + 36} cy="46" r="7" fill="none" stroke={a.color} strokeWidth="1.2" />
          <line x1={a.x + 43} y1="46" x2={a.x + 62} y2="46" stroke={a.color} strokeWidth="1.2" />
          <line x1={a.x + 56} y1="46" x2={a.x + 56} y2="52" stroke={a.color} strokeWidth="1.2" />
          <text x={a.x + 49} y="64" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">Ed25519 key{i + 1}</text>
          <text x={a.x + 49} y="72" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">independent</text>
        </motion.g>
      ))}

      {/* Message signing animation */}
      <motion.rect x="8" y="96" width="280" height="56" rx="3"
        fill={C.bg} stroke={C.blue} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.4)}>
      </motion.rect>
      <motion.text x="144" y="112" textAnchor="middle" fill={C.blue} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.5)}>SIGNED MESSAGE (orchestrator → processor)</motion.text>
      <motion.text x="144" y="124" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>{`{ source: "orchestrator", payload: {...}, sig: Ed25519(key1) }`}</motion.text>
      <motion.text x="144" y="136" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.7)}>recipient verifies against pubkey1 in public registry</motion.text>
      <motion.text x="144" y="146" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.7)}>invalid sig → reject + audit</motion.text>

      {/* Compromise isolation note */}
      <motion.rect x="296" y="96" width="256" height="56" rx="3"
        fill="#1a0505" stroke={C.alert} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.2)}>
      </motion.rect>
      <motion.text x="424" y="112" textAnchor="middle" fill={C.alert} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.3)}>COMPROMISE ISOLATION</motion.text>
      <motion.text x="424" y="126" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.4)}>key2 (intake) compromised</motion.text>
      <motion.text x="424" y="138" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.5)}>→ key1,3,4,5 remain secure</motion.text>
      <motion.text x="424" y="148" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.6)}>no shared secrets</motion.text>

      <text x="280" y="172" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace">
        public key registry — each agent issues under its own private key only
      </text>
    </svg>
  );
}

// ── P9 — Append-Only Hash-Chained Audit ───────────────────────────────────────
function P9Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.3, rm);

  const blocks = [
    { x: 8,   label: "GENESIS", sub: "h0=sha256(0)", idx: 0 },
    { x: 148, label: "LOG_1",   sub: "h1=sha256(h0+data1)", idx: 1 },
    { x: 288, label: "LOG_2",   sub: "h2=sha256(h1+data2)", idx: 2 },
    { x: 428, label: "LOG_N",   sub: "hN=sha256(hN-1+dataN)", idx: 3 },
  ];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {blocks.map((b, i) => (
        <motion.g key={b.label} initial={{ opacity: 0, scale: 0.7 }}
          style={{ transformOrigin: `${b.x + 62}px 80px` }}
          animate={{ opacity: 1, scale: 1 }} transition={t(i * 0.3)}>
          <rect x={b.x} y="36" width="124" height="88" rx="3"
            fill={C.bg2} stroke={i === 2 ? C.alert : C.bg3} strokeWidth={i === 2 ? 2 : 1} />
          <text x={b.x + 62} y="54" textAnchor="middle"
            fill={i === 2 ? C.alert : C.ok} fontSize="7" fontFamily="monospace" fontWeight="600">{b.label}</text>
          <line x1={b.x + 8} y1="60" x2={b.x + 116} y2="60" stroke={C.bg3} strokeWidth="0.8" />
          <text x={b.x + 62} y="72" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">prev_hash</text>
          <text x={b.x + 62} y="82" textAnchor="middle" fill={C.fg2} fontSize="4.5" fontFamily="monospace">
            {i === 0 ? "0000…00" : `h${i}`}
          </text>
          <line x1={b.x + 8} y1="88" x2={b.x + 116} y2="88" stroke={C.bg3} strokeWidth="0.8" />
          <text x={b.x + 62} y="100" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">data</text>
          <text x={b.x + 62} y="112" textAnchor="middle" fill={C.fg2} fontSize="4.5" fontFamily="monospace">
            {["init", "tool_call", "pii_block", "agent_msg"][i]}
          </text>
          <line x1={b.x + 8} y1="116" x2={b.x + 116} y2="116" stroke={C.bg3} strokeWidth="0.8" />
          <text x={b.x + 62} y="114" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"> </text>
          <text x={b.x + 62} y="120" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">row_hash</text>
          <text x={b.x + 62} y="116" textAnchor="middle" fill={i === 2 ? C.alert : C.ok} fontSize="4.5" fontFamily="monospace">
            {b.sub.length > 22 ? b.sub.slice(0, 22) + "…" : b.sub}
          </text>
        </motion.g>
      ))}

      {/* Chain arrows */}
      {[0, 1, 2].map((i) => (
        <motion.path key={i}
          d={`M${blocks[i].x + 124} 80 L${blocks[i + 1].x} 80`}
          stroke={i === 1 ? C.alert : C.ok} strokeWidth="1.5"
          markerEnd={i === 1 ? "url(#p9d-alert)" : "url(#p9d-ok)"}
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.0 + i * 0.3)}
        />
      ))}

      {/* Tamper annotation on LOG_2 */}
      <motion.text x="350" y="22" textAnchor="middle" fill={C.alert} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>TAMPER LOG_2</motion.text>
      <motion.path d="M350 24 L350 34" stroke={C.alert} strokeWidth="1.5" markerEnd="url(#p9d-alert2)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.1)} />

      {/* Chain break */}
      <motion.line x1="412" y1="72" x2="428" y2="88" stroke={C.alert} strokeWidth="2.5"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.4)} />
      <motion.line x1="428" y1="72" x2="412" y2="88" stroke={C.alert} strokeWidth="2.5"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.5)} />

      <motion.text x="280" y="150" textAnchor="middle" fill={C.ok} fontSize="6" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.8)}>
        INSERT-only audit_writer role · no UPDATE/DELETE granted
      </motion.text>
      <motion.text x="280" y="164" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>
        verify_chain() detects any modification · Console shows last-verified timestamp
      </motion.text>

      <Arrow id="p9d-ok"    color={C.ok}    />
      <Arrow id="p9d-alert" color={C.alert} />
      <Arrow id="p9d-alert2" color={C.alert} />
    </svg>
  );
}

// ── P10 — Egress Output Filter ────────────────────────────────────────────────
function P10Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.35, rm);

  const steps = [
    { label: "① SECRET kill-switch", sub: "SECRET label → replace + audit", color: C.purple, x: 8 },
    { label: "② URL strip",          sub: "non-allowlist → [link removed]",  color: C.blue,   x: 148 },
    { label: "③ PII regex",          sub: "SSN / card / phone → BLOCK",       color: C.warn,   x: 288 },
    { label: "④ Length cap",         sub: "truncate at MAX_OUTPUT_CHARS",     color: C.ok,     x: 428 },
  ];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Input */}
      <motion.rect x="8" y="60" width="8" height="80" rx="2" fill={C.warn}
        initial={{ scaleY: 0 }} animate={{ scaleY: 1 }}
        style={{ transformOrigin: "12px 60px" }}
        transition={t(0.1)} />
      <motion.text x="19" y="100" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.2)}>response</motion.text>

      {/* Step boxes */}
      {steps.map((s, i) => (
        <motion.g key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={t(0.4 + i * 0.35)}>
          <rect x={s.x} y="28" width="132" height="144" rx="3" fill={C.bg2} stroke={s.color} strokeWidth="1.5" />
          <text x={s.x + 66} y="46" textAnchor="middle" fill={s.color} fontSize="5.5" fontFamily="monospace" fontWeight="600">{s.label}</text>
          <line x1={s.x + 4} y1="52" x2={s.x + 128} y2="52" stroke={C.bg3} strokeWidth="0.8" />
          <text x={s.x + 66} y="66" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace">{s.sub}</text>
          {/* Drop arrow for blocked items */}
          <motion.path d={`M${s.x + 66} 152 L${s.x + 66} 170`}
            stroke={C.alert} strokeWidth="1" strokeDasharray="3 2" markerEnd="url(#p10d-alert)"
            initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.7 }}
            transition={t(1.8 + i * 0.2)} />
          <motion.text x={s.x + 66} y="182" textAnchor="middle" fill={C.alert} fontSize="5" fontFamily="monospace"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0 + i * 0.2)}>blocked</motion.text>

          {/* Short-circuit note on step 1 */}
          {i === 0 && (
            <motion.text x={s.x + 66} y="108" textAnchor="middle" fill={s.color} fontSize="5" fontFamily="monospace"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0)}>
              short-circuits steps 2–4
            </motion.text>
          )}
        </motion.g>
      ))}

      {/* Flow arrows between steps */}
      {[0, 1, 2].map((i) => (
        <motion.path key={i}
          d={`M${steps[i].x + 132} 100 L${steps[i + 1].x} 100`}
          stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p10d-ok)"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.2 + i * 0.3)} />
      ))}

      {/* Output */}
      <motion.path d="M560 100 L552 100" stroke={C.ok} strokeWidth="2"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(2.6)} />
      <motion.text x="548" y="88" textAnchor="end" fill={C.ok} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.7)}>SAFE</motion.text>

      <Arrow id="p10d-ok"    color={C.ok}    />
      <Arrow id="p10d-alert" color={C.alert} />
    </svg>
  );
}

// ── P11 — Token & Cost Budgets ────────────────────────────────────────────────
function P11Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.4, rm);

  const gauges = [
    { label: "Session tokens",    cap: "50,000 / session",   pct: 65, color: C.ok,   fill: C.ok    },
    { label: "Tool calls / agent", cap: "10 / agent",         pct: 40, color: C.blue, fill: C.blue  },
    { label: "Monthly LLM spend", cap: "$200 / month cap",   pct: 28, color: C.warn, fill: C.warn  },
    { label: "Adversarial agent", cap: "$50 / month hard cap",pct: 12, color: C.purple, fill: C.purple },
  ];

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Gauges */}
      {gauges.map((g, i) => {
        const y = 20 + i * 40;
        const barW = 360;
        const filled = (g.pct / 100) * barW;
        return (
          <motion.g key={g.label} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={t(i * 0.2)}>
            <text x="8" y={y + 12} fill={g.color} fontSize="6.5" fontFamily="monospace" fontWeight="600">{g.label}</text>
            <text x="8" y={y + 23} fill={C.fg3} fontSize="5" fontFamily="monospace">{g.cap}</text>
            {/* Track */}
            <rect x="8" y={y + 26} width={barW} height="10" rx="3" fill={C.bg2} stroke={C.bg3} strokeWidth="1" />
            {/* Fill */}
            <motion.rect x="8" y={y + 26} width="0" height="10" rx="3" fill={g.fill} opacity="0.8"
              animate={{ width: filled }} transition={{ duration: 0.8, delay: i * 0.2 + 0.4, ease: "easeOut" }} />
            {/* Pct label */}
            <motion.text x={14 + filled} y={y + 33} fill={C.fg0} fontSize="5" fontFamily="monospace"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(i * 0.2 + 1.0)}>
              {g.pct}%
            </motion.text>
          </motion.g>
        );
      })}

      {/* Hard cap line */}
      <motion.line x1="368" y1="16" x2="368" y2="176" stroke={C.alert} strokeWidth="1.5" strokeDasharray="4 3"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.2)} />
      <motion.text x="372" y="24" fill={C.alert} fontSize="6" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.3)}>HARD CAP</motion.text>
      <motion.text x="372" y="35" fill={C.alert} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.4)}>circuit breaker</motion.text>

      {/* Circuit breaker description */}
      <motion.rect x="390" y="48" width="162" height="116" rx="3"
        fill={C.bg2} stroke={C.alert} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.6)}>
      </motion.rect>
      <motion.text x="471" y="64" textAnchor="middle" fill={C.alert} fontSize="6" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.7)}>on cap exceeded:</motion.text>
      {[
        "→ halt session",
        "→ ESCALATED state",
        "→ audit row written",
        "→ SSE alert fired",
        "→ no LLM calls",
      ].map((line, i) => (
        <motion.text key={line} x="400" y={80 + i * 14} fill={C.fg2} fontSize="5.5" fontFamily="monospace"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.8 + i * 0.1)}>
          {line}
        </motion.text>
      ))}

      <motion.text x="280" y="190" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.4)}>
        per-session enforcement · per-agent enforcement · monthly roll-up · spend tracked per call
      </motion.text>
    </svg>
  );
}

// ── P12 — Signed System Prompts ───────────────────────────────────────────────
function P12Detail() {
  const rm = !!useReducedMotion();
  const t = useTrans(0.35, rm);

  return (
    <svg viewBox="0 0 560 200" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Prompt document */}
      <motion.rect x="8" y="28" width="96" height="120" rx="3"
        fill={C.bg2} stroke={C.fg3} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.2)}>
      </motion.rect>
      <motion.text x="56" y="46" textAnchor="middle" fill={C.fg1} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.3)}>SYSTEM PROMPT</motion.text>
      {[0, 1, 2, 3, 4].map((i) => (
        <motion.line key={i} x1="20" x2="92" y1={56 + i * 12} y2={56 + i * 12}
          stroke={C.fg3} strokeWidth="0.8" opacity="0.5"
          initial={{ scaleX: 0 }} animate={{ scaleX: 1 }}
          style={{ transformOrigin: "20px 0px" }}
          transition={t(0.4 + i * 0.05)} />
      ))}
      <motion.text x="56" y="130" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.6)}>prompts/intake_parser.txt</motion.text>
      <motion.text x="56" y="142" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.6)}>version-controlled</motion.text>

      {/* SHA256 hash */}
      <motion.path d="M104 88 L148 88" stroke={C.purple} strokeWidth="1.5" markerEnd="url(#p12d-pur)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(0.8)} />
      <motion.text x="126" y="80" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(0.9)}>sha256</motion.text>

      {/* Manifest */}
      <motion.rect x="148" y="40" width="144" height="96" rx="3"
        fill="#0d0720" stroke={C.purple} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.0)}>
      </motion.rect>
      <motion.text x="220" y="58" textAnchor="middle" fill={C.purple} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.1)}>MANIFEST</motion.text>
      {[
        `hash: "a3f2…c9b1"`,
        `prompt: "intake_parser"`,
        `version: "2.0"`,
        `sig: Ed25519(orch_key)`,
      ].map((line, i) => (
        <motion.text key={line} x="160" y={72 + i * 14} fill={C.fg2} fontSize="5.5" fontFamily="monospace"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.2 + i * 0.1)}>
          {line}
        </motion.text>
      ))}

      {/* Arrow → runtime verify */}
      <motion.path d="M292 88 L340 88" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#p12d-ok)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={t(1.8)} />

      {/* Runtime verify */}
      <motion.rect x="340" y="40" width="144" height="96" rx="3"
        fill={C.bg2} stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(1.9)}>
      </motion.rect>
      <motion.text x="412" y="58" textAnchor="middle" fill={C.ok} fontSize="6.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.0)}>RUNTIME VERIFY</motion.text>
      <motion.text x="412" y="72" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.1)}>sig valid (manifest)?</motion.text>
      <motion.text x="412" y="84" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.2)}>hash(prompt) == manifest.hash?</motion.text>
      <motion.text x="412" y="100" textAnchor="middle" fill={C.ok} fontSize="7" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.3)}>✓ ALLOW</motion.text>
      <motion.text x="412" y="116" textAnchor="middle" fill={C.alert} fontSize="7" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.4)}>✗ HALT + alert</motion.text>
      <motion.text x="412" y="128" textAnchor="middle" fill={C.fg3} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.4)}>(if mismatch)</motion.text>

      {/* PR change path */}
      <motion.path d="M220 136 L220 168 L412 168 L412 136" stroke={C.fg3} strokeWidth="1"
        strokeDasharray="4 2" fill="none"
        initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 0.6 }}
        transition={t(2.7)} />
      <motion.text x="316" y="184" textAnchor="middle" fill={C.fg3} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(2.9)}>
        prompt change → re-sign manifest → reviewed PR required
      </motion.text>

      {/* Attack note */}
      <motion.rect x="492" y="48" width="60" height="80" rx="3"
        fill="#1a0505" stroke={C.alert} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.0)}>
      </motion.rect>
      <motion.text x="522" y="64" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.1)}>ATTACK</motion.text>
      <motion.text x="522" y="78" textAnchor="middle" fill={C.fg2} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.2)}>swap</motion.text>
      <motion.text x="522" y="88" textAnchor="middle" fill={C.fg2} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.2)}>prompt</motion.text>
      <motion.text x="522" y="104" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.3)}>hash</motion.text>
      <motion.text x="522" y="114" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.3)}>mismatch</motion.text>
      <motion.text x="522" y="124" textAnchor="middle" fill={C.alert} fontSize="5.5" fontFamily="monospace" fontWeight="600"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={t(3.4)}>→ HALT</motion.text>

      <Arrow id="p12d-pur" color={C.purple} />
      <Arrow id="p12d-ok"  color={C.ok}     />
    </svg>
  );
}

// ── Public export map ──────────────────────────────────────────────────────────
export const DETAIL_DIAGRAM_MAP: Record<PatternId, () => ReactElement> = {
  P1:  P1Detail,
  P2:  P2Detail,
  P3:  P3Detail,
  P4:  P4Detail,
  P5:  P5Detail,
  P6:  P6Detail,
  P7:  P7Detail,
  P8:  P8Detail,
  P9:  P9Detail,
  P10: P10Detail,
  P11: P11Detail,
  P12: P12Detail,
};
