"use client";

import { ShieldCheck, ShieldAlert, Shield, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { FadeIn, SlideIn } from "@/components/primitives/motion";
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
          Live WebSocket streaming connects in Sprint 3.2.2. Submissions now return an example trace
          showing the P1 dual-LLM separation defense firing on a direct prompt injection.
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
  const cfg = VERDICT_CONFIG[trace.verdict.outcome];
  const VerdictIcon = cfg.icon;

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
        </div>
        <div className="mt-1 font-mono text-[10px] text-fg-3">
          Trace {trace.traceId} · {trace.submittedAt}
        </div>
      </div>

      {/* layers */}
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 space-y-1.5">
        {trace.layers.map((layer, i) => (
          <SlideIn key={layer.id} delay={i * 0.06} direction="up">
            <TraceLayerPanel layer={layer} index={i} />
          </SlideIn>
        ))}
      </div>

      {/* verdict */}
      <SlideIn
        delay={trace.layers.length * 0.06 + 0.05}
        className="shrink-0 border-t border-border px-4 py-3"
      >
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
              {trace.verdict.blockedByPattern && (
                <span className="rounded-sm border border-current px-1 py-0.5 font-mono text-[10px] opacity-70 text-trust border-trust">
                  {trace.verdict.blockedByPattern}
                </span>
              )}
              {trace.verdict.blockedByLayer && (
                <span className="font-mono text-[10px] text-fg-3">
                  at {trace.verdict.blockedByLayer}
                </span>
              )}
            </div>
            <p className="mt-1 font-mono text-[10px] leading-relaxed text-fg-2">
              {trace.verdict.summary}
            </p>
          </div>
        </div>
      </SlideIn>
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
