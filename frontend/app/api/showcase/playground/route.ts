import { NextRequest, NextResponse } from "next/server";
import type { AttackComposerTab } from "@/lib/types/playground";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8080";

const TAB_ATTACK: Record<AttackComposerTab, { id: number; name: string }> = {
  chat:             { id: 1,  name: "Direct Prompt Injection" },
  pdf:              { id: 2,  name: "Indirect Prompt Injection" },
  image:            { id: 6,  name: "Cross-Modal / Multimodal Injection" },
  tool:             { id: 29, name: "Tool Misuse & Exploitation" },
  "cross-customer": { id: 28, name: "Semantic-Layer Data Exfiltration" },
  custom:           { id: 1,  name: "Direct Prompt Injection" },
};

export async function POST(request: NextRequest) {
  let body: { payload?: string; tab?: string; attackId?: number; attackName?: string } = {};
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { payload, tab = "chat", attackId, attackName } = body;

  if (!payload || typeof payload !== "string" || payload.trim().length === 0) {
    return NextResponse.json({ error: "payload is required" }, { status: 422 });
  }
  if (payload.length > 8000) {
    return NextResponse.json({ error: "payload too long (max 8000 chars)" }, { status: 422 });
  }

  const validTab = (tab in TAB_ATTACK ? tab : "chat") as AttackComposerTab;
  const attack = (attackId && attackName)
    ? { id: attackId, name: attackName }
    : TAB_ATTACK[validTab];

  try {
    const resp = await fetch(`${BACKEND_URL}/showcase/playground/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: payload, attack_id: attack.id }),
      signal: AbortSignal.timeout(10_000),
    });

    if (resp.ok) {
      const data = await resp.json() as {
        trace_id: string;
        sanitizer_detections: string[];
        verdict: string;
      };

      const sseUrl = `/api/sse/playground/${data.trace_id}`;

      return NextResponse.json({ traceId: data.trace_id, sseUrl, attack }, { status: 202 });
    }
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 });
  }

  return NextResponse.json({ error: "Backend returned an error" }, { status: 502 });
}
