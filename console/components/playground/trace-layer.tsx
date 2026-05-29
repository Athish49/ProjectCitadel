"use client";

import { useState } from "react";
import { ChevronRight, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { MonoBlock } from "@/components/primitives/mono-block";
import type { TraceLayer, TraceLayerStatus } from "@/lib/types/playground";

const STATUS_COLORS: Record<TraceLayerStatus, string> = {
  pending: "text-fg-3",
  running: "text-warn",
  blocked: "text-alert",
  partial: "text-warn",
  passed:  "text-ok",
};

const STATUS_DOT: Record<TraceLayerStatus, string> = {
  pending: "bg-fg-3",
  running: "bg-warn animate-pulse",
  blocked: "bg-alert",
  partial: "bg-warn",
  passed:  "bg-ok",
};

const STATUS_LABEL: Record<TraceLayerStatus, string> = {
  pending: "PENDING",
  running: "RUNNING",
  blocked: "BLOCKED",
  partial: "PARTIAL",
  passed:  "PASSED",
};

const STATUS_BORDER: Record<TraceLayerStatus, string> = {
  pending: "border-border",
  running: "border-warn/30",
  blocked: "border-alert/40 bg-alert/5",
  partial: "border-warn/40",
  passed:  "border-border",
};

interface TraceLayerPanelProps {
  layer: TraceLayer;
  index: number;
}

export function TraceLayerPanel({ layer, index }: TraceLayerPanelProps) {
  const [expanded, setExpanded] = useState(layer.status === "blocked");

  const hasEvents = layer.events.length > 0;

  return (
    <div
      className={cn(
        "rounded border transition-colors",
        STATUS_BORDER[layer.status]
      )}
    >
      {/* header row */}
      <button
        type="button"
        onClick={() => hasEvents && setExpanded((v) => !v)}
        className={cn(
          "flex w-full items-center gap-3 px-3 py-2 text-left",
          hasEvents && "hover:bg-bg-2 transition-colors",
          !hasEvents && "cursor-default"
        )}
      >
        {/* index */}
        <span className="shrink-0 font-mono text-[10px] text-fg-3 tabular-nums">
          {String(index + 1).padStart(2, "0")}
        </span>

        {/* status dot */}
        <span
          className={cn("h-1.5 w-1.5 shrink-0 rounded-full", STATUS_DOT[layer.status])}
          aria-hidden
        />

        {/* layer name */}
        <span className={cn("flex-1 font-mono text-xs font-medium", STATUS_COLORS[layer.status])}>
          {layer.name}
        </span>

        {/* pattern badge */}
        {layer.pattern && (
          <span className="shrink-0 rounded-sm border border-trust/40 px-1 py-0.5 font-mono text-[10px] text-trust">
            {layer.pattern}
          </span>
        )}

        {/* duration */}
        {layer.durationMs !== null && (
          <span className="flex shrink-0 items-center gap-1 font-mono text-[10px] text-fg-3">
            <Clock className="h-2.5 w-2.5" />
            {layer.durationMs}ms
          </span>
        )}

        {/* status badge */}
        <span
          className={cn(
            "shrink-0 font-mono text-[10px] font-medium",
            STATUS_COLORS[layer.status]
          )}
        >
          {STATUS_LABEL[layer.status]}
        </span>

        {/* chevron */}
        {hasEvents && (
          <ChevronRight
            className={cn(
              "h-3 w-3 shrink-0 text-fg-3 transition-transform",
              expanded && "rotate-90"
            )}
          />
        )}
      </button>

      {/* events */}
      {expanded && hasEvents && (
        <div className="border-t border-border px-2 pb-2 pt-1 space-y-0.5">
          {layer.events.map((ev, i) => (
            <MonoBlock
              key={i}
              timestamp={ev.ts}
              severity={ev.severity}
              label={ev.label}
              message={ev.message}
            />
          ))}
        </div>
      )}
    </div>
  );
}
