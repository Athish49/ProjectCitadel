import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

const BACKEND_URL = getBackendUrl();

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ key: string }> }
) {
  const { key } = await params;

  let resp: Response;
  try {
    resp = await fetch(`${BACKEND_URL}/showcase/playground/profile/${key}`, {
      method: "GET",
      headers: {
        "X-Playground-Token": process.env.NEXT_PUBLIC_PLAYGROUND_TOKEN ?? "",
      },
    });
  } catch {
    return NextResponse.json({ error: "Profile not found" }, { status: 404 });
  }

  if (!resp.ok) {
    return NextResponse.json({ error: "Profile not found" }, { status: 404 });
  }

  return NextResponse.json(await resp.json());
}
