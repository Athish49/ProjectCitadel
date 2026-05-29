"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import type { ArchNode, NodeType } from "@/lib/types/showcase";

const TYPE_STYLES: Record<NodeType, { label: string; text: string; border: string }> = {
  agent:        { label: "agent",        text: "text-[#5BB5F2]", border: "border-[#5BB5F2]/40" },
  parser:       { label: "parser",       text: "text-[#F5B056]", border: "border-[#F5B056]/40" },
  orchestrator: { label: "orchestrator", text: "text-[#C879FF]", border: "border-[#C879FF]/40" },
  datastore:    { label: "datastore",    text: "text-[#4ADE80]", border: "border-[#4ADE80]/40" },
  filter:       { label: "filter",       text: "text-[#8B96A8]", border: "border-[#8B96A8]/30" },
  external:     { label: "external",     text: "text-[#8B96A8]", border: "border-[#8B96A8]/20" },
};

export function ArchNodeComponent({ data, selected }: NodeProps) {
  const node = data as unknown as ArchNode;
  const s = TYPE_STYLES[node.type];

  return (
    <div
      className={cn(
        "w-44 rounded border bg-[#161C24] px-3 py-2 shadow-sm transition-shadow",
        selected
          ? "border-[#5BB5F2] shadow-[0_0_12px_rgba(91,181,242,0.25)]"
          : s.border
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!h-1.5 !w-1.5 !border-[#1E2632] !bg-[#8B96A8]/60"
      />

      <div className={cn("mb-0.5 font-mono text-[9px] uppercase tracking-wider", s.text)}>
        {s.label}
      </div>
      <div className="font-mono text-[11px] font-medium leading-snug text-[#E8EDF2]">
        {node.label}
      </div>

      {node.patterns.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-0.5">
          {node.patterns.map((p) => (
            <span
              key={p}
              className="rounded-sm border border-[#5BB5F2]/20 px-1 py-0.5 font-mono text-[8px] text-[#5BB5F2]/60"
            >
              {p}
            </span>
          ))}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-1.5 !w-1.5 !border-[#1E2632] !bg-[#8B96A8]/60"
      />
    </div>
  );
}
