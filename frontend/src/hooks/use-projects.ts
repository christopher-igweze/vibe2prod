'use client'

import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@clerk/nextjs'
import { apiFetch } from '@/lib/api/client'
import type { ProjectSummary, ProjectScanHistory } from '@/lib/api/types'

// ---------------------------------------------------------------------------
// useProjects — list all projects for the current user
// ---------------------------------------------------------------------------

export function useProjects() {
  const { getToken } = useAuth()
  const [data, setData] = useState<ProjectSummary[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const resp = await apiFetch<ProjectSummary[] | { items: ProjectSummary[] }>('/api/user/projects', { token })
      const projects = Array.isArray(resp) ? resp : resp.items ?? []
      setData(projects)
    } catch {
      setError('Failed to load projects')
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
// useProject — fetch a single project with scan history
// ---------------------------------------------------------------------------

export function useProject(projectId: string | null) {
  const { getToken } = useAuth()
  const [data, setData] = useState<ProjectScanHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    if (!projectId) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const project = await apiFetch<ProjectScanHistory>(
        `/api/user/projects/${projectId}/scans`,
        { token },
      )
      setData(project)
    } catch {
      setError('Failed to load project')
    } finally {
      setLoading(false)
    }
  }, [getToken, projectId])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { data, loading, error, refetch: fetch }
}
