import { apiFetch } from '@/lib/api/client'
import type { ProjectSummary, ProjectIntake } from '@/lib/api/types'

/**
 * Fetch all projects for the authenticated user.
 */
export async function fetchProjects(token?: string): Promise<ProjectSummary[]> {
  const resp = await apiFetch<{ items: ProjectSummary[] }>('/api/user/projects', { token })
  return resp.items
}

/**
 * Fetch project intake data for a given project.
 */
export async function fetchProjectIntake(
  projectId: string,
  token?: string,
): Promise<ProjectIntake | null> {
  const resp = await apiFetch<{ project_intake: ProjectIntake | null }>(
    `/api/user/projects/${projectId}/intake`,
    { token },
  )
  return resp.project_intake
}
