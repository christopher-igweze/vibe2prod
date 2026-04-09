import { apiFetch } from '@/lib/api/client'
import type { ProjectSummary } from '@/lib/api/types'
import type { ScanSummary, DashboardData } from '@/types/scan-wizard.types'

/**
 * Fetch all dashboard data (scans, projects) in parallel.
 * Individual failures are silently caught and return empty arrays.
 */
export async function fetchDashboardData(token?: string): Promise<DashboardData> {
  const [scans, projects] = await Promise.all([
    apiFetch<ScanSummary[] | { items: ScanSummary[] }>('/api/user/scans', { token }).then(r => Array.isArray(r) ? r : r.items ?? []).catch(() => [] as ScanSummary[]),
    apiFetch<ProjectSummary[] | { items: ProjectSummary[] }>('/api/user/projects', { token }).then(r => Array.isArray(r) ? r : r.items ?? []).catch(() => [] as ProjectSummary[]),
  ])
  return { scans, projects }
}
