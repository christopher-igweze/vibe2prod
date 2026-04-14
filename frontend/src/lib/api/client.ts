'use client'

import {
  retryMiddleware,
  errorMiddleware,
  authRefreshMiddleware,
  composeMiddleware,
  type Middleware,
  type ApiRequest,
} from './middleware'

// When running through ngrok/vercel, use relative paths (Next.js rewrites proxy to backend).
// Only use absolute URL for direct local dev without proxy.
const API_URL = ''

// Composed middleware pipeline:
//   1. retryMiddleware — retry transient network failures
//   2. authRefreshMiddleware — on 401, refresh Clerk JWT and retry once
//      (prevents "Lost connection" flashes from the 60s token expiry window)
//   3. errorMiddleware — turn any remaining non-OK response into an ApiError
const apiMiddleware: Middleware = composeMiddleware(
  retryMiddleware(),
  authRefreshMiddleware(),
  errorMiddleware(),
)

// ---------------------------------------------------------------------------
// Sensitive-param protection: strip tokens/keys from URL query strings
// ---------------------------------------------------------------------------
const SENSITIVE_PARAM_PATTERN = /[?&](token|api_key|key|secret|password|auth)=[^&]*/gi

function stripSensitiveParams(url: string): string {
  const cleaned = url.replace(SENSITIVE_PARAM_PATTERN, '')
  // Fix leading '&' if the first param was stripped (e.g. "?&foo=bar" → "?foo=bar")
  return cleaned.replace(/\?&/, '?').replace(/\?$/, '')
}

// ---------------------------------------------------------------------------
// Simple in-memory GET cache with TTL
// ---------------------------------------------------------------------------
interface CacheEntry<T> {
  data: T
  expiresAt: number
}

const cache = new Map<string, CacheEntry<unknown>>()
const DEFAULT_TTL_MS = 30_000 // 30 seconds

function getCacheKey(path: string, token?: string): string {
  // Include token in key so different users don't share cached data
  return `${path}::${token ?? 'anon'}`
}

export function clearApiCache(): void {
  cache.clear()
}

export function invalidateApiCache(pathPrefix: string): void {
  for (const key of cache.keys()) {
    if (key.startsWith(pathPrefix)) {
      cache.delete(key)
    }
  }
}

// ---------------------------------------------------------------------------
// Filename sanitisation for downloads
// ---------------------------------------------------------------------------
const UNSAFE_FILENAME_CHARS = /[<>:"/\\|?*\x00-\x1F]/g
const PATH_TRAVERSAL = /\.\.[\\/]/g

export function sanitizeFilename(name: string): string {
  return name
    .replace(PATH_TRAVERSAL, '')
    .replace(UNSAFE_FILENAME_CHARS, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
    || 'download'
}

// ---------------------------------------------------------------------------
// In-flight request deduplication for GET requests
// ---------------------------------------------------------------------------
const inflight = new Map<string, Promise<unknown>>()

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string | Record<string, unknown>,
  ) {
    const msg = typeof detail === 'string' ? detail : (detail?.message as string) ?? String(detail)
    super(msg)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string; cacheTtl?: number } = {},
): Promise<T> {
  const { token, cacheTtl, ...fetchOptions } = options

  // Strip any sensitive params that may have leaked into the URL path
  const safePath = stripSensitiveParams(path)

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Check cache for GET requests (or requests with no method, which default to GET)
  const method = (fetchOptions.method ?? 'GET').toUpperCase()
  const isGet = method === 'GET'
  const ttl = cacheTtl ?? (isGet ? DEFAULT_TTL_MS : 0)

  if (isGet && ttl > 0) {
    const cacheKey = getCacheKey(safePath, token)
    const entry = cache.get(cacheKey)
    if (entry && Date.now() < entry.expiresAt) {
      return entry.data as T
    }
  }

  // Deduplicate in-flight GET requests: if an identical GET is already pending,
  // return the same promise instead of making a duplicate network request.
  const inflightKey = isGet ? getCacheKey(safePath, token) : ''
  if (isGet && inflight.has(inflightKey)) {
    return inflight.get(inflightKey) as Promise<T>
  }

  const request = (async (): Promise<T> => {
    const apiReq: ApiRequest = {
      url: `${API_URL}${safePath}`,
      init: { ...fetchOptions, headers },
    }

    // Run through middleware pipeline (retry + error normalization)
    const response = await apiMiddleware(apiReq, (req) =>
      fetch(req.url, req.init),
    )

    if (response.status === 204) return undefined as T
    const data: T = await response.json()

    // Populate cache for GET requests
    if (isGet && ttl > 0) {
      const cacheKey = getCacheKey(safePath, token)
      cache.set(cacheKey, { data, expiresAt: Date.now() + ttl })
    }

    // Invalidate related caches on mutations
    if (!isGet) {
      const basePath = safePath.split('?')[0]
      invalidateApiCache(basePath)
    }

    return data
  })()

  // Track in-flight GET requests and clean up when done
  if (isGet) {
    inflight.set(inflightKey, request)
    request.finally(() => inflight.delete(inflightKey))
  }

  return request
}
