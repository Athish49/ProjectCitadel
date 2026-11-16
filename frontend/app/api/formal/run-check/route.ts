import { NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

const BACKEND_URL = getBackendUrl();

export async function GET() {
  try {
    const resp = await fetch(`${BACKEND_URL}/formal/run-check`, {
      method: "GET",
      signal: AbortSignal.timeout(10_000),
    });

    if (!resp.ok) {
      return NextResponse.json({ error: "Backend returned an error" }, { status: 502 });
    }

    return NextResponse.json(await resp.json());
  } catch {
    return NextResponse.json({ error: "Backend unavailable" }, { status: 503 });
  }
}
