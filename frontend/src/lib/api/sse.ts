'use client'

export interface SSEEvent {
  event: string
  data: string
}

export type SSECallback = (event: SSEEvent) => void
export type SSEErrorCallback = (error: { status?: number; message: string }) => void

// SSE goes through a Next.js API route (/app/api/status/[scanId]/route.ts)
// that streams the backend response via Web Streams API. Next.js rewrites
// buffer responses and break SSE, but a proper route handler streams fine.

/**
 * Connect to an SSE stream using fetch + ReadableStream.
 * Uses fetch (not EventSource) to pass Bearer token in headers.
 * Returns an abort function to disconnect.
 */
export function connectSSE(
  scanId: string,
  token: string,
  onEvent: SSECallback,
  onError: SSEErrorCallback,
): () => void {
  const controller = new AbortController()

  ;(async () => {
    try {
      const response = await fetch(`/api/status/${scanId}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      })

      if (!response.ok) {
        onError({ status: response.status, message: response.statusText })
        return
      }

      const reader = response.body?.getReader()
      if (!reader) {
        onError({ message: 'No response body' })
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = 'message'
      let currentData = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const rawLine of lines) {
          // sse-starlette uses \r\n — strip trailing \r
          const line = rawLine.replace(/\r$/, '')

          // Skip SSE comments (keepalive pings)
          if (line.startsWith(':')) continue

          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6)
          } else if (line === '' && currentData) {
            onEvent({ event: currentEvent, data: currentData })
            currentEvent = 'message'
            currentData = ''
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      onError({ message: err instanceof Error ? err.message : 'SSE connection failed' })
    }
  })()

  return () => controller.abort()
}
