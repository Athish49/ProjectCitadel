import { NextRequest, NextResponse } from "next/server";
import { getPattern } from "@/lib/data/patterns";
import type { PatternId } from "@/lib/types/showcase";

export const revalidate = 3600;

export function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ patternId: string }> }
) {
  return params.then(({ patternId }) => {
    const pattern = getPattern(patternId as PatternId);
    if (!pattern) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json(pattern);
  });
}
