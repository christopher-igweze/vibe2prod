// Mirrors backend/models/scan.py and FORGE discovery report schema

export type Actionability = 'must_fix' | 'should_fix' | 'consider' | 'informational'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Category = 'security' | 'architecture' | 'quality' | 'reliability' | 'performance'
export type ScanStatus = 'pending' | 'scanning' | 'completed' | 'failed'
export type ProjectOrigin = 'inspired' | 'external'
export type SensitiveDataType = 'payments' | 'pii' | 'health' | 'auth_secrets' | 'none' | 'not_sure'

// ── FORGE Discovery Report types ──────────────────────────────────

export interface FindingLocation {
  file_path: string
  line_start: number | null
  line_end: number | null
  snippet: string
}

export interface DiscoveryFinding {
  id: string
  title: string
  description: string
  category: Category
  severity: Severity
  audit_pass: boolean | null
  locations: FindingLocation[]
  suggested_fix: string
  confidence: number
  cwe_id: string
  owasp_ref: string
  agent: string
  tier: number
  dedup_key: string
  actionability?: Actionability
  intent_signal?: string
  pattern_id?: string
  data_flow?: string
}

export interface RemediationItem {
  finding_id: string
  title: string
  tier: number
  priority: number
  estimated_files: number
  files_to_modify: string[]
  depends_on: string[]
  acceptance_criteria: string[]
  approach: string
  group: string
}

export interface RemediationDependency {
  finding_id: string
  depends_on_finding_id: string
  reason: string
}

export interface RemediationPlan {
  items: RemediationItem[]
  dependencies: RemediationDependency[]
  execution_levels: string[][]
}

export interface CodebaseModule {
  name: string
  path: string
  purpose: string
  files: string[]
  loc: number
  language: string
}

export interface DataFlow {
  source: string
  destination: string
  data_type: string
  is_authenticated: boolean
}

export interface AuthBoundary {
  path: string
  auth_type: string
  is_protected: boolean
}

export interface EntryPoint {
  path: string
  type: string
  is_public: boolean
}

export interface CodebaseMap {
  modules: CodebaseModule[]
  entry_points: EntryPoint[]
  data_flows: DataFlow[]
  auth_boundaries: AuthBoundary[]
  architecture_summary: string
  key_patterns: string[]
  loc_total: number
  file_count: number
  primary_language: string
  languages: string[]
}

export interface DependencyGraphSegment {
  id: string
  label: string
  files: string[]
  loc: number
  finding_count: number
  internal_deps: string[]
  external_deps: string[]
  entry_points: string[]
}

export interface DependencyGraph {
  total_nodes: number
  total_edges: number
  total_segments: number
  segments: DependencyGraphSegment[]
}

export interface ActionabilitySummary {
  must_fix_count: number
  should_fix_count: number
  consider_count: number
  informational_count: number
  signal_to_noise_ratio: number
}

export interface DiscoveryReport {
  run_id: string
  generated_at: string
  phase: string
  duration_seconds: number
  cost_usd: number
  loc_total: number
  file_count: number
  primary_language: string
  total_findings: number
  severity_breakdown: Record<Severity, number>
  category_breakdown: Record<string, number>
  actionability_summary: ActionabilitySummary | null
  findings: DiscoveryFinding[]
  remediation_plan: RemediationPlan | null
  codebase_map: CodebaseMap | null
  dependency_graph: DependencyGraph | null
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
  project_intake?: ProjectIntake
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

export interface QuotaLimits {
  tier: string
  project_count: number
  project_limit: number
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
