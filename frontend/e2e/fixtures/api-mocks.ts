import type { Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// Mock response data — FORGE discovery flow
// ---------------------------------------------------------------------------

export const MOCK_PRIMER_RESPONSE = {
  project_id: "proj_test_123",
  cached: false,
  primer: {
    primer_json: {
      repo_full_name: "sindresorhus/is",
      default_branch: "main",
      file_tree_sample: [
        "source/index.ts",
        "source/types.ts",
        "test/test.ts",
        "package.json",
        "readme.md",
      ],
    },
    summary: "Type check values with TypeScript-first assertions.",
    repo_sha: "abc123def456",
    confidence: 90,
    failure_reason: null,
  },
  suggested_flows: ["Type checking", "Assertion validation"],
};

export const MOCK_QUOTA = {
  tier: "forge",
  project_count: 0,
  project_limit: 3,
};

export const MOCK_AUDIT_RESPONSE = {
  scan_id: "scan_test_abc123",
  status: "pending",
  tier: "forge",
  quota_remaining: null,
  message: "Audit queued.",
};

export const MOCK_SCAN_SCANNING = {
  id: "scan_test_abc123",
  status: "scanning" as const,
  repo_url: "https://github.com/sindresorhus/is",
  repo_name: "sindresorhus/is",
  report_data: null,
};

export const MOCK_SCAN_COMPLETED = {
  id: "scan_test_abc123",
  status: "completed" as const,
  repo_url: "https://github.com/sindresorhus/is",
  repo_name: "sindresorhus/is",
  report_data: {
    discovery_report: {
      run_id: "run_abc123",
      generated_at: new Date().toISOString(),
      phase: "discovery+triage",
      duration_seconds: 45,
      cost_usd: 0.12,
      loc_total: 1200,
      file_count: 15,
      primary_language: "TypeScript",
      total_findings: 3,
      severity_breakdown: { critical: 0, high: 1, medium: 1, low: 1 },
      category_breakdown: { security: 1, quality: 1, reliability: 1 },
      actionability_summary: null,
      findings: [
        {
          id: "f1",
          title: "Missing input validation",
          description: "User input is not validated before processing.",
          category: "security",
          severity: "high",
          audit_pass: false,
          locations: [{ file_path: "source/index.ts", line_start: 42, line_end: 50, snippet: "function check(input) { ... }" }],
          suggested_fix: "Add Zod schema validation at the entry point.",
          confidence: 85,
          cwe_id: "CWE-20",
          owasp_ref: "A03:2021",
          agent: "security_auditor",
          tier: 1,
          dedup_key: "sec-input-val",
        },
        {
          id: "f2",
          title: "No error boundary in component tree",
          description: "React components lack error boundaries, causing full-page crashes on render errors.",
          category: "reliability",
          severity: "medium",
          audit_pass: false,
          locations: [{ file_path: "source/types.ts", line_start: 10, line_end: 15, snippet: "export function TypeGuard() { ... }" }],
          suggested_fix: "Wrap top-level routes with an ErrorBoundary component.",
          confidence: 72,
          cwe_id: "",
          owasp_ref: "",
          agent: "quality_auditor",
          tier: 2,
          dedup_key: "rel-error-boundary",
        },
        {
          id: "f3",
          title: "Unused dependency in package.json",
          description: "The lodash package is listed as a dependency but never imported.",
          category: "quality",
          severity: "low",
          audit_pass: true,
          locations: [{ file_path: "package.json", line_start: 8, line_end: 8, snippet: '"lodash": "^4.17.21"' }],
          suggested_fix: "Remove lodash from dependencies.",
          confidence: 95,
          cwe_id: "",
          owasp_ref: "",
          agent: "quality_auditor",
          tier: 3,
          dedup_key: "qual-unused-dep",
        },
      ],
      remediation_plan: {
        items: [
          {
            finding_id: "f1",
            title: "Add input validation",
            tier: 1,
            priority: 1,
            estimated_files: 2,
            files_to_modify: ["source/index.ts", "source/validators.ts"],
            depends_on: [],
            acceptance_criteria: [
              "All public functions validate inputs with Zod",
              "Invalid inputs throw descriptive errors",
            ],
            approach: "Add Zod schemas for each exported function's parameters.",
            group: "security",
          },
          {
            finding_id: "f2",
            title: "Add error boundaries",
            tier: 2,
            priority: 2,
            estimated_files: 1,
            files_to_modify: ["source/types.ts"],
            depends_on: ["f1"],
            acceptance_criteria: ["Error boundary catches render errors without page crash"],
            approach: "Create ErrorBoundary wrapper component.",
            group: "reliability",
          },
        ],
        dependencies: [
          {
            finding_id: "f2",
            depends_on_finding_id: "f1",
            reason: "Validation should exist before error boundaries wrap components",
          },
        ],
        execution_levels: [["f1"], ["f2"]],
      },
      codebase_map: null,
      dependency_graph: null,
    },
  },
};

/** Scan with no report data (report_data missing). */
export const MOCK_SCAN_NO_REPORT = {
  id: "scan_no_report_456",
  status: "completed" as const,
  repo_url: "https://github.com/sindresorhus/is",
  repo_name: "sindresorhus/is",
  report_data: {},
};

/** Scan still in scanning state (report page should show "waiting"). */
export const MOCK_SCAN_STILL_SCANNING = {
  id: "scan_still_scanning_789",
  status: "scanning" as const,
  repo_url: "https://github.com/sindresorhus/is",
  repo_name: "sindresorhus/is",
};

// ---------------------------------------------------------------------------
// Mock setup helpers
// ---------------------------------------------------------------------------

/**
 * Sets up all API route mocks for the happy-path scan wizard flow.
 * The scan poll endpoint transitions from "scanning" to "completed" after 2 polls.
 */
export async function setupHappyPathMocks(page: Page) {
  // GitHub OAuth status: not connected (forces manual URL entry)
  await page.route("**/api/github/status", (route) =>
    route.fulfill({ json: { connected: false } }),
  );

  // Primer analysis
  await page.route("**/api/primer", (route) =>
    route.fulfill({ json: MOCK_PRIMER_RESPONSE }),
  );

  // Quota check
  await page.route("**/api/limits", (route) =>
    route.fulfill({ json: MOCK_QUOTA }),
  );

  // Audit submission
  await page.route("**/api/audit", (route) =>
    route.fulfill({ json: MOCK_AUDIT_RESPONSE }),
  );

  // Scan polling — transitions from scanning to completed
  let pollCount = 0;
  await page.route("**/api/user/scans/scan_test_abc123", (route) => {
    pollCount++;
    if (pollCount <= 2) {
      return route.fulfill({ json: MOCK_SCAN_SCANNING });
    }
    return route.fulfill({ json: MOCK_SCAN_COMPLETED });
  });

  // Dashboard scans list (empty by default)
  await page.route("**/api/user/scans", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/user/scans") {
      return route.fulfill({ json: [] });
    }
    return route.continue();
  });
}
