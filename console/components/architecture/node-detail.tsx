"use client";

import { X, Cpu, Lock, Wrench, Shield } from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { NodeSpec, TrustLabel } from "@/lib/types/showcase";

const LABEL_STYLES: Record<TrustLabel, string> = {
  public:       "border-[#5BB5F2]/40 text-[#5BB5F2]  bg-[#5BB5F2]/8",
  personal:     "border-[#F5B056]/40 text-[#F5B056]  bg-[#F5B056]/8",
  confidential: "border-[#C879FF]/40 text-[#C879FF]  bg-[#C879FF]/8",
  secret:       "border-[#F25B5B]/40 text-[#F25B5B]  bg-[#F25B5B]/8",
  untrusted:    "border-[#8B96A8]/40 text-[#8B96A8]  bg-[#8B96A8]/8",
};

interface NodeDetailProps {
  spec: NodeSpec;
  onClose: () => void;
}

export function NodeDetail({ spec, onClose }: NodeDetailProps) {
  return (
    <motion.div
      key={spec.id}
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ type: "tween", duration: 0.18 }}
      className="absolute right-0 top-0 z-10 flex h-full w-72 flex-col overflow-hidden border-l border-[#1E2632] bg-[#0F141B]"
    >
      {/* header */}
      <div className="flex shrink-0 items-start justify-between border-b border-[#1E2632] px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="font-mono text-xs font-semibold text-[#E8EDF2]">{spec.role}</div>
          {spec.model && (
            <div className="mt-0.5 flex items-center gap-1 font-mono text-[10px] text-[#8B96A8]">
              <Cpu className="h-2.5 w-2.5 shrink-0" />
              {spec.model}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-3 shrink-0 rounded p-0.5 text-[#8B96A8] transition-colors hover:text-[#E8EDF2]"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        <p className="font-mono text-[11px] leading-relaxed text-[#A8B4C0]">
          {spec.description}
        </p>

        {spec.tools.length > 0 && (
          <section>
            <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">
              <Wrench className="h-2.5 w-2.5" />
              Tools ({spec.tools.length})
            </div>
            <div className="space-y-0.5">
              {spec.tools.map((t) => (
                <div key={t} className="font-mono text-[11px] text-[#A8B4C0]">
                  <span className="text-[#8B96A8]">›</span> {t}
                </div>
              ))}
            </div>
          </section>
        )}

        {spec.labelAccess.length > 0 && (
          <section>
            <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">
              <Lock className="h-2.5 w-2.5" />
              Label access
            </div>
            <div className="flex flex-wrap gap-1">
              {spec.labelAccess.map((l) => (
                <span
                  key={l}
                  className={cn(
                    "rounded border px-1.5 py-0.5 font-mono text-[10px]",
                    LABEL_STYLES[l]
                  )}
                >
                  {l.toUpperCase()}
                </span>
              ))}
            </div>
          </section>
        )}

        {spec.labelAccess.length === 0 && (
          <section>
            <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">
              <Lock className="h-2.5 w-2.5" />
              Label access
            </div>
            <span className="font-mono text-[11px] text-[#8B96A8]">none (external)</span>
          </section>
        )}

        {spec.patterns.length > 0 && (
          <section>
            <div className="mb-1.5 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">
              <Shield className="h-2.5 w-2.5" />
              Defense patterns
            </div>
            <div className="flex flex-wrap gap-1">
              {spec.patterns.map((p) => (
                <span
                  key={p}
                  className="rounded border border-[#5BB5F2]/25 px-1.5 py-0.5 font-mono text-[10px] text-[#5BB5F2]/70"
                >
                  {p}
                </span>
              ))}
            </div>
          </section>
        )}
      </div>
    </motion.div>
  );
}
