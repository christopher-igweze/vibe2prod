// Mirrors backend/models/scan.py and backend/tier1/contracts.py

export type Actionability = 'must_fix' | 'should_fix' | 'consider' | 'informational'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Category = 'security' | 'reliability' | 'scalability'
export type FindingStatus = 'fail' | 'warn' | 'pass' | 'skip'
export type ScanStatus = 'pending' | 'scanning' | 'completed' | 'failed'
export type ProjectOrigin = 'inspired' | 'external'
export type SensitiveDataType = 'payments' | 'pii' | 'health' | 'auth_secrets' | 'none' | 'not_sure'

export interface Tier1Finding {
  check_id: string
  title: string
  description: string
  category: Category
  severity: Severity
  status: FindingStatus
  confidence: number
  actionability: Actionability
  data_flow: string
  pattern_id: string
  pattern_slug: string
  engine: string
  file_path: string
  line_number: number | null
  evidence: string
  why_it_matters: string
  suggested_fix: string
}

export interface ProjectIntake {
  project_origin: ProjectOrigin
  product_summary: string
  target_users: string
  sensitive_data: SensitiveDataType[]
  must_not_break_flows: string[]
  deployment_target: string
  scale_expectation: string
}

export interface AuditRequest {
  repo_url: string
  vibe_prompt?: string | null
  project_charter?: Record<string, unknown> | null
  project_intake: ProjectIntake
  primer?: PrimerResult | null
}

export interface AuditResponse {
  scan_id: string
  status: ScanStatus
  tier: string
  quota_remaining: number | null
  message: string
}

export interface PrimerResult {
  primer_json: Record<string, unknown>
  summary: string
  repo_sha: string
  confidence: number
  failure_reason: string | null
}

export interface ReportScores {
  health_score: number
  security_score: number
  reliability_score: number
  scalability_score: number
}

export interface ReportCounts {
  findings_total: number
  by_severity: Record<Severity, number>
  by_category: Record<Category, number>
  by_actionability: Record<Actionability, number>
}

export interface ReportSummary {
  scores: ReportScores
  counts: ReportCounts
  strengths: string[]
  execution_plan: string[]
}

export interface ReportArtifact {
  content: string
  mime_type: string
  content_encoding: string
  expires_at: string
  filename: string
}

export interface QuotaLimits {
  tier: string
  month_key: string
  reports_generated: number
  reports_limit: number
  reports_remaining: number
  project_count: number
  project_limit: number
  loc_cap: number
}

// Mirrors backend/api/routes/primer.py PrimerResponse
export interface PrimerResponse {
  project_id: string
  cached: boolean
  primer: PrimerResult
  suggested_flows: string[]
}

// Mirrors backend/models/onboarding.py
export type TechnicalLevel = 'engineer' | 'vibe_coder' | 'founder'
export type ExplanationStyle = 'teach_me' | 'just_steps' | 'cto_brief'
export type ShippingPosture = 'ship_fast' | 'balanced' | 'production_first'
export type AcquisitionSource =
  | 'x_twitter' | 'linkedin' | 'tiktok' | 'youtube' | 'reddit'
  | 'discord' | 'product_hunt' | 'indie_hackers' | 'hacker_news'
  | 'google_search' | 'newsletter_email' | 'referral'
  | 'founder_begged_me' | 'other'
export type CodingAgentProvider = 'openai' | 'anthropic' | 'google'

export interface OrgOnboardingPayload {
  technical_level: TechnicalLevel
  explanation_style: ExplanationStyle
  shipping_posture: ShippingPosture
  tool_tags: string[]
  acquisition_source: AcquisitionSource
  acquisition_other?: string | null
  coding_agent_provider: CodingAgentProvider
  coding_agent_model: string
}
