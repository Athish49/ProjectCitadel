"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import type { Pattern } from "@/lib/types/showcase";
import { PatternDiagram } from "./pattern-diagram";

interface PatternCardProps {
  pattern: Pattern;
}

export function PatternCard({ pattern }: PatternCardProps) {
  const attackIds = pattern.attackIds.slice(0, 6);
  const overflow = pattern.attackIds.length - attackIds.length;

  return (
    <Link
      href={`/patterns/${pattern.id.toLowerCase()}`}
      className={cn(
        "group flex flex-col gap-3 rounded border border-bg-3 bg-bg-1 p-4",
        "transition-colors hover:border-bg-4 hover:bg-bg-2",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="font-mono text-xs font-semibold text-fg-3">{pattern.id}</span>
          <h3 className="mt-0.5 font-mono text-sm font-semibold text-fg-0 group-hover:text-fg-0">
            {pattern.name}
          </h3>
        </div>
        {pattern.testCount > 0 && (
          <span className="shrink-0 rounded border border-ok/20 bg-ok/5 px-1.5 py-0.5 font-mono text-xs text-ok">
            {pattern.testCount} tests
          </span>
        )}
      </div>

      {/* Animated diagram */}
      <PatternDiagram id={pattern.id} className="h-[72px] w-full" />

      {/* Summary */}
      <p className="font-mono text-xs leading-relaxed text-fg-2">{pattern.summary}</p>

      {/* Attack links */}
      <div className="flex flex-wrap items-center gap-1">
        <span className="font-mono text-xs text-fg-3">Defends:</span>
        {attackIds.map((id) => (
          <span
            key={id}
            onClick={(e) => {
              e.preventDefault();
              window.location.href = `/matrix?pattern=${pattern.id}`;
            }}
            className="rounded border border-bg-3 px-1.5 py-0.5 font-mono text-xs text-fg-3 transition-colors hover:border-alert/30 hover:text-alert"
          >
            #{id}
          </span>
        ))}
        {overflow > 0 && (
          <span className="font-mono text-xs text-fg-3">+{overflow} more</span>
        )}
      </div>

      {/* Code ref count */}
      {pattern.codeRefs.length > 0 && (
        <div className="border-t border-bg-3 pt-2">
          <span className="font-mono text-xs text-fg-3">
            {pattern.codeRefs.length} code ref{pattern.codeRefs.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}
    </Link>
  );
}
