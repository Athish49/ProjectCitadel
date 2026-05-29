"use client";

import { useState } from "react";
import { ShieldCheck, ShieldAlert, Shield, AlertTriangle, Info, Loader2, Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { FadeIn, SlideIn } from "@/components/primitives/motion";
import { EvidenceLink } from "@/components/primitives/evidence-link";
import { TraceLayerPanel } from "@/components/playground/trace-layer";
import type { PlaygroundTrace, PlaygroundVerdict } from "@/lib/types/playground";

// ── Verdict display ────────────────────────────────────────────────────────────

const VERDICT_CONFIG: Record<
  PlaygroundVerdict,
  { icon: React.FC<{ className?: string }>; color: string; bg: string; border: string; label: string }
> = {
  BLOCKED: {
    icon: ShieldCheck,
    color: "text-ok",
    bg:    "bg-ok/10",
    border:"border-ok/40",
    label: "BLOCKED",
  },
  PARTIAL: {
    icon: ShieldAlert,
    color: "text-warn",
    bg:    "bg-warn/10",
    border:"border-warn/40",
    label: "PARTIAL",
  },
  BREACH: {
    icon: AlertTriangle,
    color: "text-alert",
    bg:    "bg-alert/10",
    border:"border-alert/40",
    label: "BREACH",
  },
  CLEAN: {
    icon: Shield,
    color: "text-trust",
    bg:    "bg-trust/10",
    border:"border-trust/40",
    label: "CLEAN",
  },
};

// ── Empty state layer diagram ─────────────────────────────────────────────────

const LAYER_NAMES = [
  { name: "Ingress Sanitisation",  pattern: "P1" },
  { name: "Pattern Detection",     pattern: "P3" },
  { name: "Semantic Classifier",   pattern: "P3" },
  { name: "Untrusted Tagging",     pattern: "P3" },
  { name: "Parser LLM",           pattern: "P1" },
  { name: "Actor LLM",            pattern: "P2" },
  { name: "Egress Filter",        pattern: "P10" },
];

function EmptyState() {
  return (
    <FadeIn className="flex h-full flex-col items-center justify-center gap-8 px-8 py-12">
      {/* explanation */}
      <div className="max-w-md text-center">
        <Shield className="mx-auto mb-4 h-10 w-10 text-fg-3" />
        <h3 className="font-mono text-sm font-semibold text-fg-0">Defense Trace</h3>
        <p className="mt-2 font-mono text-xs leading-relaxed text-fg-3">
          Submit an attack payload on the left to watch it traverse each defense layer in real time.
          Each layer applies one or more security patterns (P1–P12) before passing input downstream.
        </p>
      </div>

      {/* layer diagram */}
      <div className="w-full max-w-xs space-y-1.5">
        <div className="mb-3 font-mono text-[10px] uppercase tracking-widest text-fg-3 text-center">
          Defense layers
        </div>
        {LAYER_NAMES.map((layer, i) => (
          <div
            key={layer.name}
            className="flex items-center gap-2 rounded border border-border bg-bg-1 px-3 py-1.5"
          >
            <span className="font-mono text-[10px] text-fg-3 tabular-nums">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-fg-3/40" aria-hidden />
            <span className="flex-1 font-mono text-xs text-fg-2">{layer.name}</span>
            <span className="rounded-sm border border-trust/30 px-1 py-0.5 font-mono text-[10px] text-trust/70">
              {layer.pattern}
            </span>
          </div>
        ))}

        {/* verdict placeholder */}
        <div className="mt-2 flex items-center justify-center rounded border border-border bg-bg-0 px-3 py-2">
          <span className="font-mono text-[10px] uppercase tracking-widest text-fg-3">
            Verdict
          </span>
        </div>
      </div>

      {/* info note */}
      <div className="flex max-w-md items-start gap-2 rounded border border-border bg-bg-1 px-3 py-2.5">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-fg-3" />
        <p className="font-mono text-[10px] leading-relaxed text-fg-3">
          Each submission streams layer-by-layer defense events via SSE. Scenarios are
          scenario-simulated with realistic timing; the structural defense logic (P1–P12) is
          faithfully reproduced.
        </p>
      </div>
    </FadeIn>
  );
}

// ── Trace view ─────────────────────────────────────────────────────────────────

interface TraceViewProps {
  trace: PlaygroundTrace;
}

function TraceView({ trace }: TraceViewProps) {
  const verdict = trace.verdict;
  const cfg = verdict ? VERDICT_CONFIG[verdict.outcome] : null;
  const VerdictIcon = cfg?.icon ?? null;
  const [copied, setCopied] = useState(false);

  function handleShare() {
    const url = `${window.location.origin}/playground?tab=${encodeURIComponent(trace.tab)}&autorun=1`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <FadeIn className="flex h-full flex-col">
      {/* header */}
      <div className="shrink-0 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-fg-0">Defense Trace</span>
          <span className="rounded-sm bg-bg-2 px-1.5 py-0.5 font-mono text-[10px] text-fg-3">
            #{trace.attackId} · {trace.attackName}
          </span>
          {trace.isExample && (
            <span className="rounded-sm border border-warn/40 bg-warn/10 px-1.5 py-0.5 font-mono text-[10px] text-warn">
              example trace
            </span>
          )}
          {trace.isReplay && (
            <span className="rounded-sm border border-audit/40 bg-audit/10 px-1.5 py-0.5 font-mono text-[10px] text-audit">
              replay
            </span>
          )}
          {verdict && (
            <button
              type="button"
              onClick={handleShare}
              title="Copy replay URL"
              className="ml-auto flex items-center gap-1 rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-fg-3 transition-colors hover:border-fg-3 hover:text-fg-1"
            >
              {copied ? (
                <><Check className="h-2.5 w-2.5 text-ok" />Copied</>
              ) : (
                <><Copy className="h-2.5 w-2.5" />Share</>
              )}
            </button>
          )}
        </div>
        <div className="mt-1 font-mono text-[10px] text-fg-3">
          Trace {trace.traceId} · {trace.submittedAt}
        </div>
      </div>

      {/* layers */}
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 space-y-1.5">
        {trace.layers.map((layer, i) => (
          <SlideIn key={layer.id} delay={i * 0.04} direction="up">
            <TraceLayerPanel layer={layer} index={i} />
          </SlideIn>
        ))}
      </div>

      {/* verdict — shows spinner while streaming, panel once complete */}
      <div className="shrink-0 border-t border-border px-4 py-3">
        {verdict && cfg && VerdictIcon ? (
          <SlideIn direction="up">
            <div
              className={cn(
                "flex items-start gap-3 rounded border px-4 py-3",
                cfg.bg,
                cfg.border
              )}
            >
              <VerdictIcon className={cn("mt-0.5 h-4 w-4 shrink-0", cfg.color)} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={cn("font-mono text-xs font-bold", cfg.color)}>
                    {cfg.label}
                  </span>
                  {verdict.blockedByPattern && (
                    <span className="rounded-sm border border-trust px-1 py-0.5 font-mono text-[10px] text-trust opacity-70">
                      {verdict.blockedByPattern}
                    </span>
                  )}
                  {verdict.blockedByLayer && (
                    <span className="font-mono text-[10px] text-fg-3">
                      at {verdict.blockedByLayer}
                    </span>
                  )}
                </div>
                <p className="mt-1 font-mono text-[10px] leading-relaxed text-fg-2">
                  {verdict.summary}
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <EvidenceLink
                    href={`/audit?trace=${trace.traceId}`}
                    label="Evidence: open audit rows"
                  />
                  {verdict.blockedByPattern && (
                    <EvidenceLink
                      href={`/patterns/${verdict.blockedByPattern}`}
                      label={`Pattern: ${verdict.blockedByPattern}`}
                    />
                  )}
                  <EvidenceLink
                    href="/matrix"
                    label="Attack matrix"
                  />
                </div>
              </div>
            </div>
          </SlideIn>
        ) : (
          <div className="flex items-center gap-2 py-1 text-fg-3">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span className="font-mono text-[10px]">Evaluating…</span>
          </div>
        )}
      </div>
    </FadeIn>
  );
}

// ── Public component ──────────────────────────────────────────────────────────

interface DefenseTraceProps {
  trace: PlaygroundTrace | null;
}

export function DefenseTrace({ trace }: DefenseTraceProps) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {trace ? <TraceView trace={trace} /> : <EmptyState />}
    </div>
  );
}
