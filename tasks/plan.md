# Vibe2Prod: Master Implementation Plan

## Context

Vibe2Prod has a strong backend (12-agent FORGE pipeline with full remediation + validation) and solid strategy docs, but multiple layers of the product are misaligned:

1. **UI undersells the product** — Landing page says "tells you if it's ready" instead of "we harden it." Positioned as a scanner when FORGE is the only tool that auto-fixes.
2. **Remediation/Validation invisible** — `POST /api/fix` exists, all 12 agents work E2E (15 live tests pass), but the frontend only shows discovery results. No "Fix with FORGE" button, no Production Readiness Score display, no validation evidence.
3. **Strategy is documented but not operationalized** — Competitive moat docs (5 moats, AdalFlow learning loop, NIST SSDF compliance) are excellent strategy, but the learning loop is a data collection skeleton (telemetry captures data, never feeds back), compliance layer is completely unbuilt, and none of this surfaces in the product.
4. **Report downloads missing** — Landing page promises PDF/MD, only JSON exists.
5. **Frontend polish gaps** — SSE polling instead of streaming, no findings filters, no quota display.

**What exists in FORGE engine today:**
- All 12 agents fully implemented with proper prompts
- 3 nested control loops (inner retry max 3, middle escalation, outer replan max 1)
- `ForgeTelemetry` captures per-agent costs, training data entries, findings history
- `ProductionReadinessReport` with overall_score (0-100), category_scores, debt_items, investor_summary
- `IntegrationValidationResult` with tests_run/passed/failed, regressions detected
- 3 curated vulnerability patterns (VP-001 through VP-003) with prevalence tracking schema
- Checkpoint/resume system at phase boundaries
- Git worktree isolation for parallel fix execution

**What's specced but NOT built:**
- AdalFlow/LLM-AutoDiff prompt optimization (backward LLM, textual gradients)
- NIST SSDF compliance mapping & hardening attestations
- Pattern extraction from findings_history (proposed/ dir is empty)
- Feedback loop from training_data.jsonl → prompt refinement
- Fine-tuning pipeline for specialist models

**Goal:** Surface the full Discover → Fix → Validate pipeline in the UI, operationalize the competitive moat (learning loop + compliance), close frontend gaps, and add report download formats.

---

## Priority Order

| Priority | Workstream | Why |
|----------|-----------|-----|
| **P0** | WS2: Landing Page Competitive Moat | Highest impact — changes how every visitor perceives the product |
| **P0** | WS3: Remediation + Validation UI | The core differentiator has no frontend — this is the moat made real |
| **P1** | WS4: Report Download (PDF/MD) | Promised on landing page, credibility gap |
| **P1** | WS5: FORGE Learning Loop (AdalFlow) | The data moat — specced in strategy, telemetry exists, feedback loop missing |
| **P1** | WS6: Compliance & Trust Layer | NIST SSDF mapping, hardening attestations — enterprise buyer unlocks |
| **P2** | WS1: Frontend Polish (SSE, filters, quota) | Important but not differentiating |

---

## WS2: Landing Page Competitive Moat Rewrite

**File:** [page.tsx](frontend/src/app/page.tsx)

### Task 2.1 — Rewrite HeroSection + Visual Upgrades `[Medium]` **DECISION: Copy + subtle visual flair**
- **Current:** "Ship AI Code With Confidence" / "tells you if it's ready for production"
- **New copy:**
  - Badge: "The only AI audit that fixes what it finds"
  - H1: "Discover. Fix. Ship." (with "Fix" in emerald-400)
  - Subtitle: "Your AI wrote the code. Vibe2Prod audits it, auto-fixes critical issues, and validates the result — 12 specialized agents, zero manual triage."
- **Visual upgrades:**
  - Subtle gradient background on hero (dark gray → slight emerald tint)
  - Fade-in-up animation on hero text using CSS `@keyframes` (no framer-motion dependency)
  - Soft glow effect behind the H1 using `bg-gradient-radial` or `box-shadow`
- Keep existing CTA buttons (Get Started / Sign In / Dashboard)

### Task 2.2 — Rewrite FeaturesSection as 3-Phase Pipeline `[Medium]`
- Replace "Paste. Scan. Ship" with the actual pipeline:
  1. **Discover** — "12 AI agents analyze security, architecture, reliability, and quality. Context-aware findings classified by actionability, not just severity."
  2. **Fix** — "FORGE's 3-loop remediation engine auto-fixes critical issues, generates tests, and handles escalation. No manual patching."
  3. **Validate** — "Integration validator confirms fixes don't break functionality. Get a Production Readiness Score (0-100) before you ship."
- Switch from emoji icons to lucide-react icons (`Search`, `Wrench`, `ShieldCheck`)
- Heading: "The Full Pipeline" or "Discover. Fix. Validate."
- **Visual upgrade:** Staggered fade-in animation on the 3 cards, subtle border glow on hover

### Task 2.3 — Rewrite StatsSection `[Small]`
- **Current:** "15+ Static Checks", "3 Vulnerability Patterns", "< 2 min Scan Time", "4 Actionability Tiers"
- **New:** "12 Specialized AI Agents", "3 Control Loops", "0-100 Production Readiness Score", "Auto-Fix, Not Just Reports"

### Task 2.4 — Add Comparison Section `[Medium]`
- New `ComparisonSection` between ActionabilitySection and StatsSection
- Two-column layout:
  - Left: "Detection Tools (CodeRabbit, Greptile, Snyk)" — "Find problems. Generate reports. Leave you to fix everything."
  - Right: "Vibe2Prod FORGE" — "Find problems. Auto-fix them. Validate the result. Ship production-ready."
- Simple Card-based layout, no new dependencies

### Task 2.5 — Keep ActionabilitySection as-is
- Already well-differentiated, no changes needed

---

## WS3: FORGE Remediation + Validation UI (Differentiation)

The FORGE engine already produces rich remediation + validation data that the frontend doesn't expose. Key data structures from the engine:

**ForgeResult** (from `forge_bridge.py`):
```python
forge_run_id, success, mode, summary, total_findings, findings_fixed,
findings_deferred, agent_invocations, cost_usd, duration_seconds,
readiness_report: {
    overall_score (0-100),
    category_scores: [{category, score, max_score, findings_count, fixed_count}],
    recommendations: [str],
    debt_items: [{severity, title, description, source_finding_id}],
    investor_summary: str  # "viral hook" narrative
}
```

**IntegrationValidationResult** (Agent 11):
```python
passed (bool), tests_run, tests_passed, tests_failed,
regressions_detected, new_issues_introduced, summary
```

### Task 3.1 — Add Fix/Remediation Types to Frontend `[Small]`
**File:** [types.ts](frontend/src/lib/api/types.ts)

```typescript
export interface FixResponse { fix_attempt_id: string; status: string; message: string }
export interface CategoryScore {
  category: string; score: number; max_score: number;
  findings_count: number; fixed_count: number;
}
export interface DebtItem { severity: Severity; title: string; description: string; source_finding_id: string }
export interface ProductionReadinessReport {
  overall_score: number;               // 0-100
  category_scores: CategoryScore[];    // Security, Error Handling, Test Coverage, etc.
  recommendations: string[];
  debt_items: DebtItem[];
  investor_summary: string;            // narrative for execs
}
export interface ValidationResult {
  passed: boolean; tests_run: number; tests_passed: number;
  tests_failed: number; regressions_detected: number;
  new_issues_introduced: number; summary: string;
}
export interface RemediationResult {
  fix_attempt_id: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  forge_run_id: string;
  findings_fixed: number;
  findings_deferred: number;
  agent_invocations: number;
  cost_usd: number;
  duration_seconds: number;
  readiness_report: ProductionReadinessReport;
  validation: ValidationResult;
  pr_url: string | null;
  summary: string;
}
```

### Task 3.2 — Backend: Scan-Level Remediation Endpoint `[Medium]` **DECISION: New endpoint**
**File:** [fix.py](backend/api/routes/fix.py)

- Add `POST /api/fix-scan/{scan_id}` — looks up scan findings, creates fix_attempt, calls `trigger_forge_remediate()` in background, returns `FixResponse`
- Add `GET /api/fix-scan/{scan_id}/status` — returns current fix_attempt status + results (findings_fixed, findings_deferred, readiness_score, pr_url)
- Reuses existing `trigger_forge_remediate()` from [forge_bridge.py](backend/services/forge_bridge.py)
- This replaces the per-action-item approach — one button, one click to remediate the whole scan

### Task 3.3 — Production Readiness Score Gauge Component `[Medium]`
**New file:** `frontend/src/components/score-gauge.tsx`

- Reusable SVG circular gauge: `{ score: number, label: string, size?: number }`
- SVG circle with `stroke-dashoffset` animation
- Color: red (0-39), yellow (40-69), green (70+)
- Pure Tailwind colors, no external dependencies
- Used on report page and potentially dashboard

### Task 3.4 — "Fix with FORGE" Button on Report Header `[Medium]`
**File:** [report-header.tsx](frontend/src/app/(app)/scan/[scanId]/report/_components/report-header.tsx)

- Prominent emerald CTA button with `Wrench` icon, positioned as primary action
- Calls `POST /api/fix-scan/{scan_id}`
- Shows loading state during request
- On success, navigates to remediation progress page
- Only rendered when scan status is `completed` and no active fix_attempt exists

### Task 3.5 — Remediation Progress Page `[Medium]`
**New file:** `frontend/src/app/(app)/scan/[scanId]/remediation/page.tsx`

- Follows same pattern as existing [scan progress page](frontend/src/app/(app)/scan/[scanId]/page.tsx)
- Shows phase indicators: Discovery (complete) → Remediation (in progress) → Validation (pending)
- Polls `GET /api/fix-scan/{scan_id}/status` every 5 seconds
- On completion, redirects to report page with remediation results visible

### Task 3.6 — Remediation Results Page (Separate Route) `[Large]` **DECISION: Separate page**
**New file:** `frontend/src/app/(app)/scan/[scanId]/remediation/results/page.tsx`
**New components:** `frontend/src/app/(app)/scan/[scanId]/remediation/results/_components/`

Dedicated page at `/scan/{id}/remediation/results` showing:

**Hero Section:**
1. **Production Readiness Score** — large gauge component (Task 3.3) as hero metric, centered prominently
2. **Investor Summary** — `readiness_report.investor_summary` narrative text below score

**Category Breakdown Section:**
3. **Category Score Cards** — grid of mini-gauges for each category (Security, Error Handling, Test Coverage, Architecture, Performance, Documentation) from `readiness_report.category_scores[]`
4. Each card shows: category name, score/max_score, findings_count → fixed_count

**Remediation Stats Section:**
5. **Before/After Card** — total_findings → findings_fixed (green) / findings_deferred (yellow)
6. **Agent Stats** — agent_invocations count, duration_seconds, cost_usd
7. **Validation Badge** — `validation.passed` with tests_run/passed/failed breakdown

**Findings Detail Section:**
8. **Fixed Findings List** — collapsible list of what was fixed
9. **Deferred/Debt Items** — `readiness_report.debt_items[]` with severity + description
10. **Recommendations** — `readiness_report.recommendations[]` as action items

**Actions:**
11. **PR Link** — prominent button to generated PR (if `pr_url` present)
12. **Navigation** — "Back to Discovery Report" + "Download Remediation Report"

The remediation progress page (Task 3.5) redirects here on completion. The discovery report page (report-header.tsx) also links here if remediation has been run.

### Task 3.7 — Update Discovery Report Header to Link to Remediation `[Small]`
**File:** [report-header.tsx](frontend/src/app/(app)/scan/[scanId]/report/_components/report-header.tsx)

- If remediation has been run (fix_attempt exists with status=success), show link: "View Remediation Results →"
- Change "FORGE Discovery Report" title to "FORGE Report" and add phase badges: "Discovery ✓" / "Remediation ✓" / "Validation ✓"

---

## WS4: Report Download (PDF/MD)

### Task 4.1 — Markdown Report Serializer `[Medium]`
**New file:** `frontend/src/lib/report/to-markdown.ts`

Pure function: `reportToMarkdown(report: DiscoveryReport, repoName?: string): string`

Structure:
```
# FORGE Report: {repoName}
**Generated:** {date} | **Duration:** {duration} | **Cost:** ${cost}

## Summary
- Total LOC / Files / Language / Findings count / Signal-to-noise ratio

## Findings
### Must Fix
#### {title}
- Severity | Category | Confidence | CWE | OWASP
- Description, Locations (file:line + snippet), Suggested Fix

### Should Fix / Consider / Informational (same structure)

## Remediation Plan (if present)
### Level N (items with priority, approach, files, acceptance criteria)

## Architecture Context
- Modules, Entry Points, Data Flows, Auth Boundaries
```

Groups findings by actionability tier. Includes all metadata fields. No external dependencies.

### Task 4.2 — PDF via Print Stylesheet `[Medium]` **DECISION: window.print() approach**
**New file:** `frontend/src/app/(app)/scan/[scanId]/report/print.css`

- `@media print` rules: hide nav, sidebar, buttons, non-content elements
- White background, black text for PDF readability
- Page breaks before major sections (findings groups, remediation plan, architecture)
- Force-expand all collapsed finding details
- Proper A4 sizing
- Add FORGE branding header with logo/text in print view

**Trigger:** "Save as PDF" button calls `window.print()` — zero dependencies, works everywhere.

### Task 4.3 — Download Button Group `[Small]`
**File:** [report-header.tsx](frontend/src/app/(app)/scan/[scanId]/report/_components/report-header.tsx)

Replace single "Download JSON" button with three inline buttons:
- **Download JSON** (existing, `FileJson` icon)
- **Download MD** (`FileText` icon) — calls `reportToMarkdown()` + Blob download
- **Save as PDF** (`Printer` icon) — calls `window.print()`

### Task 4.4 — Markdown Preview Tab `[Medium]`
**File:** [report/page.tsx](frontend/src/app/(app)/scan/[scanId]/report/page.tsx)

- Add `Tabs` component (already in shadcn/ui) at top of report page
- Tab 1: "Report" (default) — existing visual report
- Tab 2: "Markdown" — renders `reportToMarkdown()` output via `react-markdown` + `remark-gfm` + `rehype-highlight` (all already in package.json)
- Includes "Copy Markdown" button within the tab

---

## WS5: FORGE Learning Loop (AdalFlow Strategy)

**Goal:** Operationalize the AdalFlow/LLM-AutoDiff methodology from `forge-engine/doc/strategy/forge-differentiation.md`. Currently, telemetry captures finding→fix pairs in `training_data.jsonl` and findings are appended to `findings_history.jsonl`, but **nothing reads this data back** to improve agent prompts.

**What exists (data collection skeleton):**
- `ForgeTelemetry` (`forge/execution/telemetry.py`) — captures TrainingDataEntry per fix: finding_id, category, severity, tier, fix_outcome, retry_count, escalated, model_used
- `append_findings_history()` (`forge/patterns/extractor.py`) — appends findings to `.artifacts/findings_history.jsonl`
- `update_pattern_prevalence()` — increments `times_detected` on VulnerabilityPattern objects
- 3 curated patterns in `forge/patterns/library/curated/VP-{001,002,003}.yaml`
- Pattern schema (`forge/patterns/schema.py`) has `times_detected`, `times_confirmed`, `false_positive_rate` fields
- `proposed/` directory exists but is empty (scan-derived patterns would go here)

**What's NOT built:** backward LLM, textual gradients, prompt optimization, feedback loop, pattern extraction from history.

### Task 5.1 — Pattern Extraction Pipeline `[Large]`
**New file:** `forge-engine/forge/patterns/learner.py`
**Existing file to extend:** `forge-engine/forge/patterns/extractor.py`

Build the first feedback loop: findings_history.jsonl → proposed patterns.

1. **Cluster findings** from `findings_history.jsonl` by category + dedup_key similarity
2. **Identify recurring patterns** — findings that appear in 3+ scans with similar signatures
3. **Generate proposed VulnerabilityPattern YAML** — using an LLM to synthesize the pattern from clustered examples:
   - `pattern_id`: auto-generated VP-NNN
   - `source`: SCAN_DERIVED
   - `deterministic_signals`: extract regex/file patterns from recurring findings
   - `llm_guidance`: synthesize from the cluster's descriptions
   - `fix_template`: if most fixes in the cluster used similar approaches
4. **Save to `forge/patterns/library/proposed/`** with `times_detected` pre-populated
5. **Validation gate** — proposed patterns require manual review before promotion to curated

**Trigger:** Run after every N scans (configurable, default 10) or manually via CLI.

### Task 5.2 — Fix Outcome Feedback for Agents `[Medium]`
**Files to modify:**
- `forge-engine/forge/reasoners/remediation.py` (coder prompts)
- `forge-engine/forge/execution/telemetry.py` (feedback aggregation)

Build the feedback mechanism from training_data → agent prompts:

1. **Aggregate fix outcomes** from `training_data.jsonl`:
   - Per category: success rate, avg retry count, common escalation reasons
   - Per pattern: which fix approaches work vs fail
2. **Generate few-shot examples** from successful fixes:
   - Select top-performing fix examples per category (lowest retry count, no escalation)
   - Format as `{"finding": ..., "fix": ..., "outcome": "success"}` examples
3. **Inject into coder prompts** — Add a `LESSONS_LEARNED` section to coder system prompts with:
   - "For {category} findings, prefer {approach} (success rate: X%)"
   - "Avoid {anti-pattern} — leads to escalation Y% of the time"
   - Top 3 few-shot examples per category
4. **Persist as `forge/patterns/feedback/agent_guidance.json`** — regenerated periodically

This is the **lightweight version** of AdalFlow — no backward LLM yet, but data-driven prompt enrichment from accumulated scan data.

### Task 5.3 — Feedback Dashboard / CLI Report `[Medium]`
**New file:** `forge-engine/forge/learning/report.py`

CLI command or function that generates a learning loop status report:
- Total scans processed, total findings, total fixes attempted
- Fix success rate by category and tier
- Top patterns by prevalence (`times_detected`)
- Agent performance: avg retries per agent, escalation rate
- Proposed patterns awaiting review
- Cost trends over time

**Output:** JSON + formatted terminal output. This gives visibility into whether the learning loop is working.

### Task 5.4 — AdalFlow Textual Gradient Optimization `[Large]`
**New files:**
- `forge-engine/forge/learning/optimizer.py` — core optimization loop
- `forge-engine/forge/learning/graph.py` — computation graph representation
- `forge-engine/forge/learning/backward.py` — backward LLM for textual gradients
- `forge-engine/forge/learning/validation.py` — A/B testing framework

Full AdalFlow/LLM-AutoDiff implementation per `forge-engine/doc/strategy/forge-differentiation.md`:

**5.4a — Computation Graph (`graph.py`):**
- Model FORGE pipeline as a directed graph: nodes = agent invocations, edges = data flow
- Each node wraps: agent name, input schema, output schema, current prompt template
- Support subgraph extraction (e.g., just the remediation subgraph for coder optimization)
- `ForgeGraph.from_run(telemetry: ForgeTelemetry) -> ForgeGraph` — build graph from a completed run

**5.4b — Backward LLM (`backward.py`):**
- `generate_textual_gradient(node: GraphNode, expected: Any, actual: Any, model: str) -> TextualGradient`
- Uses a "critic" LLM (Haiku 4.5 for cost efficiency) to analyze what went wrong
- `TextualGradient` contains: `target_node`, `feedback`, `suggested_prompt_changes`, `confidence`
- Selective computation — only generates gradients for failed/suboptimal nodes
- Example output: "The Security Auditor missed SQL injection because the prompt's ORM bypass section lacks examples for SQLAlchemy. Add: 'Check for f-string queries in SQLAlchemy session.execute()'"

**5.4c — Parameter Updater (`optimizer.py`):**
- `optimize_agent_prompts(graph: ForgeGraph, gradients: list[TextualGradient]) -> PromptPatch`
- Takes textual gradients and generates concrete prompt modifications
- `PromptPatch`: diff-style changes to agent prompt templates (add/remove/modify sections)
- Safety constraints:
  - Max 20% of prompt changed per optimization cycle
  - Never removes core instructions (marked with `# INVARIANT` in templates)
  - Changes are PROPOSED, not applied — saved to `forge/learning/patches/` for review
- Optimization modes:
  - `CONSERVATIVE`: Only add few-shot examples and clarifying instructions
  - `MODERATE`: Rewrite instruction sections based on gradient feedback
  - `AGGRESSIVE`: Full prompt restructuring (requires manual approval)

**5.4d — A/B Validation Framework (`validation.py`):**
- `ab_test(baseline_prompts, patched_prompts, golden_tests: list[GoldenTest]) -> ABResult`
- Run both prompt versions against golden test suite
- Measure: detection rate, fix success rate, retry count, escalation rate, cost
- Statistical significance check (at least 3 golden tests showing improvement)
- `ABResult`: per_metric_comparison, overall_verdict (PROMOTE / REJECT / INCONCLUSIVE)
- Only promote patches that beat baseline on ALL metrics (no regressions)

**5.4e — Golden Test Suite Extension:**
- The 4 golden tests from the tech spec serve as the validation set:
  1. Lovable SaaS (10K LOC) — missing auth, exposed keys, no error handling
  2. Bolt e-commerce (25K LOC) — SQL injection, missing rate limiting
  3. Cursor API (50K LOC) — god modules, circular deps, no tests
  4. Mixed framework (75K LOC) — Python + React inconsistencies
- Each golden test has: known findings (ground truth), known correct fixes, expected readiness scores
- Store in `forge-engine/tests/golden/` with `expected_findings.json` and `expected_fixes.json`

**5.4f — CLI Integration:**
- `forge optimize --mode conservative --golden-dir tests/golden/` — run one optimization cycle
- `forge optimize --validate-only` — run A/B test without applying patches
- `forge optimize --apply-patch patches/patch-001.json` — apply a validated prompt patch

**Dependencies:** Tasks 5.1-5.3 must be complete (need accumulated training data). Golden test suite must have ground truth annotations.

---

## WS6: Compliance & Trust Layer (NIST SSDF)

**Goal:** Map FORGE's output to NIST SP 800-218A (Secure Software Development for Generative AI) and produce hardening attestations. This is the enterprise buyer unlock — procurement teams need compliance evidence.

**Current state:** Completely unbuilt. No NIST references in either codebase. The `ProductionReadinessReport` has generic category scores but no compliance mapping.

### Task 6.1 — NIST SSDF Practice Mapping `[Medium]` **DECISION: Manually curated**
**New file:** `forge-engine/forge/compliance/nist_ssdf.py`
**New data file:** `forge-engine/forge/compliance/ssdf_mapping.yaml`

Manually curate the mapping by reviewing NIST SP 800-218A spec. Map FORGE agent activities to SSDF practices:

| SSDF Practice | FORGE Coverage |
|--------------|----------------|
| PO.1 (Define Security Requirements) | Agent 1 CodebaseMap + Agent 4 Architecture Reviewer |
| PS.1 (Protect Software) | Agent 2 Security Auditor findings |
| PW.1 (Design Software to Meet Security Requirements) | Agent 4 + Agent 5 Fix Strategist |
| PW.5 (Create Source Code) | Agents 7-8 Coders with Sonnet 4.6 |
| PW.6 (Configure Software) | Tier 1 deterministic fixes |
| PW.7 (Review Code) | Agent 10 Code Reviewer |
| PW.8 (Test) | Agent 9 Test Generator + Agent 11 Integration Validator |
| RV.1 (Identify and Confirm Vulnerabilities) | Agents 2-4 Discovery + Agent 6 Triage |
| RV.2 (Assess, Prioritize, and Remediate) | Agent 5 Fix Strategist + Remediation loop |
| RV.3 (Analyze Vulnerabilities to Identify Root Causes) | Agent 4 Architecture Reviewer + Escalation Agent |

**Implementation:**
1. Define YAML mapping of SSDF practice IDs → FORGE agent IDs + evidence types
2. After a FORGE run, generate a `ComplianceReport` that maps each SSDF practice to specific evidence from the run (finding IDs, fix IDs, test results)
3. Mark practices as COVERED / PARTIAL / NOT_APPLICABLE based on what the run actually did

### Task 6.2 — Attestation Document Generator `[Medium]`
**New file:** `forge-engine/forge/compliance/attestation.py`

Generate a formal hardening attestation document:

```
FORGE HARDENING ATTESTATION
Repository: {repo_url}
Date: {date}
Run ID: {forge_run_id}

SCOPE
- Lines of code analyzed: {loc_total}
- Files analyzed: {file_count}
- Agents invoked: {agent_invocations}

FINDINGS & REMEDIATION
- Total findings discovered: {total_findings}
- Findings remediated: {findings_fixed}
- Findings deferred as tech debt: {findings_deferred}
- Fix success rate: {success_rate}%

PRODUCTION READINESS
- Overall Score: {overall_score}/100
- Category Scores: {category_breakdown}

NIST SP 800-218A COVERAGE
- Practices covered: {covered_count}/{total_practices}
- Evidence: {per_practice_evidence}

VALIDATION
- Integration tests run: {tests_run}
- Tests passed: {tests_passed}
- Regressions detected: {regressions}

ATTESTATION
This codebase was analyzed and hardened by FORGE v{version}
using {agent_count} specialized AI agents across {phase_count} phases.
```

**Output:** JSON (machine-readable) + Markdown (human-readable) + integrated into Production Readiness Report.

### Task 6.3 — Surface Compliance in Frontend `[Medium]`
**Files to modify:**
- Remediation results page (Task 3.6)
- Report download templates (Task 4.1 markdown serializer)

1. Add **"NIST SSDF Coverage" section** to remediation results page — collapsible card showing mapped practices with COVERED/PARTIAL badges
2. Add **attestation download** button — generates the attestation doc as Markdown
3. Include **compliance summary** in the markdown/PDF report download

### Task 6.4 — SBOM Generation Foundation `[Small]` *(Future)*
**New file:** `forge-engine/forge/compliance/sbom.py`

Generate Software Bill of Materials in SPDX or CycloneDX format from Agent 1's CodebaseMap (tech stack + dependencies). This is a natural extension once the compliance module exists.

---

## WS1: Frontend Implementation Gaps (Polish)

### Task 1.1 — SSE Streaming for Scan Progress `[Large]`
**File:** [scan/[scanId]/page.tsx](frontend/src/app/(app)/scan/[scanId]/page.tsx)

Replace polling `useEffect` with SSE using existing [sse.ts](frontend/src/lib/api/sse.ts) utilities:
- `connectSSE(scanId, token, onEvent, onError)` already implemented
- Handle event types: `agent_start`, `agent_log`, `agent_complete`, `finding`, `scan_complete`, `scan_error`
- Backend SSE proxy already exists at [/api/status/[scanId]/route.ts](frontend/src/app/api/status/[scanId]/route.ts)
- Enhanced UI: active agent badges, real-time log lines, finding counter, phase progress
- Fallback to polling on SSE connection failure
- New state: `agents[]`, `logEntries[]`, `findingsCount`, `currentPhase`

### Task 1.2 — Dashboard Quota Indicator `[Small]`
**File:** [dashboard/page.tsx](frontend/src/app/(app)/dashboard/page.tsx)

- Fetch `/api/limits` endpoint (already exists, returns `{ tier, project_count, project_limit }`)
- Display card: "Scan Quota: X of Y used" with `Progress` bar from [progress.tsx](frontend/src/components/ui/progress.tsx)
- Position above scan list

### Task 1.3 — Pattern ID Badges on Findings `[Small]`
**File:** [findings-table.tsx](frontend/src/app/(app)/scan/[scanId]/report/_components/findings-table.tsx)

- `DiscoveryFinding` already has `pattern_id?: string` field
- Add monospace `Badge` showing pattern ID (e.g., "VP-001") in finding detail section
- Only renders when `pattern_id` is present

### Task 1.4 — Findings Filters `[Medium]`
**File:** [findings-table.tsx](frontend/src/app/(app)/scan/[scanId]/report/_components/findings-table.tsx)

- Filter bar above findings with toggle badges for:
  - Severity: critical / high / medium / low
  - Category: security / architecture / quality / reliability / performance
- State: `severityFilter: Set<Severity>`, `categoryFilter: Set<Category>`
- Clicking a badge toggles it in/out of the filter set
- Findings filtered before rendering into actionability groups

### Task 1.5 — Analysis Methodology Footer `[Small]`
**File:** [report/page.tsx](frontend/src/app/(app)/scan/[scanId]/report/page.tsx)

- New collapsible `AnalysisMethodology` component at bottom of report
- Shows: agent names/roles table, scan duration, cost, model info
- Static content referencing FORGE's 12-agent architecture

---

## Execution Order

### Sprint 1: Positioning + Foundation (WS2 + WS3 setup)
*Landing page rewrite + remediation type foundation*
1. Task 2.1 — Hero rewrite with visual upgrades
2. Task 2.2 — Features rewrite (3-phase pipeline)
3. Task 2.3 — Stats rewrite
4. Task 2.4 — Comparison section ("Why Not Just Another Scanner?")
5. Task 3.1 — Fix/Remediation types in frontend
6. Task 3.3 — Score gauge component
7. Task 3.2 — Backend scan-level fix endpoint

### Sprint 2: Remediation Pipeline UI (WS3)
*Surface the full FORGE pipeline in the frontend*
8. Task 3.4 — "Fix with FORGE" button on report header
9. Task 3.5 — Remediation progress page (`/scan/{id}/remediation`)
10. Task 3.6 — Remediation results page with full data (`/scan/{id}/remediation/results`)
11. Task 3.7 — Update discovery report header with phase badges + remediation link

### Sprint 3: Report Downloads (WS4)
*Close the "Downloadable Reports" credibility gap*
12. Task 4.1 — Markdown serializer
13. Task 4.2 — PDF print stylesheet
14. Task 4.3 — Download button group
15. Task 4.4 — Markdown preview tab

### Sprint 4: Learning Loop — Data Pipeline (WS5 Part 1)
*Close the gap from "data collection" to "data-driven improvement"*
16. Task 5.1 — Pattern extraction pipeline (findings_history → proposed patterns)
17. Task 5.2 — Fix outcome feedback for coder agents (training_data → prompt enrichment)
18. Task 5.3 — Feedback dashboard / CLI report (visibility into learning loop health)

### Sprint 5: Learning Loop — AdalFlow Optimization (WS5 Part 2)
*Full textual gradient backpropagation for agent prompt optimization*
19. Task 5.4a — Computation graph representation
20. Task 5.4b — Backward LLM for textual gradients
21. Task 5.4c — Parameter updater (prompt patch generation)
22. Task 5.4d — A/B validation framework
23. Task 5.4e — Golden test suite ground truth annotations
24. Task 5.4f — CLI integration (`forge optimize`)

### Sprint 6: Compliance & Trust Layer (WS6)
*Enterprise buyer unlock — NIST SSDF mapping + attestations*
25. Task 6.1 — NIST SSDF practice mapping (manually curated YAML + Python module)
26. Task 6.2 — Attestation document generator
27. Task 6.3 — Surface compliance in frontend (remediation results page + downloads)

### Sprint 7: Frontend Polish (WS1)
*Quality-of-life improvements*
28. Task 1.1 — SSE streaming for scan progress
29. Task 1.2 — Dashboard quota indicator
30. Task 1.3 — Pattern ID badges on findings
31. Task 1.4 — Findings filters (severity, category)
32. Task 1.5 — Analysis methodology footer

### Future (After initial implementation)
- Task 6.4 — SBOM generation (SPDX/CycloneDX)
- Fine-tuning pipeline for specialist models (Triage Classifier first)
- Enterprise pricing tier model override (all Sonnet 4.6)

---

## Agent Team Execution Strategy

The plan will be saved to `tasks/plan.md` and executed by an agent team with the following structure:

### Team: `vibe2prod-build`

| Agent | Role | Sprints | Working Directory |
|-------|------|---------|-------------------|
| **lead** (me) | Team lead — coordinates, reviews, handles cross-cutting concerns | All | Both repos |
| **frontend-ui** | Landing page rewrite + remediation UI + report downloads | 1, 2, 3, 7 | `vibe2prod/frontend/` |
| **forge-learning** | Pattern extraction, feedback loop, AdalFlow optimization | 4, 5 | `forge-engine/` |
| **forge-compliance** | NIST SSDF mapping, attestation generator | 6 | `forge-engine/` |
| **backend-api** | Scan-level fix endpoint, fix status API | 2 (Task 3.2 only) | `vibe2prod/backend/` |

### Parallel Execution Plan
- **Sprint 1**: `frontend-ui` handles all landing page tasks (2.1-2.4 + 3.1, 3.3)
- **Sprint 2**: `frontend-ui` (Tasks 3.4-3.7) + `backend-api` (Task 3.2) run in parallel
- **Sprint 3**: `frontend-ui` handles downloads (4.1-4.4)
- **Sprint 4-5**: `forge-learning` handles learning loop (5.1-5.4)
- **Sprint 6**: `forge-compliance` handles NIST mapping (6.1-6.3)
- **Sprint 7**: `frontend-ui` handles polish (1.1-1.5)

Agents working on different repos/directories can run in parallel where sprints don't depend on each other.

---

## Deferred / Decision Required

| Item | Status |
|------|--------|
| Clerk Waitlist component | Skip — direct sign-up flow is better for current stage |
| Per-category score gauges | Covered by WS3 Task 3.6 — `category_scores[]` from ProductionReadinessReport |
| Onboarding as separate page | Skip — modal approach works fine |
| Full AdalFlow backward LLM | Included in Sprint 5 (Tasks 5.4a-5.4f) per user decision |
| SBOM generation | Deferred — natural extension after compliance module exists |
| Fine-tuning pipeline | Deferred — requires significant data accumulation first |
| Pitch deck | Out of scope for this plan — strategy docs feed into it but deck is a separate deliverable |

---

## Key Files Reference (Both Repos)

### Vibe2Prod Frontend
- Landing page: `frontend/src/app/page.tsx`
- Report page: `frontend/src/app/(app)/scan/[scanId]/report/page.tsx`
- Report components: `frontend/src/app/(app)/scan/[scanId]/report/_components/`
- Report header: `frontend/src/app/(app)/scan/[scanId]/report/_components/report-header.tsx`
- Findings table: `frontend/src/app/(app)/scan/[scanId]/report/_components/findings-table.tsx`
- Scan progress: `frontend/src/app/(app)/scan/[scanId]/page.tsx`
- SSE utils: `frontend/src/lib/api/sse.ts`
- API types: `frontend/src/lib/api/types.ts`
- Dashboard: `frontend/src/app/(app)/dashboard/page.tsx`

### Vibe2Prod Backend
- Fix route: `backend/api/routes/fix.py`
- Forge bridge: `backend/services/forge_bridge.py`
- Status SSE: `backend/api/routes/status.py`
- Config: `backend/config.py`

### FORGE Engine
- Telemetry: `forge/execution/telemetry.py`
- Control loops: `forge/execution/forge_executor.py`
- Remediation agents: `forge/reasoners/remediation.py`
- Validation agents: `forge/reasoners/validation.py`
- Pipeline: `forge/standalone.py`, `forge/app.py`, `forge/phases.py`
- Pattern schema: `forge/patterns/schema.py`
- Pattern extractor: `forge/patterns/extractor.py`
- Pattern library: `forge/patterns/library/{curated,proposed}/`
- Strategy docs: `doc/strategy/forge-differentiation.md`

### Strategy Docs
- Competitive moat: `vibe2prod/doc/strategy/competitive-moat.md`
- FORGE differentiation: `forge-engine/doc/strategy/forge-differentiation.md`
- Technical spec: `forge-engine/FORGE_Technical_Specification.docx`

---

## Verification Plan

### After Sprint 1 (Landing Page)
- Visual review of landing page at localhost:3000
- Check responsive design on mobile viewport
- Verify all links work (Sign In, Get Started, Dashboard)
- Verify animations (fade-in, gradient) work smoothly
- Screenshot before/after for comparison

### After Sprint 2 (Remediation UI)
- Trigger a scan → wait for completion → click "Fix with FORGE"
- Verify `POST /api/fix-scan/{scan_id}` creates fix_attempt and returns 200
- Verify remediation progress page renders and polls correctly
- Verify remediation results page displays:
  - Production Readiness Score gauge (0-100)
  - Category score cards (6 categories)
  - Before/after findings breakdown
  - Validation results (tests run/passed/failed)
  - Investor summary narrative
  - Debt items list
  - PR link (if present)
- Test error states (fix fails, scan not found, already in progress)
- Verify phase badges on discovery report header

### After Sprint 3 (Downloads)
- Download JSON → verify file contents
- Download MD → verify formatted markdown with all sections (findings grouped by actionability, remediation plan, architecture, compliance if available)
- Save as PDF → verify print dialog renders clean report with proper page breaks
- Test Markdown tab → verify rendered markdown matches data
- Verify download from dashboard also works

### After Sprint 4 (Learning Loop — Data Pipeline)
- Run pattern extraction on existing findings_history.jsonl:
  - Verify proposed patterns generated in `forge/patterns/library/proposed/`
  - Verify pattern YAML schema matches VulnerabilityPattern
- Run feedback aggregation on training_data.jsonl:
  - Verify agent_guidance.json generated with per-category success rates
  - Verify few-shot examples selected
- Run feedback CLI report → verify stats output
- Run a new scan → verify coder prompts include LESSONS_LEARNED section

### After Sprint 5 (Learning Loop — AdalFlow)
- Build computation graph from a completed run's telemetry:
  - Verify graph nodes match agent invocations
  - Verify edges match data flow between agents
- Run backward LLM on a known failure case:
  - Verify TextualGradient generated with concrete prompt suggestions
  - Verify selective computation (only failed nodes get gradients)
- Generate a prompt patch:
  - Verify PromptPatch respects safety constraints (max 20% change, INVARIANT preserved)
  - Verify patch saved to `forge/learning/patches/`
- Run A/B validation against golden tests:
  - Verify both baseline and patched versions run
  - Verify ABResult with per-metric comparison
  - Verify PROMOTE/REJECT verdict
- Test CLI: `forge optimize --mode conservative --golden-dir tests/golden/`

### After Sprint 6 (Compliance)
- Run FORGE scan + remediation → verify ComplianceReport generated
- Verify SSDF practices mapped to agent evidence
- Verify attestation document generated (Markdown + JSON)
- Verify compliance section visible on remediation results page
- Verify attestation download button works
- Verify compliance summary included in markdown/PDF report

### After Sprint 7 (Polish)
- SSE: Start scan → verify real-time events stream (agent badges, log lines, finding counter)
- Quota: Check dashboard shows "X of Y" indicator
- Filters: Toggle severity/category badges → verify findings list updates
- Pattern badges: Verify VP-XXX badges show on findings that have pattern_id
- Methodology footer: Verify agent table + scan metadata visible
