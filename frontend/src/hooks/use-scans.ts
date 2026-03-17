'use client'

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import type { ScanSummary, ScanDetail } from '@/types/scan-wizard.types'
import { fetchScans, fetchScan } from '@/services/scan-service'

// Re-export shared types for backward compatibility
export type { ScanSummary, ScanDetail } from '@/types/scan-wizard.types'

// ---------------------------------------------------------------------------
// useScans — list all scans for the current user
// ---------------------------------------------------------------------------

export function useScans() {
  const { getToken } = useAuth()
  const [data, setData] = useState<ScanSummary[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const scans = await fetchScans(token)
      setData(scans)
    } catch {
      setError('Failed to load scans')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, refetch: load }
}

// ---------------------------------------------------------------------------
// useScan — fetch a single scan by ID
// ---------------------------------------------------------------------------

export function useScan(scanId: string | null) {
  const { getToken } = useAuth()
  const [data, setData] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!scanId) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const scan = await fetchScan(scanId, token)
      setData(scan)
    } catch {
      setError('Failed to load scan')
    } finally {
      setLoading(false)
    }
  }, [getToken, scanId])

  useEffect(() => {
    load()
  }, [load])

  return { data, loading, error, refetch: load }
}
