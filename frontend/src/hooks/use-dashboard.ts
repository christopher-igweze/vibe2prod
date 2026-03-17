'use client'

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import type { DashboardData } from '@/types/scan-wizard.types'
import { fetchDashboardData } from '@/services/dashboard-service'

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

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const dashboard = await fetchDashboardData(token)
      setData(dashboard)
    } catch {
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, refetch: load }
}
