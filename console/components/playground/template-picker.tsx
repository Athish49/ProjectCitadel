"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AttackTemplate } from "@/lib/types/playground";

interface TemplatePickerProps {
  templates: AttackTemplate[];
  onSelect: (template: AttackTemplate) => void;
}

export function TemplatePicker({ templates, onSelect }: TemplatePickerProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  if (templates.length === 0) return null;

  const grouped = templates.reduce<Record<string, AttackTemplate[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex items-center gap-1.5 rounded border px-2.5 py-1 font-mono text-xs",
          "border-border text-fg-2 hover:text-fg-0 hover:border-fg-3 transition-colors",
          open && "border-fg-3 text-fg-0"
        )}
      >
        <Zap className="h-3 w-3" />
        Templates
        <ChevronDown className={cn("h-3 w-3 transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div
          className={cn(
            "absolute left-0 top-full z-50 mt-1.5 w-72 rounded border border-border",
            "bg-bg-1 shadow-lg"
          )}
        >
          <div className="max-h-80 overflow-y-auto p-1">
            {Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <div className="px-2 py-1.5 font-mono text-[10px] uppercase tracking-widest text-fg-3">
                  {category}
                </div>
                {items.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      onSelect(t);
                      setOpen(false);
                    }}
                    className={cn(
                      "w-full rounded px-2 py-1.5 text-left transition-colors",
                      "hover:bg-bg-2 group"
                    )}
                  >
                    <div className="font-mono text-xs text-fg-1 group-hover:text-fg-0">
                      {t.label}
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] text-fg-3">
                      #{t.attackId} · {t.attackName}
                    </div>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
