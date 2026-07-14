export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8080";

const SSE_HEADERS = {
  "Content-Type":      "text/event-stream",
  "Cache-Control":     "no-cache, no-transform",
  "X-Accel-Buffering": "no",
  "Connection":        "keep-alive",
} as const;

export async function GET() {
  try {
    const upstream = await fetch(`${BACKEND_URL}/showcase/sse/audit`, {
      headers: { Accept: "text/event-stream", "Cache-Control": "no-cache" },
    });
    if (upstream.ok && upstream.body) {
      return new Response(upstream.body, { headers: SSE_HEADERS });
    }
  } catch {
    // backend not reachable
  }

  const body = new TextEncoder().encode(
    'event: backend_down\ndata: {"reason":"backend_unavailable"}\n\n'
  );
  return new Response(body, { headers: SSE_HEADERS });
}
