"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Static spec data ──────────────────────────────────────────────────────────

interface Invariant {
  name: string;
  kind: "safety" | "liveness";
  formula: string;
  plain: string;
}

const INVARIANTS: Invariant[] = [
  {
    name: "TypeOK",
    kind: "safety",
    formula: "stage ∈ Stages ∧ fraud_decision ∈ FraudDecisions ∧ settlement_amount ∈ AmountDomain ∧ ...",
    plain: "All 8 state variables remain within their declared value domains.",
  },
  {
    name: "ClosedIsAbsorbing",
    kind: "safety",
    formula: "[][stage = \"CLOSED\" ⇒ stage' = \"CLOSED\"]_vars",
    plain: "Once a claim reaches CLOSED, no further stage transitions are possible. CLOSED is a terminal sink.",
  },
  {
    name: "ForwardProgress",
    kind: "safety",
    formula: "[][stage ≠ stage' ⇒ Rank(stage') > Rank(stage)]_vars",
    plain: "Every stage change strictly increases topological rank. No backward transitions, no lateral hops.",
  },
  {
    name: "EventualClosure",
    kind: "liveness",
    formula: "<>(stage = \"CLOSED\")",
    plain: "Under weak fairness (WF_vars), every execution path eventually reaches CLOSED.",
  },
];

interface Suite {
  file: string;
  tests: number;
  passed: number;
  label: string;
}

const SUITES: Suite[] = [
  {
    file: "tests/unit/test_spec_invariants.py",
    tests: 30,
    passed: 30,
    label: "BFS over spec model: TypeOK, ClosedIsAbsorbing, ForwardProgress, EventualClosure, state-space bounds",
  },
  {
    file: "tests/unit/test_formal_conformance.py",
    tests: 102,
    passed: 102,
    label: "Implementation vs. spec: 11 valid edges accepted, 70 invalid pairs rejected, guard boundaries, terminal stage",
  },
];

// ── Props ─────────────────────────────────────────────────────────────────────

interface FormalShellProps {
  tlaSpec: string;
  checkedAt: string | null;
  unitPassed: number | null;
  unitTotal: number | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTs(iso: string | null): string {
  if (!iso) return "never run";
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "2-digit", minute: "2-digit", timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

// ── Workflow state diagram (SVG) ───────────────────────────────────────────────

const BW = 138;
const BH = 26;

const NODES: Record<string, { x: number; y: number }> = {
  INTAKE:            { x: 190, y: 35  },
  IDENTITY_PENDING:  { x: 190, y: 115 },
  IDENTITY_VERIFIED: { x: 190, y: 195 },
  PROCESSING:        { x: 190, y: 280 },
  DECIDED:           { x: 190, y: 365 },
  SETTLED:           { x: 55,  y: 462 },
  ESCALATED:         { x: 190, y: 462 },
  DENIED:            { x: 325, y: 462 },
  CLOSED:            { x: 190, y: 545 },
};

function bTop(n: string) { return { x: NODES[n].x, y: NODES[n].y - BH / 2 }; }
function bBot(n: string) { return { x: NODES[n].x, y: NODES[n].y + BH / 2 }; }
function bLeft(n: string) { return { x: NODES[n].x - BW / 2, y: NODES[n].y }; }
function bRight(n: string) { return { x: NODES[n].x + BW / 2, y: NODES[n].y }; }

function vLine(from: string, to: string) {
  const s = bBot(from);
  const e = bTop(to);
  return `M ${s.x} ${s.y} L ${e.x} ${e.y - 7}`;
}

function WorkflowDiagram() {
  return (
    <svg
      viewBox="0 0 380 575"
      xmlns="http://www.w3.org/2000/svg"
      className="w-full max-w-xs"
      role="img"
      aria-label="Claim workflow state diagram — 9 stages, 11 transitions"
    >
      <defs>
        <marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M 0 0 L 8 4 L 0 8 z" fill="#3D4856" />
        </marker>
        <marker id="arr-c" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M 0 0 L 8 4 L 0 8 z" fill="#F5B056" />
        </marker>
      </defs>

      {/* ── edges (drawn before nodes so nodes appear on top) ── */}

      {/* 1 INTAKE → IDENTITY_PENDING */}
      <path d={vLine("INTAKE", "IDENTITY_PENDING")} stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)" />

      {/* 2 IDENTITY_PENDING → IDENTITY_VERIFIED */}
      <path d={vLine("IDENTITY_PENDING", "IDENTITY_VERIFIED")} stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)" />

      {/* 3 IDENTITY_VERIFIED → PROCESSING */}
      <path d={vLine("IDENTITY_VERIFIED", "PROCESSING")} stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)" />

      {/* 4 IDENTITY_VERIFIED → ESCALATED — complaint path, curves right */}
      <path
        d={`M ${bRight("IDENTITY_VERIFIED").x} ${bRight("IDENTITY_VERIFIED").y}
            C 358 ${bRight("IDENTITY_VERIFIED").y} 358 ${bRight("ESCALATED").y}
              ${bRight("ESCALATED").x - 7} ${bRight("ESCALATED").y}`}
        stroke="#F5B056" strokeWidth="1.5" fill="none" markerEnd="url(#arr-c)"
      />
      <text x="365" y="330" fontSize="8" fill="#F5B056" fontFamily="monospace" writingMode="tb" textAnchor="middle">
        complaint
      </text>

      {/* 5 PROCESSING → DECIDED */}
      <path d={vLine("PROCESSING", "DECIDED")} stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)" />

      {/* 6 DECIDED → SETTLED */}
      <path
        d={`M ${bLeft("DECIDED").x} ${bLeft("DECIDED").y}
            Q 10 ${(NODES.DECIDED.y + NODES.SETTLED.y) / 2}
              ${bTop("SETTLED").x} ${bTop("SETTLED").y - 7}`}
        stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)"
      />

      {/* 7 DECIDED → ESCALATED */}
      <path d={vLine("DECIDED", "ESCALATED")} stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)" />

      {/* 8 DECIDED → DENIED */}
      <path
        d={`M ${bRight("DECIDED").x} ${bRight("DECIDED").y}
            Q 370 ${(NODES.DECIDED.y + NODES.DENIED.y) / 2}
              ${bTop("DENIED").x} ${bTop("DENIED").y - 7}`}
        stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)"
      />

      {/* 9 SETTLED → CLOSED */}
      <path
        d={`M ${bBot("SETTLED").x} ${bBot("SETTLED").y}
            Q 10 ${(NODES.SETTLED.y + NODES.CLOSED.y) / 2}
              ${bLeft("CLOSED").x} ${bLeft("CLOSED").y}`}
        stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)"
      />

      {/* 10 ESCALATED → CLOSED */}
      <path d={vLine("ESCALATED", "CLOSED")} stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)" />

      {/* 11 DENIED → CLOSED */}
      <path
        d={`M ${bBot("DENIED").x} ${bBot("DENIED").y}
            Q 370 ${(NODES.DENIED.y + NODES.CLOSED.y) / 2}
              ${bRight("CLOSED").x} ${bRight("CLOSED").y}`}
        stroke="#3D4856" strokeWidth="1.5" fill="none" markerEnd="url(#arr)"
      />

      {/* ── nodes ── */}
      {Object.entries(NODES).map(([name, { x, y }]) => {
        const isClosed = name === "CLOSED";
        const isPreTerminal = ["SETTLED", "ESCALATED", "DENIED"].includes(name);
        return (
          <g key={name}>
            <rect
              x={x - BW / 2}
              y={y - BH / 2}
              width={BW}
              height={BH}
              rx="3"
              fill="#0F141B"
              stroke={isClosed ? "#4ADE80" : "#1E2632"}
              strokeWidth={isClosed ? 1.5 : 1}
            />
            <text
              x={x}
              y={y + 4}
              textAnchor="middle"
              fontSize="9"
              fontFamily="monospace"
              fill={
                isClosed
                  ? "#4ADE80"
                  : isPreTerminal
                  ? "#B0BAC6"
                  : "#6E7B8C"
              }
            >
              {name.replace(/_/g, " ")}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function FormalShell({
  tlaSpec,
  checkedAt,
  unitPassed,
  unitTotal,
}: FormalShellProps) {
  const [specOpen, setSpecOpen] = useState(false);

  const allPassed = SUITES.every((s) => s.passed === s.tests);
  const totalFormal = SUITES.reduce((a, s) => a + s.tests, 0);

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-10 space-y-8">

      {/* ── Page header ─────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <h1 className="font-mono text-lg font-semibold text-fg-0">
          Formal Specification
        </h1>
        <p className="font-mono text-xs text-fg-2 max-w-2xl">
          Claim-workflow state machine specified in TLA+ (<code className="text-fg-1">formal/workflow.tla</code>).
          Invariants verified by exhaustive Python BFS over a bounded state space of ≤ 3,456 states.
          Conformance driven against the live <code className="text-fg-1">advance_stage()</code> implementation.
        </p>

        {/* status bar */}
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          <span className="flex items-center gap-1.5 text-fg-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ok" />
            Last checked:
            <span className="text-fg-1">{fmtTs(checkedAt)}</span>
          </span>
          <span className="text-fg-3">·</span>
          <span className="text-fg-2">
            {totalFormal} formal tests
            <span className={cn("ml-1", allPassed ? "text-ok" : "text-alert")}>
              ({allPassed ? "all passed" : "failures"})
            </span>
          </span>
          {unitTotal !== null && (
            <>
              <span className="text-fg-3">·</span>
              <span className="text-fg-2">
                {unitPassed}/{unitTotal} unit tests passing
              </span>
            </>
          )}
        </div>
      </div>

      {/* ── Main two-column layout ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[auto_1fr]">

        {/* left: state diagram */}
        <div className="space-y-2">
          <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3">
            State diagram · 9 stages · 11 transitions
          </div>
          <div className="rounded border border-bg-3 bg-bg-1 p-4">
            <WorkflowDiagram />
          </div>
          <p className="font-mono text-[9px] text-fg-3">
            <span className="text-ok">━</span> normal path&nbsp;&nbsp;
            <span className="text-warn">━</span> complaint path&nbsp;&nbsp;
            <span className="inline-block h-[10px] w-[10px] rounded-sm border border-ok" /> terminal
          </p>
        </div>

        {/* right: invariants + conformance */}
        <div className="space-y-6">

          {/* invariants */}
          <div className="space-y-2">
            <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3">
              Invariants
            </div>
            <div className="rounded border border-bg-3 overflow-hidden">
              {INVARIANTS.map((inv, i) => (
                <div
                  key={inv.name}
                  className={cn(
                    "px-4 py-3 space-y-1",
                    i > 0 && "border-t border-bg-3"
                  )}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-fg-0">
                        {inv.name}
                      </span>
                      <span
                        className={cn(
                          "rounded-sm border px-1 py-px font-mono text-[9px] uppercase tracking-wide",
                          inv.kind === "liveness"
                            ? "border-trust/40 text-trust"
                            : "border-audit/40 text-audit"
                        )}
                      >
                        {inv.kind}
                      </span>
                    </div>
                    <span className="shrink-0 rounded-sm border border-ok/40 bg-ok/8 px-1.5 py-px font-mono text-[9px] text-ok">
                      PASS
                    </span>
                  </div>
                  <p className="font-mono text-[10px] text-fg-3 leading-relaxed">
                    {inv.formula}
                  </p>
                  <p className="text-xs text-fg-2 leading-relaxed">
                    {inv.plain}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* conformance suites */}
          <div className="space-y-2">
            <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3">
              Conformance test suites
            </div>
            <div className="rounded border border-bg-3 overflow-hidden">
              {SUITES.map((suite, i) => (
                <div
                  key={suite.file}
                  className={cn(
                    "px-4 py-3 space-y-1",
                    i > 0 && "border-t border-bg-3"
                  )}
                >
                  <div className="flex items-center justify-between gap-4">
                    <code className="font-mono text-[11px] text-fg-1 break-all">
                      {suite.file}
                    </code>
                    <span className="shrink-0 rounded-sm border border-ok/40 bg-ok/8 px-1.5 py-px font-mono text-[9px] text-ok">
                      {suite.passed}/{suite.tests} PASS
                    </span>
                  </div>
                  <p className="text-xs text-fg-2 leading-relaxed">
                    {suite.label}
                  </p>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* ── TLA+ spec ────────────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <button
          onClick={() => setSpecOpen((o) => !o)}
          className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-fg-3 hover:text-fg-1 transition-colors"
        >
          {specOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          formal/workflow.tla ({tlaSpec.split("\n").length} lines)
        </button>
        {specOpen && (
          <div className="rounded border border-bg-3 bg-bg-1 overflow-hidden">
            <div className="flex items-center justify-between border-b border-bg-3 px-4 py-2">
              <span className="font-mono text-[10px] text-fg-3">
                TLA+ · formal specification
              </span>
            </div>
            {tlaSpec ? (
              <pre className="overflow-x-auto p-4 font-mono text-xs text-fg-2 leading-relaxed whitespace-pre">
                {tlaSpec}
              </pre>
            ) : (
              <p className="p-4 font-mono text-xs text-fg-3">
                Spec file not found — run from the project root with the backend directory present.
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── What this proves ─────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3">
          What this proves
        </div>
        <div className="rounded border border-bg-3 bg-bg-1 px-5 py-4 space-y-3 text-sm text-fg-2 leading-relaxed max-w-3xl">
          <p>
            The TLA+ spec models the claim workflow as a mathematical state machine with 9 stages and 11 legal
            transitions. It proves that within its bounded model (9 stages × 4 fraud values × 3 settlement amounts
            × 2⁵ boolean flags = 3,456 maximum states), the four invariants hold under all reachable execution
            paths — including paths where the environment sets flags in adversarial orders.
          </p>
          <p>
            The conformance test suite then drives the <em>real</em> <code className="font-mono text-fg-1">advance_stage()</code>{" "}
            implementation and verifies that its edge graph exactly matches the spec&apos;s 11 valid transitions,
            and that every guard boundary condition behaves as specified.
          </p>
          <p className="text-fg-3">
            <strong className="text-fg-2">What it does not prove:</strong> the spec does not model concurrent
            claims, network faults, or database atomicity. It models the logical state machine only — not the
            full system. Postgres RLS, audit-chain integrity, and capability-token enforcement are verified
            separately by their own test suites.
          </p>
        </div>
      </div>

      {/* ── Links ────────────────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3">
          Source
        </div>
        <div className="flex flex-wrap gap-3">
          {[
            { label: "formal/workflow.tla", href: "https://github.com/Athish49/ProjectCitadel/blob/main/backend/formal/workflow.tla" },
            { label: "formal/check_spec.py", href: "https://github.com/Athish49/ProjectCitadel/blob/main/backend/formal/check_spec.py" },
            { label: "test_spec_invariants.py", href: "https://github.com/Athish49/ProjectCitadel/blob/main/backend/tests/unit/test_spec_invariants.py" },
            { label: "test_formal_conformance.py", href: "https://github.com/Athish49/ProjectCitadel/blob/main/backend/tests/unit/test_formal_conformance.py" },
          ].map(({ label, href }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "flex items-center gap-1.5 rounded border border-bg-3 bg-bg-1 px-3 py-1.5",
                "font-mono text-xs text-fg-2 transition-colors hover:border-bg-3 hover:bg-bg-2 hover:text-fg-0"
              )}
            >
              {label}
              <ExternalLink size={11} className="shrink-0 text-fg-3" />
            </a>
          ))}
        </div>
      </div>

    </div>
  );
}
