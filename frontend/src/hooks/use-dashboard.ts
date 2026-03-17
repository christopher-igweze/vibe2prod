'use client'

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { apiFetch } from '@/lib/api/client'
import type { ProjectSummary, ProbeSummary } from '@/lib/api/types'
import type { ScanSummary, DashboardData } from '@/types/scan-wizard.types'

// Re-export shared types for backward compatibility
export type { DashboardData } from '@/types/scan-wizard.types'

// ---------------------------------------------------------------------------
// useDashboardData — load scans, projects, and probes in parallel
// ---------------------------------------------------------------------------

export function useDashboardData() {
  const { getToken } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const [scans, projects, probes] = await Promise.all([
        apiFetch<ScanSummary[]>('/api/user/scans', { token }).catch(() => [] as ScanSummary[]),
        apiFetch<ProjectSummary[]>('/api/user/projects', { token }).catch(() => [] as ProjectSummary[]),
        apiFetch<ProbeSummary[]>('/api/user/probes', { token }).catch(() => [] as ProbeSummary[]),
      ])
      setData({ scans, projects, probes })
    } catch {
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
