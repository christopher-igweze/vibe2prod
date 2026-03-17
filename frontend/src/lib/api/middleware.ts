/**
 * API client middleware layer for consistent error handling, retry logic, and logging.
 *
 * Middleware functions wrap the fetch call and can modify requests/responses or
 * handle errors uniformly.
 */

import { ApiError } from './client'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiRequest {
  url: string
  init: RequestInit
}

export interface NormalizedError {
  code: number
  message: string
}

export type NextFn = (req: ApiRequest) => Promise<Response>
export type Middleware = (req: ApiRequest, next: NextFn) => Promise<Response>

// ---------------------------------------------------------------------------
// retryMiddleware — retry on network errors only, not 4xx/5xx
// ---------------------------------------------------------------------------

const MAX_RETRIES = 2
const BASE_DELAY_MS = 500

export function retryMiddleware(
  maxRetries: number = MAX_RETRIES,
  baseDelay: number = BASE_DELAY_MS,
): Middleware {
  return async (req: ApiRequest, next: NextFn): Promise<Response> => {
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await next(req)
        // Don't retry HTTP error responses (4xx, 5xx) — only network failures
        return response
      } catch (err) {
        // Only retry on network errors (TypeError from fetch = network failure)
        if (err instanceof TypeError) {
          lastError = err
          if (attempt < maxRetries) {
            const delay = baseDelay * Math.pow(2, attempt)
            await new Promise((resolve) => setTimeout(resolve, delay))
            continue
          }
        }
        // Non-network error (e.g. AbortError): don't retry
        throw err
      }
    }

    // All retries exhausted
    throw lastError ?? new Error('Request failed after retries')
  }
}

// ---------------------------------------------------------------------------
// errorMiddleware — normalize error responses into a consistent shape
// ---------------------------------------------------------------------------

export function normalizeApiError(status: number, body: unknown): NormalizedError {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as Record<string, unknown>).detail
    const message =
      typeof detail === 'string'
        ? detail
        : (detail as Record<string, unknown>)?.message
          ? String((detail as Record<string, unknown>).message)
          : JSON.stringify(detail)
    return { code: status, message }
  }
  if (body && typeof body === 'object' && 'message' in body) {
    return { code: status, message: String((body as Record<string, unknown>).message) }
  }
  return { code: status, message: `Request failed with status ${status}` }
}

export function errorMiddleware(): Middleware {
  return async (req: ApiRequest, next: NextFn): Promise<Response> => {
    const response = await next(req)

    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: response.statusText }))
      const normalized = normalizeApiError(response.status, body)
      throw new ApiError(normalized.code, normalized.message)
    }

    return response
  }
}

// ---------------------------------------------------------------------------
// composeMiddleware — chain multiple middleware into a single function
// ---------------------------------------------------------------------------

export function composeMiddleware(...middlewares: Middleware[]): Middleware {
  return (req: ApiRequest, next: NextFn): Promise<Response> => {
    let index = middlewares.length - 1

    const chain = (i: number): NextFn => {
      if (i < 0) return next
      return (r: ApiRequest) => middlewares[i](r, chain(i - 1))
    }

    return chain(index)(req)
  }
}
