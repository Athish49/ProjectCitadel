import { NextResponse } from "next/server";
import { ARCH_NODES, ARCH_EDGES } from "@/lib/data/architecture";

export const revalidate = 30;

export function GET() {
  return NextResponse.json({
    nodes: ARCH_NODES,
    edges: ARCH_EDGES,
    snapshotAt: new Date().toISOString(),
  });
}
