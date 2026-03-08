'use client'

// When running through ngrok/vercel, use relative paths (Next.js rewrites proxy to backend).
// Only use absolute URL for direct local dev without proxy.
const API_URL = ''

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
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const { token, ...fetchOptions } = options
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    const detail = body.detail
    throw new ApiError(response.status, detail ?? response.statusText)
  }

  if (response.status === 204) return undefined as T
  return response.json()
}
