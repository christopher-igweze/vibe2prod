"use client";

export const dynamic = "force-dynamic";

import { useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

import { apiFetch, ApiError } from "@/lib/api/client";
import type {
  PrimerResult,
  AuditResponse,
  QuotaLimits,
  ProjectOrigin,
  SensitiveDataType,
  ProjectIntake,
} from "@/lib/api/types";

import { OnboardingModal } from "@/components/scan/onboarding-modal";
import { StepIndicator } from "@/components/scan/step-indicator";
import { RepoStep } from "@/components/scan/repo-step";
import { IntakeStep } from "@/components/scan/intake-step";
import { ReviewStep } from "@/components/scan/review-step";

// ---------------------------------------------------------------------------
// Main Page (thin orchestrator)
// ---------------------------------------------------------------------------

export default function NewScanPage() {
  const { getToken } = useAuth();
  const router = useRouter();

  // Wizard state
  const [step, setStep] = useState(1);

  // Step 1: Repo URL + Branch + Primer
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [primerResult, setPrimerResult] = useState<PrimerResult | null>(null);
  const [suggestedFlows, setSuggestedFlows] = useState<string[]>([]);
  const [repoSelectorManual, setRepoSelectorManual] = useState(false);

  // Step 2: Project Intake
  const [projectOrigin, setProjectOrigin] = useState<ProjectOrigin>("inspired");
  const [productSummary, setProductSummary] = useState("");
  const [targetUsers, setTargetUsers] = useState("");
  const [sensitiveData, setSensitiveData] = useState<SensitiveDataType[]>([]);
  const [mustNotBreakFlows, setMustNotBreakFlows] = useState<string[]>([]);
  const [deploymentTarget, setDeploymentTarget] = useState("");
  const [scaleExpectation, setScaleExpectation] = useState("");

  // Step 3: Submit
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [quotaChecking, setQuotaChecking] = useState(false);
  const [quota, setQuota] = useState<QuotaLimits | null>(null);
  const [quotaError, setQuotaError] = useState<string | null>(null);

  // Onboarding modal
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [pendingRetry, setPendingRetry] = useState(false);

  // ---------------------------------------------------------------------------
  // Step 2 validation
  // ---------------------------------------------------------------------------

  const isStep2Valid = (): boolean => {
    return (
      productSummary.length >= 3 &&
      productSummary.length <= 800 &&
      targetUsers.length >= 2 &&
      targetUsers.length <= 400 &&
      deploymentTarget.length >= 2 &&
      deploymentTarget.length <= 200 &&
      scaleExpectation.length >= 2 &&
      scaleExpectation.length <= 200
    );
  };

  // ---------------------------------------------------------------------------
  // Step 3: Check quota + submit
  // ---------------------------------------------------------------------------

  const checkQuota = useCallback(async () => {
    setQuotaChecking(true);
    setQuotaError(null);
    try {
      const token = await getToken();
      const limits = await apiFetch<QuotaLimits>("/api/limits", {
        token: token ?? undefined,
      });
      setQuota(limits);
      if (limits.reports_remaining <= 0) {
        setQuotaError(
          `You've used all ${limits.reports_limit} free scans this month. Resets next month.`
        );
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setQuotaError("Unable to check quota. Please ensure you are onboarded.");
      } else {
        setQuotaError("Could not check scan limits. Try submitting anyway.");
      }
    } finally {
      setQuotaChecking(false);
    }
  }, [getToken]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      const token = await getToken();

      const intake: ProjectIntake = {
        project_origin: projectOrigin,
        product_summary: productSummary,
        target_users: targetUsers,
        sensitive_data: sensitiveData.length > 0 ? sensitiveData : ["not_sure"],
        must_not_break_flows: mustNotBreakFlows,
        deployment_target: deploymentTarget,
        scale_expectation: scaleExpectation,
      };

      const body: {
        repo_url: string;
        branch?: string;
        project_intake: ProjectIntake;
        primer?: PrimerResult;
      } = {
        repo_url: repoUrl.trim(),
        project_intake: intake,
      };

      if (branch) {
        body.branch = branch;
      }

      if (primerResult) {
        body.primer = primerResult;
      }

      const result = await apiFetch<AuditResponse>("/api/audit", {
        method: "POST",
        body: JSON.stringify(body),
        token: token ?? undefined,
      });

      router.push(`/scan/${result.scan_id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        // Handle structured 403 errors
        if (err.status === 403) {
          let detail: { code?: string; message?: string };
          try {
            detail = typeof err.detail === "string" ? JSON.parse(err.detail) : err.detail;
          } catch {
            detail = { message: err.detail };
          }

          const code = (detail as { code?: string })?.code;

          if (code === "onboarding_required") {
            setShowOnboarding(true);
            setPendingRetry(true);
            setSubmitting(false);
            return;
          }

          if (code === "limit_reports_exceeded") {
            setSubmitError("You have used all your free scans this month. Quota resets next month.");
          } else if (code === "limit_projects_exceeded") {
            setSubmitError("You have reached the free tier project limit.");
          } else if (code === "limit_loc_exceeded") {
            setSubmitError("This repository exceeds the free tier LOC limit (50,000 lines).");
          } else {
            setSubmitError(
              (detail as { message?: string })?.message || err.detail || "Access denied"
            );
          }
        } else if (err.status === 429) {
          setSubmitError("Rate limited. Please wait a moment and try again.");
        } else {
          setSubmitError(err.detail || "Scan failed to start");
        }
      } else {
        setSubmitError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    if (pendingRetry) {
      setPendingRetry(false);
      handleSubmit();
    }
  };

  // ---------------------------------------------------------------------------
  // Step navigation
  // ---------------------------------------------------------------------------

  const goToStep = (target: number) => {
    if (target === 2 && !repoUrl.trim()) return;
    if (target === 3) {
      if (!isStep2Valid()) return;
      checkQuota();
    }
    setStep(target);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-100 mb-1">New Scan</h1>
        <p className="text-neutral-400 text-sm">
          Audit your codebase for security, reliability, and scalability issues.
        </p>
      </div>

      <StepIndicator currentStep={step} />

      {/* Step 1: Repository URL + Primer */}
      {step === 1 && (
        <RepoStep
          getToken={getToken}
          repoUrl={repoUrl}
          setRepoUrl={setRepoUrl}
          branch={branch}
          setBranch={setBranch}
          primerResult={primerResult}
          setPrimerResult={setPrimerResult}
          setSuggestedFlows={setSuggestedFlows}
          repoSelectorManual={repoSelectorManual}
          setRepoSelectorManual={setRepoSelectorManual}
          onContinue={() => goToStep(2)}
        />
      )}

      {/* Step 2: Project Intake Form */}
      {step === 2 && (
        <IntakeStep
          projectOrigin={projectOrigin}
          setProjectOrigin={setProjectOrigin}
          productSummary={productSummary}
          setProductSummary={setProductSummary}
          targetUsers={targetUsers}
          setTargetUsers={setTargetUsers}
          sensitiveData={sensitiveData}
          setSensitiveData={setSensitiveData}
          mustNotBreakFlows={mustNotBreakFlows}
          setMustNotBreakFlows={setMustNotBreakFlows}
          deploymentTarget={deploymentTarget}
          setDeploymentTarget={setDeploymentTarget}
          scaleExpectation={scaleExpectation}
          setScaleExpectation={setScaleExpectation}
          suggestedFlows={suggestedFlows}
          onBack={() => setStep(1)}
          onContinue={() => goToStep(3)}
          isValid={isStep2Valid()}
        />
      )}

      {/* Step 3: Review & Submit */}
      {step === 3 && (
        <ReviewStep
          repoUrl={repoUrl}
          branch={branch}
          primerResult={primerResult}
          projectOrigin={projectOrigin}
          productSummary={productSummary}
          targetUsers={targetUsers}
          sensitiveData={sensitiveData}
          mustNotBreakFlows={mustNotBreakFlows}
          deploymentTarget={deploymentTarget}
          scaleExpectation={scaleExpectation}
          quotaChecking={quotaChecking}
          quota={quota}
          quotaError={quotaError}
          submitting={submitting}
          submitError={submitError}
          onEditRepo={() => setStep(1)}
          onEditContext={() => setStep(2)}
          onBack={() => setStep(2)}
          onSubmit={handleSubmit}
        />
      )}

      {/* Onboarding Modal */}
      <OnboardingModal
        open={showOnboarding}
        onClose={() => {
          setShowOnboarding(false);
          setPendingRetry(false);
        }}
        onComplete={handleOnboardingComplete}
        getToken={getToken}
      />
    </div>
  );
}
