import { NextRequest, NextResponse } from "next/server";
import { ATTACKS, toMatrixRow } from "@/lib/data/attacks";
import type { MatrixClass, PatternId } from "@/lib/types/showcase";

export const revalidate = 60;

export function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const classFilter = searchParams.get("class") as MatrixClass | null;
  const patternFilter = searchParams.get("pattern") as PatternId | null;

  let rows = ATTACKS.map(toMatrixRow);

  if (classFilter) {
    rows = rows.filter((r) => r.class === classFilter);
  }
  if (patternFilter) {
    rows = rows.filter((r) => r.patterns.includes(patternFilter));
  }

  return NextResponse.json({
    rows,
    generatedAt: new Date().toISOString(),
  });
}
