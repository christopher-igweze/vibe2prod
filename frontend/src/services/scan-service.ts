import { apiFetch } from '@/lib/api/client'
import type { ScanSummary, ScanDetail } from '@/types/scan-wizard.types'

/**
 * Fetch all scans for the authenticated user.
 */
export async function fetchScans(token?: string): Promise<ScanSummary[]> {
  return apiFetch<ScanSummary[]>('/api/user/scans', { token })
}

/**
 * Fetch a single scan by ID.
 */
export async function fetchScan(scanId: string, token?: string): Promise<ScanDetail> {
  return apiFetch<ScanDetail>(`/api/user/scans/${scanId}`, { token })
}
