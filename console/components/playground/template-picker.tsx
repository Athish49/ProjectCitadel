"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AttackTemplate } from "@/lib/types/playground";

interface TemplatePickerProps {
  templates: AttackTemplate[];
  onSelect: (template: AttackTemplate) => void;
}

interface DropdownPos {
  left: number;
  bottom: number;
  width: number;
}

export function TemplatePicker({ templates, onSelect }: TemplatePickerProps) {
  const [mounted, setMounted] = useState(false);
  const [open, setOpen]       = useState(false);
  const [pos, setPos]         = useState<DropdownPos | null>(null);
  const btnRef  = useRef<HTMLButtonElement>(null);
  const dropRef = useRef<HTMLDivElement>(null);

  // Mark as mounted so the portal only renders on the client (avoids SSR mismatch).
  useEffect(() => { setMounted(true); }, []);

  const recalc = useCallback(() => {
    if (!btnRef.current) return;
    const r = btnRef.current.getBoundingClientRect();
    setPos({
      left:   r.left,
      bottom: window.innerHeight - r.top + 6,
      width:  288,
    });
  }, []);

  useEffect(() => {
    if (!open) return;
    function onOutside(e: MouseEvent) {
      const t = e.target as Node;
      if (btnRef.current?.contains(t) || dropRef.current?.contains(t)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", onOutside);
    window.addEventListener("scroll",  recalc, true);
    window.addEventListener("resize",  recalc);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      window.removeEventListener("scroll",  recalc, true);
      window.removeEventListener("resize",  recalc);
    };
  }, [open, recalc]);

  if (templates.length === 0) return null;

  const grouped = templates.reduce<Record<string, AttackTemplate[]>>((acc, t) => {
    (acc[t.category] ??= []).push(t);
    return acc;
  }, {});

  function toggle() {
    recalc();
    setOpen((v) => !v);
  }

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onClick={toggle}
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

      {mounted && open && pos &&
        createPortal(
          <div
            ref={dropRef}
            style={{
              position: "fixed",
              left:     pos.left,
              bottom:   pos.bottom,
              width:    pos.width,
              zIndex:   9999,
            }}
            className="rounded border border-border bg-bg-1 shadow-lg"
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
                      onClick={() => { onSelect(t); setOpen(false); }}
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
          </div>,
          document.body
        )
      }
    </>
  );
}
