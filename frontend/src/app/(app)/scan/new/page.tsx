"use client";

export const dynamic = "force-dynamic";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

import { apiFetch, ApiError } from "@/lib/api/client";
import type {
  PrimerResult,
  AuditResponse,
  ProjectOrigin,
  SensitiveDataType,
  ProjectIntake,
} from "@/lib/api/types";

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
  // Step 3: Submit
  // ---------------------------------------------------------------------------

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      const token = await getToken();

      const body: {
        repo_url: string;
        branch?: string;
        project_intake?: ProjectIntake;
        primer?: PrimerResult;
      } = {
        repo_url: repoUrl.trim(),
      };

      // Only send intake if user filled any fields
      if (productSummary || targetUsers || deploymentTarget || scaleExpectation) {
        body.project_intake = {
          project_origin: projectOrigin,
          product_summary: productSummary,
          target_users: targetUsers,
          sensitive_data: sensitiveData.length > 0 ? sensitiveData : ["not_sure"],
          must_not_break_flows: mustNotBreakFlows,
          deployment_target: deploymentTarget,
          scale_expectation: scaleExpectation,
        };
      }

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
          const detail = typeof err.detail === 'object' ? err.detail : { message: err.detail }
          const code = (detail as { code?: string })?.code

          if (code === "waitlist_required") {
            router.replace('/waitlist')
            return
          }

          if (code === "onboarding_required") {
            router.replace('/onboarding')
            return
          }

          setSubmitError(
            (detail as { message?: string })?.message || err.message || "Access denied"
          );
        } else if (err.status === 429) {
          setSubmitError("Rate limited. Please wait a moment and try again.");
        } else {
          setSubmitError(err.message || "Scan failed to start");
        }
      } else {
        setSubmitError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Step navigation
  // ---------------------------------------------------------------------------

  const goToStep = (target: number) => {
    if (target === 2 && !repoUrl.trim()) return;
    setStep(target);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-100 mb-1 font-[family-name:var(--font-heading)]">New Scan</h1>
        <p className="text-[#8692A8] text-sm">
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
          onSkip={() => goToStep(3)}
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
          submitting={submitting}
          submitError={submitError}
          onEditRepo={() => setStep(1)}
          onEditContext={() => setStep(2)}
          onBack={() => setStep(2)}
          onSubmit={handleSubmit}
        />
      )}

    </div>
  );
}
