'use client'

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { apiFetch } from '@/lib/api/client'
import type { ProbeSummary, ProbeDetail, ProbeFinding } from '@/lib/api/types'

// ---------------------------------------------------------------------------
// useProbes — list all probes for the current user
// ---------------------------------------------------------------------------

export function useProbes() {
  const { getToken } = useAuth()
  const [data, setData] = useState<ProbeSummary[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const probes = await apiFetch<ProbeSummary[]>('/api/user/probes', { token })
      setData(probes)
    } catch {
      setError('Failed to load probes')
    } finally {
      setLoading(false)
    }
  }, [getToken])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

// ---------------------------------------------------------------------------
// useProbe — fetch a single probe by ID (public endpoint, no auth needed)
// ---------------------------------------------------------------------------

export function useProbe(probeId: string | null) {
  const [data, setData] = useState<ProbeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    if (!probeId) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const probe = await apiFetch<ProbeDetail>(`/api/probe/${probeId}`, { cacheTtl: 0 })
      setData(probe)
    } catch {
      setError('Failed to load probe')
    } finally {
      setLoading(false)
    }
  }, [probeId])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}

// ---------------------------------------------------------------------------
// useProbeFindings — fetch findings for a completed probe (requires auth)
// ---------------------------------------------------------------------------

export function useProbeFindings(probeId: string | null) {
  const { getToken, isSignedIn } = useAuth()
  const [data, setData] = useState<ProbeFinding[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    if (!probeId || !isSignedIn) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const findings = await apiFetch<ProbeFinding[]>(`/api/probe/${probeId}/findings`, { token })
      setData(findings)
    } catch {
      setError('Failed to load probe findings')
    } finally {
      setLoading(false)
    }
  }, [getToken, isSignedIn, probeId])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
