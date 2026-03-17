import { apiFetch } from '@/lib/api/client'
import type { ProjectSummary, ProbeSummary } from '@/lib/api/types'
import type { ScanSummary, DashboardData } from '@/types/scan-wizard.types'

/**
 * Fetch all dashboard data (scans, projects, probes) in parallel.
 * Individual failures are silently caught and return empty arrays.
 */
export async function fetchDashboardData(token?: string): Promise<DashboardData> {
  const [scans, projects, probes] = await Promise.all([
    apiFetch<ScanSummary[]>('/api/user/scans', { token }).catch(() => [] as ScanSummary[]),
    apiFetch<ProjectSummary[]>('/api/user/projects', { token }).catch(() => [] as ProjectSummary[]),
    apiFetch<ProbeSummary[]>('/api/user/probes', { token }).catch(() => [] as ProbeSummary[]),
  ])
  return { scans, projects, probes }
}
