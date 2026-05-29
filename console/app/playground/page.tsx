"use client";

import { useState } from "react";
import { AttackComposer } from "@/components/playground/attack-composer";
import { DefenseTrace } from "@/components/playground/defense-trace";
import { buildExampleTrace } from "@/components/playground/example-trace";
import { ATTACKS } from "@/lib/data/attacks";
import type { AttackComposerTab, PlaygroundTrace, TargetFlow, SessionMode } from "@/lib/types/playground";

export default function PlaygroundPage() {
  const [trace, setTrace] = useState<PlaygroundTrace | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(
    payload: string,
    tab: AttackComposerTab,
    _targetFlow: TargetFlow,
    _sessionMode: SessionMode,
  ) {
    setIsSubmitting(true);
    setTrace(null);

    // Simulate network latency while WebSocket stream connects in Sprint 3.2.2
    await new Promise((r) => setTimeout(r, 900));

    const TAB_ATTACK: Record<AttackComposerTab, number> = {
      chat:             1,
      pdf:              2,
      image:            6,
      tool:             29,
      "cross-customer": 28,
      custom:           1,
    };

    const attackId = TAB_ATTACK[tab];
    const attack = ATTACKS.find((a) => a.attackId === attackId);
    const attackName = attack?.name ?? "Direct Prompt Injection";

    setTrace(buildExampleTrace(attackId, attackName));
    setIsSubmitting(false);
  }

  return (
    <div className="flex h-[calc(100vh-48px)] overflow-hidden">
      {/* Left pane: Attack Composer (40%) */}
      <div className="flex w-[40%] min-w-[320px] shrink-0 flex-col border-r border-border">
        <AttackComposer onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </div>

      {/* Right pane: Defense Trace (60%) */}
      <div className="flex min-w-0 flex-1 flex-col">
        <DefenseTrace trace={trace} />
      </div>
    </div>
  );
}
