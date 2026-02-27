import { NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Streaming SSE proxy — Next.js rewrites buffer responses, breaking SSE.
 * This API route uses the Web Streams API to forward SSE events in real-time.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scanId: string }> }
) {
  const { scanId } = await params;
  const authorization = request.headers.get("authorization") || "";

  const backendResponse = await fetch(`${BACKEND_URL}/api/status/${scanId}`, {
    headers: {
      Authorization: authorization,
      Accept: "text/event-stream",
    },
  });

  if (!backendResponse.ok) {
    return new Response(backendResponse.statusText, {
      status: backendResponse.status,
    });
  }

  if (!backendResponse.body) {
    return new Response("No response body", { status: 502 });
  }

  // Pipe the backend SSE stream directly to the client
  return new Response(backendResponse.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
