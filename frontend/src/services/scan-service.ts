import { apiFetch } from '@/lib/api/client'
import type { ScanSummary, ScanDetail } from '@/types/scan-wizard.types'

/**
 * Fetch all scans for the authenticated user.
 */
export async function fetchScans(token?: string): Promise<ScanSummary[]> {
  const resp = await apiFetch<ScanSummary[] | { items: ScanSummary[] }>('/api/user/scans', { token })
  return Array.isArray(resp) ? resp : resp.items ?? []
}

/**
 * Fetch a single scan by ID.
 */
export async function fetchScan(scanId: string, token?: string): Promise<ScanDetail> {
  return apiFetch<ScanDetail>(`/api/user/scans/${scanId}`, { token })
}
