// Shared types for scan wizard context and hooks.
// Extracted to break circular dependency between context/ and hooks/.

import type { DiscoveryReport } from '@/lib/api/types'

// ---------------------------------------------------------------------------
// Scan summaries (used by useScans hook and useDashboardData hook)
// ---------------------------------------------------------------------------

export interface ScanSummary {
  id: string
  repo_url: string
  repo_name: string
  branch: string | null
  status: string
  scan_tier: string | null
  created_at: string
  project_id: string | null
  health_score: number | null
  security_score: number | null
  reliability_score: number | null
  scalability_score: number | null
}

export interface ScanDetail {
  id: string
  repo_url: string
  repo_name: string
  branch: string | null
  status: string
  scan_tier: string | null
  created_at: string
  project_id: string | null
  health_score: number | null
  report_data?: {
    discovery_report?: DiscoveryReport
  }
}

// ---------------------------------------------------------------------------
// Dashboard aggregate
// ---------------------------------------------------------------------------

export interface DashboardData {
  scans: ScanSummary[]
  projects: import('@/lib/api/types').ProjectSummary[]
}
