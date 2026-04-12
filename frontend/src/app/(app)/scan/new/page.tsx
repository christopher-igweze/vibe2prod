"use client";

export const dynamic = "force-dynamic";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter, useSearchParams } from "next/navigation";

import { StepIndicator } from "@/components/scan/step-indicator";
import { RepoStep } from "@/components/scan/repo-step";
import { IntakeStep } from "@/components/scan/intake-step";
import { ReviewStep } from "@/components/scan/review-step";
import {
  ScanWizardProvider,
  useScanWizard,
} from "@/context/scan-wizard-context";

// ---------------------------------------------------------------------------
// Inner component (uses useSearchParams, needs Suspense boundary)
// ---------------------------------------------------------------------------

function NewScanInner() {
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const wizard = useScanWizard();

  // Collapsed intake editor toggle for rescan review step
  const [showIntakeEditor, setShowIntakeEditor] = useState(false);

  // ---------------------------------------------------------------------------
  // Pre-fill from previous scan (when ?repo_url= is present)
  // ---------------------------------------------------------------------------

  const prefill = useCallback(async () => {
    const repoParam = searchParams.get("repo_url");
    if (!repoParam) return;
    await wizard.prefillFromProject(repoParam, getToken);
  }, [searchParams, getToken, wizard.prefillFromProject]);

  useEffect(() => {
    prefill();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        {wizard.preFilled && (
          <p className="text-xs text-forge-emerald mt-1">
            Pre-filled from previous scan
          </p>
        )}
      </div>

      <StepIndicator currentStep={wizard.step} skipStep2={wizard.hasExistingContext} />

      {/* Step 1: Repository URL + Primer */}
      {wizard.step === 1 && (
        <div data-tour="repo-input">
        <RepoStep
          getToken={getToken}
          repoUrl={wizard.repoUrl}
          setRepoUrl={wizard.setRepoUrl}
          branch={wizard.branch}
          setBranch={wizard.setBranch}
          primerResult={wizard.primerResult}
          setPrimerResult={wizard.setPrimerResult}
          setSuggestedFlows={wizard.setSuggestedFlows}
          repoSelectorManual={wizard.repoSelectorManual}
          setRepoSelectorManual={wizard.setRepoSelectorManual}
          onContinue={() => wizard.goToStep(wizard.hasExistingContext ? 3 : 2)}
        />
        </div>
      )}

      {/* Step 2: Project Intake Form */}
      {wizard.step === 2 && (
        <div data-tour="intake-form">
        <IntakeStep
          projectOrigin={wizard.projectOrigin}
          setProjectOrigin={wizard.setProjectOrigin}
          productSummary={wizard.productSummary}
          setProductSummary={wizard.setProductSummary}
          targetUsers={wizard.targetUsers}
          setTargetUsers={wizard.setTargetUsers}
          sensitiveData={wizard.sensitiveData}
          setSensitiveData={wizard.setSensitiveData}
          mustNotBreakFlows={wizard.mustNotBreakFlows}
          setMustNotBreakFlows={wizard.setMustNotBreakFlows}
          deploymentTarget={wizard.deploymentTarget}
          setDeploymentTarget={wizard.setDeploymentTarget}
          scaleExpectation={wizard.scaleExpectation}
          setScaleExpectation={wizard.setScaleExpectation}
          suggestedFlows={wizard.suggestedFlows}
          onBack={() => wizard.setStep(1)}
          onContinue={() => wizard.goToStep(3)}
          onSkip={() => wizard.goToStep(3)}
          isValid={wizard.isStep2Valid()}
        />
        </div>
      )}

      {/* Step 3: Review & Submit */}
      {wizard.step === 3 && (
        <div data-tour="submit-review">
        <ReviewStep
          repoUrl={wizard.repoUrl}
          branch={wizard.branch}
          primerResult={wizard.primerResult}
          projectOrigin={wizard.projectOrigin}
          productSummary={wizard.productSummary}
          targetUsers={wizard.targetUsers}
          sensitiveData={wizard.sensitiveData}
          mustNotBreakFlows={wizard.mustNotBreakFlows}
          deploymentTarget={wizard.deploymentTarget}
          scaleExpectation={wizard.scaleExpectation}
          submitting={wizard.submitting}
          submitError={wizard.submitError}
          onEditRepo={() => wizard.setStep(1)}
          onEditContext={() => wizard.setStep(2)}
          onBack={() => wizard.setStep(wizard.hasExistingContext ? 1 : 2)}
          onSubmit={() =>
            wizard.handleSubmit(
              getToken,
              (scanId) => router.push(`/scan/${scanId}`),
              (path) => router.replace(path),
            )
          }
          hasExistingContext={wizard.hasExistingContext}
          showIntakeEditor={showIntakeEditor}
          onToggleIntakeEditor={() => setShowIntakeEditor((v) => !v)}
          setProjectOrigin={wizard.setProjectOrigin}
          setProductSummary={wizard.setProductSummary}
          setTargetUsers={wizard.setTargetUsers}
          setSensitiveData={wizard.setSensitiveData}
          setMustNotBreakFlows={wizard.setMustNotBreakFlows}
          setDeploymentTarget={wizard.setDeploymentTarget}
          setScaleExpectation={wizard.setScaleExpectation}
          suggestedFlows={wizard.suggestedFlows}
        />
        </div>
      )}

    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page (Suspense wrapper for useSearchParams)
// ---------------------------------------------------------------------------

export default function NewScanPage() {
  return (
    <ScanWizardProvider>
      <Suspense fallback={
        <div className="max-w-2xl mx-auto">
          <div className="h-8 w-48 bg-forge-nav rounded animate-pulse mb-6" />
          <div className="h-64 bg-forge-nav rounded-lg animate-pulse" />
        </div>
      }>
        <NewScanInner />
      </Suspense>
    </ScanWizardProvider>
  );
}
