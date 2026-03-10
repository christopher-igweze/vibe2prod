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
export type CodingTool =
  | 'claude_code' | 'codex' | 'antigravity' | 'cursor'
  | 'replit' | 'lovable' | 'other'
export type AcquisitionSource =
  | 'hackathon' | 'linkedin' | 'founder_begged_me'
  | 'x_twitter' | 'threads' | 'other'

export interface OrgOnboardingPayload {
  technical_level: TechnicalLevel
  explanation_style: ExplanationStyle
  shipping_posture: ShippingPosture
  tool_tags: string[]
  coding_tool: CodingTool
  coding_tool_other?: string | null
  acquisition_source: AcquisitionSource
  acquisition_other?: string | null
}

// ── FORGE Fix / Remediation types ────────────────────────────────

export interface FixResponse {
  fix_attempt_id: string
  status: string
  message: string
}

export interface CategoryScore {
  category: string
  score: number
  max_score: number
  findings_count: number
  fixed_count: number
}

export interface DebtItem {
  severity: Severity
  title: string
  description: string
  source_finding_id: string
}

export interface ProductionReadinessReport {
  overall_score: number
  category_scores: CategoryScore[]
  recommendations: string[]
  debt_items: DebtItem[]
  investor_summary: string
}

export interface ValidationResult {
  passed: boolean
  tests_run: number
  tests_passed: number
  tests_failed: number
  regressions_detected: number
  new_issues_introduced: number
  summary: string
}

export interface RemediationResult {
  fix_attempt_id: string
  status: 'pending' | 'running' | 'success' | 'failed'
  forge_run_id: string
  findings_fixed: number
  findings_deferred: number
  agent_invocations: number
  cost_usd: number
  duration_seconds: number
  readiness_report: ProductionReadinessReport
  validation: ValidationResult
  pr_url: string | null
  summary: string
}

// ── FORGE Remediation Report types (matches forge-engine schemas) ────

export interface ForgeCategoryScore {
  name: string
  score: number      // 0-100
  weight: number
  details: string
}

export interface ForgeDebtItem {
  title: string
  description: string
  severity: Severity
  category: string
  source_finding_id: string
  reason_deferred: string
}

export interface ForgeReadinessReport {
  overall_score: number
  category_scores: ForgeCategoryScore[]
  findings_total: number
  findings_fixed: number
  findings_deferred: number
  debt_items: ForgeDebtItem[]
  summary: string
  recommendations: string[]
  investor_summary: string
}

// ── ScanFixStatus (matches GET /api/fix-scan/{scanId}/status) ────

export interface ScanFixStatus {
  fix_attempt_id: string
  scan_id: string
  status: 'pending' | 'running' | 'success' | 'failed'
  findings_fixed: number | null
  findings_deferred: number | null
  readiness_score: number | null
  pr_url: string | null
  summary: string | null
  cost_usd: number | null
  duration_seconds: number | null
  readiness_report: ForgeReadinessReport | null
  agent_invocations: number | null
  error: string | null
}

// ── Project & Scan History ────────────────────────────────────────

export interface ProjectSummary {
  id: string
  repo_url: string
  repo_name: string | null
  scan_count: number
  latest_health_score: number | null
  latest_scan_tier: string | null
  created_at: string
  updated_at: string
}

export interface ScanHistoryItem {
  id: string
  status: string
  scan_tier: string
  health_score: number | null
  security_score: number | null
  reliability_score: number | null
  scalability_score: number | null
  created_at: string
  completed_at: string | null
}

export interface ProjectScanHistory {
  project: ProjectSummary
  scans: ScanHistoryItem[]
}

// ── User roles & profile ─────────────────────────────────────────

export type UserRole = 'developer' | 'beta_tester' | 'user'

export interface UserProfile {
  user_id: string
  role: UserRole
  onboarding_complete: boolean
  tour_completed?: boolean
  technical_level?: TechnicalLevel | null
  lifetime_scans_used: number
  lifetime_scan_cap: number
  scan_credits: number
  balance_usd: number
  email?: string | null
  display_name?: string | null
  avatar_url?: string | null
}

export interface DepositOption {
  id: string
  amount_cents: number
  label: string
}

export interface CreditTransaction {
  id: string
  user_id: string
  amount: number
  balance_after: number
  type: 'purchase' | 'usage' | 'free_grant'
  stripe_session_id: string | null
  package_name: string | null
  created_at: string
}
