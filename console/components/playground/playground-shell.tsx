"use client";

import { useEffect } from "react";
import { AttackComposer } from "@/components/playground/attack-composer";
import { DefenseTrace } from "@/components/playground/defense-trace";
import { usePlaygroundStream } from "@/lib/hooks/use-playground-stream";
import { ATTACK_TEMPLATES } from "@/components/playground/attack-templates";
import type { AttackComposerTab } from "@/lib/types/playground";

interface PlaygroundShellProps {
  initialTemplateId: string | null;
  initialTab: AttackComposerTab | null;
  autorun: boolean;
}

export function PlaygroundShell({ initialTemplateId, initialTab, autorun }: PlaygroundShellProps) {
  const { trace, isStreaming, error, submit } = usePlaygroundStream();

  useEffect(() => {
    if (!autorun) return;

    const tmpl = initialTemplateId
      ? ATTACK_TEMPLATES.find((t) => t.id === initialTemplateId)
      : null;

    const tab: AttackComposerTab = tmpl?.tab ?? initialTab ?? "chat";
    const payload = tmpl?.payload ?? "[replay]";

    const id = setTimeout(() => {
      submit(
        payload,
        tab,
        tmpl?.tab === "cross-customer" ? "claims" : tmpl?.tab === "tool" ? "settlement" : "intake",
        "sandboxed",
        tmpl ? { id: tmpl.attackId, name: tmpl.attackName } : undefined,
        { isReplay: true },
      );
    }, 300);

    return () => clearTimeout(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden">
      {/* Left pane: Attack Composer (40%) */}
      <div className="flex w-[40%] min-w-[320px] shrink-0 flex-col border-r border-border">
        <AttackComposer
          onSubmit={submit}
          isSubmitting={isStreaming}
          initialTemplateId={initialTemplateId}
        />
      </div>

      {/* Right pane: Defense Trace (60%) */}
      <div className="flex min-w-0 flex-1 flex-col">
        {error && (
          <div className="shrink-0 border-b border-alert/40 bg-alert/10 px-4 py-2 font-mono text-xs text-alert">
            {error}
          </div>
        )}
        <DefenseTrace trace={trace} />
      </div>
    </div>
  );
}
