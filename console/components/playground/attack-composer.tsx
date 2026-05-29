"use client";

import { useState, useEffect } from "react";
import {
  MessageSquare,
  FileText,
  Image as ImageIcon,
  Wrench,
  Users,
  Code2,
  Send,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { TemplatePicker } from "@/components/playground/template-picker";
import { UploadZone } from "@/components/playground/upload-zone";
import { ATTACK_TEMPLATES, templatesForTab } from "@/components/playground/attack-templates";
import type {
  AttackComposerTab,
  AttackTemplate,
  TargetFlow,
  SessionMode,
} from "@/lib/types/playground";

const TABS: { id: AttackComposerTab; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: "chat",           label: "Chat",          icon: MessageSquare },
  { id: "pdf",            label: "PDF",           icon: FileText      },
  { id: "image",          label: "Image",         icon: ImageIcon     },
  { id: "tool",           label: "Tool",          icon: Wrench        },
  { id: "cross-customer", label: "Cross-Cust",    icon: Users         },
  { id: "custom",         label: "Custom",        icon: Code2         },
];

const TARGET_FLOWS: { id: TargetFlow; label: string }[] = [
  { id: "intake",     label: "Intake Parser" },
  { id: "claims",     label: "Claims Processor" },
  { id: "settlement", label: "Settlement Actor" },
];

interface AttackComposerProps {
  onSubmit: (payload: string, tab: AttackComposerTab, targetFlow: TargetFlow, sessionMode: SessionMode) => Promise<void>;
  isSubmitting: boolean;
  initialTemplateId?: string | null;
}

export function AttackComposer({ onSubmit, isSubmitting, initialTemplateId }: AttackComposerProps) {
  const [tab, setTab] = useState<AttackComposerTab>("chat");
  const [payload, setPayload] = useState("");
  const [targetFlow, setTargetFlow] = useState<TargetFlow>("intake");
  const [sessionMode, setSessionMode] = useState<SessionMode>("sandboxed");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  useEffect(() => {
    if (!initialTemplateId) return;
    const tmpl = ATTACK_TEMPLATES.find((t) => t.id === initialTemplateId);
    if (!tmpl) return;
    setTab(tmpl.tab);
    setPayload(tmpl.payload);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleTemplateSelect(t: AttackTemplate) {
    setPayload(t.payload);
  }

  function handleSubmit() {
    const p = tab === "pdf" || tab === "image"
      ? uploadedFile ? `[file: ${uploadedFile.name}]` : payload
      : payload;
    if (!p.trim()) return;
    onSubmit(p, tab, targetFlow, sessionMode);
  }

  const templates = templatesForTab(tab);
  const canSubmit = !isSubmitting && (
    tab === "pdf" || tab === "image"
      ? (uploadedFile !== null || payload.trim().length > 0)
      : payload.trim().length > 0
  );

  return (
    <div className="flex h-full flex-col">
      {/* ── top bar ─────────────────────────────────────────────────────────── */}
      <div className="shrink-0 border-b border-border px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <span className="font-mono text-xs font-semibold text-fg-0">Attack Composer</span>
          <div className="flex items-center gap-2">
            {/* session mode toggle */}
            <button
              type="button"
              onClick={() => setSessionMode((m) => m === "sandboxed" ? "live" : "sandboxed")}
              className={cn(
                "flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-[10px] transition-colors",
                sessionMode === "sandboxed"
                  ? "border-ok/40 bg-ok/10 text-ok"
                  : "border-alert/40 bg-alert/10 text-alert"
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  sessionMode === "sandboxed" ? "bg-ok" : "bg-alert animate-pulse"
                )}
                aria-hidden
              />
              {sessionMode === "sandboxed" ? "Sandboxed" : "Live"}
            </button>
          </div>
        </div>

        {/* target flow selector */}
        <div className="mt-2 flex items-center gap-2">
          <span className="font-mono text-[10px] text-fg-3">Target:</span>
          <div className="flex gap-1">
            {TARGET_FLOWS.map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setTargetFlow(f.id)}
                className={cn(
                  "rounded px-2 py-0.5 font-mono text-[10px] transition-colors",
                  targetFlow === f.id
                    ? "bg-bg-3 text-fg-0"
                    : "text-fg-3 hover:text-fg-1"
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── tab bar ─────────────────────────────────────────────────────────── */}
      <div
        className="shrink-0 flex border-b border-border overflow-x-auto"
        role="tablist"
        aria-label="Attack type"
      >
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 font-mono text-[11px] transition-colors",
                tab === t.id
                  ? "border-trust text-fg-0"
                  : "border-transparent text-fg-3 hover:text-fg-1"
              )}
            >
              <Icon className="h-3 w-3" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ── tab content ─────────────────────────────────────────────────────── */}
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {tab === "pdf" && (
          <UploadZone
            accept=".pdf"
            label="Drop a PDF claim form"
            hint="Drag & drop or click to select · PDF only"
            icon="pdf"
            onFile={(f) => setUploadedFile(f)}
          />
        )}

        {tab === "image" && (
          <UploadZone
            accept="image/*"
            label="Drop a claim image"
            hint="Drag & drop or click to select · JPG / PNG"
            icon="image"
            onFile={(f) => setUploadedFile(f)}
          />
        )}

        {tab === "tool" && (
          <div className="space-y-3">
            <div className="rounded border border-border bg-bg-1 p-3">
              <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3 mb-2">
                Tool misuse simulation
              </div>
              <p className="font-mono text-xs text-fg-2 leading-relaxed">
                Select a template from the picker to pre-load a tool-abuse scenario. These
                simulations probe P4 (Capability-Scoped Tools) by attempting out-of-scope
                tool invocations without a valid capability token.
              </p>
            </div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              placeholder="Describe the tool misuse scenario or pick a template…"
              className={cn(
                "w-full min-h-[160px] rounded border border-border bg-bg-1",
                "px-3 py-2.5 font-mono text-xs text-fg-1 placeholder:text-fg-3",
                "focus:border-trust focus:outline-none resize-none transition-colors"
              )}
            />
          </div>
        )}

        {tab === "cross-customer" && (
          <div className="space-y-3">
            <div className="rounded border border-border bg-bg-1 p-3">
              <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3 mb-2">
                Cross-customer probe
              </div>
              <p className="font-mono text-xs text-fg-2 leading-relaxed">
                These attacks attempt to access another customer&apos;s data. P7 (DB-Enforced
                Tenancy / RLS) enforces row-level isolation — even if the agent generates a
                valid SQL query, the database silently filters cross-customer rows.
              </p>
            </div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              placeholder="Describe the cross-customer access attempt or pick a template…"
              className={cn(
                "w-full min-h-[160px] rounded border border-border bg-bg-1",
                "px-3 py-2.5 font-mono text-xs text-fg-1 placeholder:text-fg-3",
                "focus:border-trust focus:outline-none resize-none transition-colors"
              )}
            />
          </div>
        )}

        {tab === "custom" && (
          <div className="space-y-3">
            <div className="rounded border border-border bg-bg-1 p-3">
              <div className="font-mono text-[10px] uppercase tracking-widest text-fg-3 mb-2">
                Custom attack
              </div>
              <p className="font-mono text-xs text-fg-2 leading-relaxed">
                Free-form attack payload. Every submission passes through all 7 defense layers
                regardless of attack type.
              </p>
            </div>
            <textarea
              value={payload}
              onChange={(e) => setPayload(e.target.value)}
              placeholder="Write any attack payload…"
              className={cn(
                "w-full min-h-[180px] rounded border border-border bg-bg-1",
                "px-3 py-2.5 font-mono text-xs text-fg-1 placeholder:text-fg-3",
                "focus:border-trust focus:outline-none resize-none transition-colors"
              )}
            />
          </div>
        )}

        {(tab === "chat") && (
          <textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            placeholder="Type an attack payload, or pick a template above…"
            className={cn(
              "w-full h-full min-h-[200px] rounded border border-border bg-bg-1",
              "px-3 py-2.5 font-mono text-xs text-fg-1 placeholder:text-fg-3",
              "focus:border-trust focus:outline-none resize-none transition-colors"
            )}
          />
        )}
      </div>

      {/* ── bottom bar ──────────────────────────────────────────────────────── */}
      <div className="shrink-0 border-t border-border px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <TemplatePicker templates={templates} onSelect={handleTemplateSelect} />

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={cn(
              "flex items-center gap-2 rounded px-4 py-2 font-mono text-xs font-medium transition-colors",
              canSubmit
                ? "bg-trust text-bg-0 hover:bg-trust/90"
                : "cursor-not-allowed bg-bg-3 text-fg-3"
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Running…
              </>
            ) : (
              <>
                <Send className="h-3.5 w-3.5" />
                Run Attack
              </>
            )}
          </button>
        </div>

        {sessionMode === "live" && (
          <div className="mt-2 flex items-center gap-1.5 font-mono text-[10px] text-alert">
            <span className="h-1.5 w-1.5 rounded-full bg-alert animate-pulse" aria-hidden />
            Live mode — attacks route to the real agent pipeline
          </div>
        )}
      </div>
    </div>
  );
}
