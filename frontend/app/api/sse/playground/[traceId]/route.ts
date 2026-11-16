import { NextRequest } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

const BACKEND_URL = getBackendUrl();

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
      {
        headers: {
          "Accept": "text/event-stream",
          "X-Playground-Token": process.env.NEXT_PUBLIC_PLAYGROUND_TOKEN ?? "",
        },
      }
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
