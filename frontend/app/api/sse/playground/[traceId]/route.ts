import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8080";

function errorStream(message: string): Response {
  const body = `event: stream_error\ndata: ${JSON.stringify({ message })}\n\n`;
  return new Response(body, {
    headers: {
      "Content-Type":      "text/event-stream",
      "Cache-Control":     "no-cache, no-transform",
      "X-Accel-Buffering": "no",
      "Connection":        "keep-alive",
    },
  });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ traceId: string }> }
) {
  const { traceId } = await params;

  let backendResp: Response;
  try {
    backendResp = await fetch(
      `${BACKEND_URL}/showcase/sse/playground/${traceId}`,
      { headers: { Accept: "text/event-stream" } }
    );
  } catch {
    return errorStream("Backend unavailable. Check that the server is running.");
  }

  if (!backendResp.ok || !backendResp.body) {
    return errorStream(`Backend returned ${backendResp.status}.`);
  }

  return new Response(backendResp.body, {
    headers: {
      "Content-Type":      "text/event-stream",
      "Cache-Control":     "no-cache, no-transform",
      "X-Accel-Buffering": "no",
      "Connection":        "keep-alive",
    },
  });
}
