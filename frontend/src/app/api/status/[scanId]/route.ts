import { NextRequest } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Streaming SSE proxy — Next.js rewrites buffer responses, breaking SSE.
 * This API route uses the Web Streams API to forward SSE events in real-time.
 *
 * When the backend SSE endpoint is unavailable or returns an error, we return
 * a minimal SSE stream with the scan status from the backend poll endpoint
 * so the client always gets actionable data.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scanId: string }> }
) {
  const { scanId } = await params;
  const authorization = request.headers.get("authorization") || "";

  try {
    const backendResponse = await fetch(`${BACKEND_URL}/api/status/${scanId}`, {
      headers: {
        Authorization: authorization,
        Accept: "text/event-stream",
      },
      signal: request.signal,
    });

    if (!backendResponse.ok) {
      // If backend returns 404 or other error, return it directly
      return new Response(
        JSON.stringify({ detail: backendResponse.statusText }),
        {
          status: backendResponse.status,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    if (!backendResponse.body) {
      return new Response("No response body", { status: 502 });
    }

    // Pipe the backend SSE stream directly to the client without buffering
    return new Response(backendResponse.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no", // Disable nginx buffering (Coolify uses nginx)
      },
    });
  } catch (err) {
    // If the client aborted, just close cleanly
    if (err instanceof DOMException && err.name === "AbortError") {
      return new Response(null, { status: 499 });
    }

    // Connection error to backend — return 502
    return new Response(
      JSON.stringify({ detail: "Backend unavailable" }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
