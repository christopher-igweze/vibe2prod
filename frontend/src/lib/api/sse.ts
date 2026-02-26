'use client'

export interface SSEEvent {
  event: string
  data: string
}

export type SSECallback = (event: SSEEvent) => void
export type SSEErrorCallback = (error: { status?: number; message: string }) => void

// Relative path — Next.js rewrites proxy /api/* to the backend
const API_URL = ''

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
      const response = await fetch(`${API_URL}/api/status/${scanId}`, {
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

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = 'message'
        let currentData = ''

        for (const line of lines) {
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
