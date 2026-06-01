"use client";

import type { ReactElement } from "react";
import { motion } from "framer-motion";
import type { PatternId } from "@/lib/types/showcase";

// All diagrams share a 120×72 viewBox. Colours from design tokens (inline for SVG compat).
const C = {
  bg:     "#0d0d0d",
  border: "#1f1f1f",
  dim:    "#2a2a2a",
  muted:  "#4a4a4a",
  fg2:    "#888888",
  fg0:    "#e8e8e8",
  ok:     "#22c55e",
  warn:   "#f59e0b",
  alert:  "#ef4444",
  blue:   "#3b82f6",
  purple: "#a855f7",
};

function DualLlmDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Parser box */}
      <rect x="4" y="20" width="42" height="32" rx="3" fill={C.dim} stroke={C.border} />
      <text x="25" y="34" textAnchor="middle" fill={C.fg2} fontSize="6" fontFamily="monospace">PARSER</text>
      <text x="25" y="42" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">no tools</text>

      {/* Boundary line */}
      <line x1="60" y1="8" x2="60" y2="64" stroke={C.border} strokeWidth="1" strokeDasharray="3 2" />
      <text x="60" y="6" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">trust boundary</text>

      {/* Actor box */}
      <rect x="74" y="20" width="42" height="32" rx="3" fill={C.dim} stroke={C.blue} />
      <text x="95" y="34" textAnchor="middle" fill={C.blue} fontSize="6" fontFamily="monospace">ACTOR</text>
      <text x="95" y="42" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">privileged</text>

      {/* Animated arrow: left → parser */}
      <motion.line
        x1="0" y1="36" x2="4" y2="36"
        stroke={C.warn} strokeWidth="1.5"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      />
      {/* Arrow: parser → actor */}
      <motion.path
        d="M46 36 L74 36"
        stroke={C.ok} strokeWidth="1.5"
        markerEnd="url(#arrowOk)"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.8 }}
      />
      <text x="60" y="33" textAnchor="middle" fill={C.fg2} fontSize="5" fontFamily="monospace">JSON</text>
      <defs>
        <marker id="arrowOk" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.ok} />
        </marker>
      </defs>
    </svg>
  );
}

function StateMachineDiagram() {
  const delays = [0, 0.5, 1.0];
  const labels = ["INTAKE", "PROC", "SETTLED"];
  const colors = [C.blue, C.warn, C.ok];
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {labels.map((label, i) => (
        <motion.g key={label}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: delays[i] }}
        >
          <circle cx={20 + i * 40} cy="36" r="12" fill={C.dim} stroke={colors[i]} strokeWidth="1.5" />
          <text x={20 + i * 40} y="39" textAnchor="middle" fill={colors[i]} fontSize="5" fontFamily="monospace">{label}</text>
        </motion.g>
      ))}
      {[0, 1].map((i) => (
        <motion.path
          key={i}
          d={`M${32 + i * 40} 36 L${48 + i * 40} 36`}
          stroke={C.ok} strokeWidth="1" markerEnd="url(#arrowSm)"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.3, delay: 0.6 + i * 0.5 }}
        />
      ))}
      <text x="60" y="60" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">code decides</text>
      <defs>
        <marker id="arrowSm" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.ok} />
        </marker>
      </defs>
    </svg>
  );
}

function LabelStackDiagram() {
  const layers = [
    { label: "SECRET",       color: C.alert,  y: 16 },
    { label: "CONFIDENTIAL", color: C.warn,   y: 28 },
    { label: "PERSONAL",     color: C.blue,   y: 40 },
    { label: "PUBLIC",       color: C.ok,     y: 52 },
  ];
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {layers.map((l, i) => (
        <motion.rect
          key={l.label}
          x="22" y={l.y} width="76" height="10" rx="2"
          fill={C.dim} stroke={l.color} strokeWidth="1"
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          style={{ originX: "22px" }}
          transition={{ duration: 0.25, delay: i * 0.15 }}
        />
      ))}
      {layers.map((l, i) => (
        <motion.text
          key={l.label + "t"}
          x="60" y={l.y + 7} textAnchor="middle"
          fill={l.color} fontSize="5.5" fontFamily="monospace"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.15 + 0.2 }}
        >
          {l.label}
        </motion.text>
      ))}
      {/* Sensitivity arrow */}
      <text x="13" y="64" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace" transform="rotate(-90,13,40)">sensitivity</text>
    </svg>
  );
}

function CapabilityTokenDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Tool call box */}
      <rect x="70" y="22" width="44" height="28" rx="3" fill={C.dim} stroke={C.border} />
      <text x="92" y="35" textAnchor="middle" fill={C.fg2} fontSize="6" fontFamily="monospace">TOOL</text>
      <text x="92" y="43" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">registry</text>

      {/* Capability token badge */}
      <motion.rect
        x="6" y="26" width="50" height="20" rx="3"
        fill="#1a1a2e" stroke={C.purple} strokeWidth="1.5"
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      />
      <motion.text x="31" y="35" textAnchor="middle" fill={C.purple} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
        TOKEN
      </motion.text>
      <motion.text x="31" y="42" textAnchor="middle" fill={C.muted} fontSize="4.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}>
        signed · scoped
      </motion.text>

      {/* Arrow token → tool */}
      <motion.path d="M56 36 L70 36" stroke={C.purple} strokeWidth="1.5" markerEnd="url(#arrowP)"
        initial={{ pathLength: 0, opacity: 0 }}
        animate={{ pathLength: 1, opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.9 }}
      />
      {/* Checkmark */}
      <motion.text x="92" y="20" textAnchor="middle" fill={C.ok} fontSize="9" fontFamily="monospace"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 1.3, type: "spring", stiffness: 300 }}
      >✓</motion.text>
      <defs>
        <marker id="arrowP" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.purple} />
        </marker>
      </defs>
    </svg>
  );
}

function SandboxDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Container boundary */}
      <motion.rect
        x="30" y="12" width="60" height="48" rx="4"
        fill={C.bg} stroke={C.warn} strokeWidth="1.5" strokeDasharray="4 2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      />
      <text x="60" y="10" textAnchor="middle" fill={C.warn} fontSize="5" fontFamily="monospace">CONTAINER</text>
      {/* Parser process inside */}
      <rect x="40" y="22" width="40" height="18" rx="2" fill={C.dim} stroke={C.border} />
      <text x="60" y="34" textAnchor="middle" fill={C.fg2} fontSize="6" fontFamily="monospace">PARSER</text>
      {/* No egress marker */}
      <line x1="90" y1="36" x2="108" y2="36" stroke={C.muted} strokeWidth="1" strokeDasharray="2 1" />
      <motion.line x1="103" y1="31" x2="108" y2="41" stroke={C.alert} strokeWidth="1.5"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.6 }} />
      <motion.line x1="103" y1="41" x2="108" y2="31" stroke={C.alert} strokeWidth="1.5"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.7 }} />
      <text x="102" y="48" textAnchor="middle" fill={C.alert} fontSize="4.5" fontFamily="monospace">no egress</text>
      {/* OCR text out */}
      <motion.path d="M60 40 L60 52" stroke={C.ok} strokeWidth="1" markerEnd="url(#arrowSb)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.8 }} />
      <text x="60" y="62" textAnchor="middle" fill={C.ok} fontSize="4.5" fontFamily="monospace">text → P1</text>
      <defs>
        <marker id="arrowSb" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.ok} />
        </marker>
      </defs>
    </svg>
  );
}

function RedactDiagram() {
  const blocks = [
    { x: 28, y: 20, w: 28, h: 6 },
    { x: 62, y: 30, w: 22, h: 6 },
    { x: 32, y: 42, w: 32, h: 6 },
  ];
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Image frame */}
      <rect x="18" y="10" width="84" height="52" rx="3" fill={C.dim} stroke={C.border} />
      {/* Fake image content lines */}
      {[18, 26, 34, 42, 50].map((y) => (
        <line key={y} x1="26" x2="96" y1={y} y2={y} stroke={C.muted} strokeWidth="1" opacity="0.3" />
      ))}
      {/* Redaction blocks appear */}
      {blocks.map((b, i) => (
        <motion.rect
          key={i}
          x={b.x} y={b.y} width={b.w} height={b.h} rx="1"
          fill={C.alert} opacity={0.8}
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 0.85, scaleX: 1 }}
          style={{ originX: `${b.x}px` }}
          transition={{ duration: 0.25, delay: 0.4 + i * 0.25 }}
        />
      ))}
      <text x="60" y="68" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">OCR → pixel redact</text>
    </svg>
  );
}

function RlsDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* DB cylinder (simplified as rect) */}
      <ellipse cx="60" cy="24" rx="26" ry="8" fill={C.dim} stroke={C.border} />
      <rect x="34" y="24" width="52" height="22" fill={C.dim} stroke={C.border} />
      <ellipse cx="60" cy="46" rx="26" ry="8" fill={C.dim} stroke={C.border} />
      <text x="60" y="39" textAnchor="middle" fill={C.fg2} fontSize="6" fontFamily="monospace">claims</text>
      {/* Shield overlay */}
      <motion.path
        d="M60 16 L72 20 L72 30 C72 36 66 40 60 42 C54 40 48 36 48 30 L48 20 Z"
        fill="#1a2a1a" stroke={C.ok} strokeWidth="1.5"
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: 1, scale: 1 }}
        style={{ originX: "60px", originY: "29px" }}
        transition={{ duration: 0.4, delay: 0.4, type: "spring", stiffness: 200 }}
      />
      <motion.text x="60" y="32" textAnchor="middle" fill={C.ok} fontSize="6"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>
        RLS
      </motion.text>
      <text x="60" y="62" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">enforced at DB layer</text>
    </svg>
  );
}

function SigningDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Message envelope */}
      <rect x="10" y="20" width="38" height="28" rx="3" fill={C.dim} stroke={C.border} />
      <text x="29" y="33" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace">MSG</text>
      <text x="29" y="41" textAnchor="middle" fill={C.muted} fontSize="4.5" fontFamily="monospace">payload</text>

      {/* Key icon */}
      <motion.g
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <circle cx="29" cy="12" r="4" fill="none" stroke={C.warn} strokeWidth="1.5" />
        <line x1="33" y1="12" x2="38" y2="12" stroke={C.warn} strokeWidth="1.5" />
        <line x1="36" y1="12" x2="36" y2="15" stroke={C.warn} strokeWidth="1.5" />
      </motion.g>

      {/* Signature tag */}
      <motion.rect x="10" y="52" width="38" height="8" rx="2" fill="#1a1a2e" stroke={C.purple} strokeWidth="1"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
      />
      <motion.text x="29" y="58" textAnchor="middle" fill={C.purple} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0 }}>
        ✓ sig
      </motion.text>

      {/* Arrow to verifier */}
      <motion.path d="M48 36 L72 36" stroke={C.ok} strokeWidth="1.5" markerEnd="url(#arrowSg)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 1.2, duration: 0.4 }}
      />
      {/* Verifier */}
      <rect x="72" y="24" width="38" height="24" rx="3" fill={C.dim} stroke={C.ok} />
      <text x="91" y="35" textAnchor="middle" fill={C.ok} fontSize="5.5" fontFamily="monospace">VERIFY</text>
      <text x="91" y="43" textAnchor="middle" fill={C.muted} fontSize="4.5" fontFamily="monospace">pubkey</text>
      <defs>
        <marker id="arrowSg" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.ok} />
        </marker>
      </defs>
    </svg>
  );
}

function HashChainDiagram() {
  const blocks = [{ x: 6 }, { x: 42 }, { x: 78 }];
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {blocks.map((b, i) => (
        <motion.g key={i}
          initial={{ opacity: 0, scale: 0.7 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: i * 0.3 }}
        >
          <rect x={b.x} y="18" width="34" height="36" rx="2" fill={C.dim} stroke={i === 2 ? C.blue : C.border} strokeWidth={i === 2 ? 1.5 : 1} />
          <text x={b.x + 17} y="31" textAnchor="middle" fill={C.muted} fontSize="4.5" fontFamily="monospace">h(prev)</text>
          <line x1={b.x + 6} y1="33" x2={b.x + 28} y2="33" stroke={C.border} strokeWidth="0.5" />
          <text x={b.x + 17} y="41" textAnchor="middle" fill={i === 2 ? C.blue : C.fg2} fontSize="4.5" fontFamily="monospace">{`LOG_${i + 1}`}</text>
          <text x={b.x + 17} y="49" textAnchor="middle" fill={C.muted} fontSize="4" fontFamily="monospace">hash</text>
        </motion.g>
      ))}
      {[0, 1].map((i) => (
        <motion.path key={i} d={`M${40 + i * 36} 36 L${42 + i * 36} 36`}
          stroke={C.fg2} strokeWidth="1" markerEnd="url(#arrowHc)"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }}
          transition={{ delay: 0.5 + i * 0.3 }}
        />
      ))}
      <text x="60" y="66" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">tamper → chain breaks</text>
      <defs>
        <marker id="arrowHc" markerWidth="3" markerHeight="3" refX="3" refY="1.5" orient="auto">
          <path d="M0,0 L0,3 L3,1.5 z" fill={C.fg2} />
        </marker>
      </defs>
    </svg>
  );
}

function FilterDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Pipeline */}
      <rect x="6" y="28" width="24" height="16" rx="2" fill={C.dim} stroke={C.border} />
      <text x="18" y="39" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace">text</text>

      {/* Arrow */}
      <line x1="30" y1="36" x2="40" y2="36" stroke={C.fg2} strokeWidth="1" />

      {/* Filter gate */}
      <motion.path
        d="M40 20 L80 20 L80 52 L40 52 Z M40 20 L60 36 L40 52"
        fill="#1a1a2e" stroke={C.warn} strokeWidth="1.5"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      />
      <motion.text x="63" y="39" textAnchor="middle" fill={C.warn} fontSize="5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
        FILTER
      </motion.text>

      {/* Arrow out */}
      <line x1="80" y1="36" x2="90" y2="36" stroke={C.ok} strokeWidth="1" markerEnd="url(#arrowFl)" />

      <rect x="90" y="28" width="24" height="16" rx="2" fill={C.dim} stroke={C.ok} />
      <text x="102" y="39" textAnchor="middle" fill={C.ok} fontSize="5" fontFamily="monospace">safe</text>

      {/* Blocked items fall down */}
      <motion.path d="M58 52 L52 62" stroke={C.alert} strokeWidth="1" strokeDasharray="2 1"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.9 }} />
      <text x="48" y="68" fill={C.alert} fontSize="4.5" fontFamily="monospace">blocked</text>
      <defs>
        <marker id="arrowFl" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.ok} />
        </marker>
      </defs>
    </svg>
  );
}

function BudgetDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Token gauge */}
      <text x="60" y="16" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace">session tokens</text>
      <rect x="14" y="22" width="92" height="12" rx="3" fill={C.dim} stroke={C.border} />
      <motion.rect x="14" y="22" width="0" height="12" rx="3" fill={C.ok}
        animate={{ width: 65 }} transition={{ duration: 1.2, delay: 0.2, ease: "easeOut" }} />
      <text x="60" y="44" textAnchor="middle" fill={C.muted} fontSize="5" fontFamily="monospace">65% of cap</text>

      {/* Tool-call gauge */}
      <text x="60" y="52" textAnchor="middle" fill={C.fg2} fontSize="5.5" fontFamily="monospace">tool calls / agent</text>
      <rect x="14" y="56" width="92" height="8" rx="2" fill={C.dim} stroke={C.border} />
      <motion.rect x="14" y="56" width="0" height="8" rx="2" fill={C.warn}
        animate={{ width: 40 }} transition={{ duration: 0.8, delay: 0.8, ease: "easeOut" }} />

      {/* Hard cap marker */}
      <line x1="106" y1="20" x2="106" y2="36" stroke={C.alert} strokeWidth="1.5" />
      <text x="110" y="29" fill={C.alert} fontSize="4.5" fontFamily="monospace">cap</text>
    </svg>
  );
}

function SignedPromptDiagram() {
  return (
    <svg viewBox="0 0 120 72" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Prompt document */}
      <rect x="20" y="12" width="36" height="44" rx="3" fill={C.dim} stroke={C.border} />
      {[20, 26, 32, 38].map((y) => (
        <line key={y} x1="26" x2="50" y1={y + 8} y2={y + 8} stroke={C.muted} strokeWidth="0.8" opacity="0.5" />
      ))}
      <text x="38" y="53" textAnchor="middle" fill={C.fg2} fontSize="5" fontFamily="monospace">PROMPT</text>

      {/* Hash → manifest */}
      <motion.path d="M56 34 L72 34" stroke={C.purple} strokeWidth="1.5" markerEnd="url(#arrowSp)"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: 0.5 }} />
      <text x="64" y="30" textAnchor="middle" fill={C.muted} fontSize="4.5" fontFamily="monospace">sha256</text>

      {/* Manifest badge */}
      <motion.rect x="72" y="22" width="40" height="24" rx="3"
        fill="#1a1a2e" stroke={C.purple} strokeWidth="1.5"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}
      />
      <motion.text x="92" y="34" textAnchor="middle" fill={C.purple} fontSize="5.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0 }}>
        MANIFEST
      </motion.text>
      <motion.text x="92" y="41" textAnchor="middle" fill={C.muted} fontSize="4.5" fontFamily="monospace"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.1 }}>
        ✓ signed
      </motion.text>

      {/* Verification check */}
      <motion.text x="92" y="58" textAnchor="middle" fill={C.ok} fontSize="9"
        initial={{ opacity: 0, scale: 0 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 1.4, type: "spring", stiffness: 300 }}>
        ✓
      </motion.text>
      <defs>
        <marker id="arrowSp" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
          <path d="M0,0 L0,4 L4,2 z" fill={C.purple} />
        </marker>
      </defs>
    </svg>
  );
}

const DIAGRAM_MAP: Record<PatternId, () => ReactElement> = {
  P1:  DualLlmDiagram,
  P2:  StateMachineDiagram,
  P3:  LabelStackDiagram,
  P4:  CapabilityTokenDiagram,
  P5:  SandboxDiagram,
  P6:  RedactDiagram,
  P7:  RlsDiagram,
  P8:  SigningDiagram,
  P9:  HashChainDiagram,
  P10: FilterDiagram,
  P11: BudgetDiagram,
  P12: SignedPromptDiagram,
};

interface PatternDiagramProps {
  id: PatternId;
  className?: string;
}

export function PatternDiagram({ id, className }: PatternDiagramProps) {
  const Diagram = DIAGRAM_MAP[id];
  return (
    <div className={className} style={{ background: C.bg, borderRadius: 4, overflow: "hidden" }}>
      <Diagram />
    </div>
  );
}
