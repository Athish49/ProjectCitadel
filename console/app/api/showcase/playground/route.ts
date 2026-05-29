import { NextRequest, NextResponse } from "next/server";
import type { AttackComposerTab } from "@/lib/types/playground";

const TAB_ATTACK: Record<AttackComposerTab, { id: number; name: string }> = {
  chat:             { id: 1,  name: "Direct Prompt Injection" },
  pdf:              { id: 2,  name: "Indirect Prompt Injection" },
  image:            { id: 6,  name: "Cross-Modal / Multimodal Injection" },
  tool:             { id: 29, name: "Tool Misuse & Exploitation" },
  "cross-customer": { id: 28, name: "Semantic-Layer Data Exfiltration" },
  custom:           { id: 1,  name: "Direct Prompt Injection" },
};

export async function POST(request: NextRequest) {
  let body: { payload?: string; tab?: string } = {};
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { payload, tab = "chat" } = body;

  if (!payload || typeof payload !== "string" || payload.trim().length === 0) {
    return NextResponse.json({ error: "payload is required" }, { status: 422 });
  }
  if (payload.length > 8000) {
    return NextResponse.json({ error: "payload too long (max 8000 chars)" }, { status: 422 });
  }

  const validTab = (tab in TAB_ATTACK ? tab : "chat") as AttackComposerTab;
  const traceId = crypto.randomUUID();
  const attack = TAB_ATTACK[validTab];
  const sseUrl = `/api/sse/playground/${traceId}?tab=${encodeURIComponent(validTab)}&attackId=${attack.id}`;

  return NextResponse.json({ traceId, sseUrl, attack }, { status: 202 });
}
