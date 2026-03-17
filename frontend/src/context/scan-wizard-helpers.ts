/**
 * Pure helper functions extracted from ScanWizardContext to reduce context file size.
 * These functions contain no React state — they are pure logic helpers.
 */

import { apiFetch, ApiError } from "@/lib/api/client";
import type {
  PrimerResult,
  AuditResponse,
  ProjectOrigin,
  SensitiveDataType,
  ProjectIntake,
  ProjectSummary,
} from "@/lib/api/types";

// ---------------------------------------------------------------------------
// GitHub URL validation
// ---------------------------------------------------------------------------

const GITHUB_URL_REGEX = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

export function validateGitHubUrl(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) return "Please enter a GitHub repository URL";
  if (!trimmed.startsWith("https://github.com/")) {
    return "URL must start with https://github.com/";
  }
  if (!GITHUB_URL_REGEX.test(trimmed)) {
    return "Must be a valid GitHub URL (e.g. https://github.com/owner/repo)";
  }
  return null;
}

// ---------------------------------------------------------------------------
// Step 2 validation
// ---------------------------------------------------------------------------

export function checkStep2Valid(fields: {
  productSummary: string;
  targetUsers: string;
  deploymentTarget: string;
  scaleExpectation: string;
}): boolean {
  return (
    fields.productSummary.length >= 3 &&
    fields.productSummary.length <= 800 &&
    fields.targetUsers.length >= 2 &&
    fields.targetUsers.length <= 400 &&
    fields.deploymentTarget.length >= 2 &&
    fields.deploymentTarget.length <= 200 &&
    fields.scaleExpectation.length >= 2 &&
    fields.scaleExpectation.length <= 200
  );
}

// ---------------------------------------------------------------------------
// Pre-fill from previous project
// ---------------------------------------------------------------------------

export interface PrefillResult {
  projectOrigin: ProjectOrigin;
  productSummary: string;
  targetUsers: string;
  sensitiveData: SensitiveDataType[];
  mustNotBreakFlows: string[];
  deploymentTarget: string;
  scaleExpectation: string;
}

/**
 * Fetch intake data for a previously scanned repo to pre-fill the wizard.
 * Returns null if no matching project or intake is found.
 */
export async function fetchPrefillData(
  repoParam: string,
  getToken: () => Promise<string | null>,
): Promise<PrefillResult | null> {
  const token = (await getToken()) ?? undefined;

  const resp = await apiFetch<{ items: ProjectSummary[] }>("/api/user/projects", {
    token,
  });
  const match = resp.items.find((p) => p.repo_url === repoParam);
  if (!match) return null;

  const intakeResp = await apiFetch<{ project_intake: ProjectIntake | null }>(
    `/api/user/projects/${match.id}/intake`,
    { token },
  );

  const intake = intakeResp.project_intake;
  if (!intake) return null;

  return {
    projectOrigin: intake.project_origin,
    productSummary: intake.product_summary || "",
    targetUsers: intake.target_users || "",
    sensitiveData: intake.sensitive_data || [],
    mustNotBreakFlows: intake.must_not_break_flows || [],
    deploymentTarget: intake.deployment_target || "",
    scaleExpectation: intake.scale_expectation || "",
  };
}

// ---------------------------------------------------------------------------
// Build audit request body
// ---------------------------------------------------------------------------

export interface AuditRequestBody {
  repo_url: string;
  branch?: string;
  project_intake?: ProjectIntake;
  primer?: PrimerResult;
}

export function buildAuditBody(fields: {
  repoUrl: string;
  branch: string;
  primerResult: PrimerResult | null;
  projectOrigin: ProjectOrigin;
  productSummary: string;
  targetUsers: string;
  sensitiveData: SensitiveDataType[];
  mustNotBreakFlows: string[];
  deploymentTarget: string;
  scaleExpectation: string;
}): AuditRequestBody {
  const body: AuditRequestBody = {
    repo_url: fields.repoUrl.trim(),
  };

  if (
    fields.productSummary ||
    fields.targetUsers ||
    fields.deploymentTarget ||
    fields.scaleExpectation
  ) {
    body.project_intake = {
      project_origin: fields.projectOrigin,
      product_summary: fields.productSummary,
      target_users: fields.targetUsers,
      sensitive_data:
        fields.sensitiveData.length > 0 ? fields.sensitiveData : ["not_sure"],
      must_not_break_flows: fields.mustNotBreakFlows,
      deployment_target: fields.deploymentTarget,
      scale_expectation: fields.scaleExpectation,
    };
  }

  if (fields.branch) body.branch = fields.branch;
  if (fields.primerResult) body.primer = fields.primerResult;

  return body;
}

/**
 * Submit the audit request and return the scan ID.
 * Throws ApiError on failure.
 */
export async function submitAudit(
  body: AuditRequestBody,
  getToken: () => Promise<string | null>,
): Promise<string> {
  const token = await getToken();
  const result = await apiFetch<AuditResponse>("/api/audit", {
    method: "POST",
    body: JSON.stringify(body),
    token: token ?? undefined,
  });
  return result.scan_id;
}

/**
 * Classify an ApiError into a user-facing error message or a redirect path.
 */
export function classifySubmitError(
  err: unknown,
): { redirect: string } | { message: string } {
  if (err instanceof ApiError) {
    if (err.status === 403) {
      const detail =
        typeof err.detail === "object" ? err.detail : { message: err.detail };
      const code = (detail as { code?: string })?.code;

      if (code === "waitlist_required") return { redirect: "/waitlist" };
      if (code === "onboarding_required") return { redirect: "/onboarding" };

      return {
        message:
          (detail as { message?: string })?.message ||
          err.message ||
          "Access denied",
      };
    }
    if (err.status === 429) {
      return { message: "Rate limited. Please wait a moment and try again." };
    }
    return { message: err.message || "Scan failed to start" };
  }
  return { message: "An unexpected error occurred. Please try again." };
}
