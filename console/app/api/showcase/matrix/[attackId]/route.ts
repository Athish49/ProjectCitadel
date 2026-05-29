import { NextRequest, NextResponse } from "next/server";
import { getAttack } from "@/lib/data/attacks";

export const revalidate = 60;

export function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ attackId: string }> }
) {
  return params.then(({ attackId }) => {
    const id = parseInt(attackId, 10);
    if (isNaN(id) || id < 1 || id > 79) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    const entry = getAttack(id);
    if (!entry) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    return NextResponse.json({
      attackId: entry.attackId,
      name: entry.name,
      description: entry.description,
      class: "UNTESTED",
      patterns: entry.patterns,
      codeRefs: [],
      recentAttempts: [],
    });
  });
}
