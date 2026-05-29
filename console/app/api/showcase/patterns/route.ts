import { NextResponse } from "next/server";
import { PATTERNS } from "@/lib/data/patterns";

export const revalidate = 3600;

export function GET() {
  return NextResponse.json({
    patterns: PATTERNS,
    generatedAt: new Date().toISOString(),
  });
}
