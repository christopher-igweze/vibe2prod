"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

import type {
  PrimerResult,
  ProjectOrigin,
  SensitiveDataType,
} from "@/lib/api/types";

import {
  validateGitHubUrl,
  checkStep2Valid,
  fetchPrefillData,
  buildAuditBody,
  submitAudit,
  classifySubmitError,
} from "./scan-wizard-helpers";

// Re-export for consumers that import from this module
export { validateGitHubUrl } from "./scan-wizard-helpers";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ScanWizardState {
  // Navigation
  step: number;
  setStep: (step: number) => void;
  goToStep: (target: number) => void;

  // Rescan detection
  hasExistingContext: boolean;

  // Step 1: Repository
  repoUrl: string;
  setRepoUrl: (url: string) => void;
  branch: string;
  setBranch: (branch: string) => void;
  primerResult: PrimerResult | null;
  setPrimerResult: (result: PrimerResult | null) => void;
  suggestedFlows: string[];
  setSuggestedFlows: (flows: string[]) => void;
  repoSelectorManual: boolean;
  setRepoSelectorManual: (manual: boolean) => void;
  repoUrlError: string | null;
  setRepoUrlError: (error: string | null) => void;

  // Step 2: Project Intake
  projectOrigin: ProjectOrigin;
  setProjectOrigin: (origin: ProjectOrigin) => void;
  productSummary: string;
  setProductSummary: (summary: string) => void;
  targetUsers: string;
  setTargetUsers: (users: string) => void;
  sensitiveData: SensitiveDataType[];
  setSensitiveData: (data: SensitiveDataType[]) => void;
  mustNotBreakFlows: string[];
  setMustNotBreakFlows: (flows: string[]) => void;
  deploymentTarget: string;
  setDeploymentTarget: (target: string) => void;
  scaleExpectation: string;
  setScaleExpectation: (expectation: string) => void;

  // Step 3: Submit
  submitting: boolean;
  submitError: string | null;

  // Pre-fill
  preFilled: boolean;

  // Validation
  isStep2Valid: () => boolean;

  // Actions
  prefillFromProject: (
    repoParam: string,
    getToken: () => Promise<string | null>,
  ) => Promise<void>;
  handleSubmit: (
    getToken: () => Promise<string | null>,
    onSuccess: (scanId: string) => void,
    onRedirect: (path: string) => void,
  ) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ScanWizardContext = createContext<ScanWizardState | null>(null);

export function useScanWizard(): ScanWizardState {
  const ctx = useContext(ScanWizardContext);
  if (!ctx) {
    throw new Error("useScanWizard must be used within a ScanWizardProvider");
  }
  return ctx;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function ScanWizardProvider({ children }: { children: ReactNode }) {
  // Navigation
  const [step, setStep] = useState(1);

  // Step 1: Repository
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [primerResult, setPrimerResult] = useState<PrimerResult | null>(null);
  const [suggestedFlows, setSuggestedFlows] = useState<string[]>([]);
  const [repoSelectorManual, setRepoSelectorManual] = useState(false);
  const [repoUrlError, setRepoUrlError] = useState<string | null>(null);

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

  // Pre-fill
  const [preFilled, setPreFilled] = useState(false);

  // Rescan detection — true when a project already has intake data
  const [hasExistingContext, setHasExistingContext] = useState(false);

  const goToStep = useCallback(
    (target: number) => {
      if (target >= 2) {
        const urlErr = validateGitHubUrl(repoUrl);
        if (urlErr) {
          setRepoUrlError(urlErr);
          return;
        }
        setRepoUrlError(null);
      }
      setStep(target);
    },
    [repoUrl],
  );

  const isStep2Valid = useCallback(
    () =>
      checkStep2Valid({
        productSummary,
        targetUsers,
        deploymentTarget,
        scaleExpectation,
      }),
    [productSummary, targetUsers, deploymentTarget, scaleExpectation],
  );

  const prefillFromProject = useCallback(
    async (repoParam: string, getToken: () => Promise<string | null>) => {
      setRepoUrl(repoParam);
      try {
        const data = await fetchPrefillData(repoParam, getToken);
        if (!data) return;
        setProjectOrigin(data.projectOrigin);
        setProductSummary(data.productSummary);
        setTargetUsers(data.targetUsers);
        setSensitiveData(data.sensitiveData);
        setMustNotBreakFlows(data.mustNotBreakFlows);
        setDeploymentTarget(data.deploymentTarget);
        setScaleExpectation(data.scaleExpectation);
        setPreFilled(true);
        setHasExistingContext(true);
      } catch {
        // Silently fail -- user can still fill manually
      }
    },
    [],
  );

  const handleSubmit = useCallback(
    async (
      getToken: () => Promise<string | null>,
      onSuccess: (scanId: string) => void,
      onRedirect: (path: string) => void,
    ) => {
      const urlErr = validateGitHubUrl(repoUrl);
      if (urlErr) {
        setRepoUrlError(urlErr);
        setStep(1);
        return;
      }

      setSubmitting(true);
      setSubmitError(null);

      try {
        const body = buildAuditBody({
          repoUrl,
          branch,
          primerResult,
          projectOrigin,
          productSummary,
          targetUsers,
          sensitiveData,
          mustNotBreakFlows,
          deploymentTarget,
          scaleExpectation,
        });
        const scanId = await submitAudit(body, getToken);
        onSuccess(scanId);
      } catch (err) {
        const result = classifySubmitError(err);
        if ("redirect" in result) {
          onRedirect(result.redirect);
        } else {
          setSubmitError(result.message);
        }
      } finally {
        setSubmitting(false);
      }
    },
    [
      repoUrl,
      branch,
      primerResult,
      projectOrigin,
      productSummary,
      targetUsers,
      sensitiveData,
      mustNotBreakFlows,
      deploymentTarget,
      scaleExpectation,
    ],
  );

  const value: ScanWizardState = {
    step,
    setStep,
    goToStep,
    hasExistingContext,
    repoUrl,
    setRepoUrl,
    branch,
    setBranch,
    primerResult,
    setPrimerResult,
    suggestedFlows,
    setSuggestedFlows,
    repoSelectorManual,
    setRepoSelectorManual,
    repoUrlError,
    setRepoUrlError,
    projectOrigin,
    setProjectOrigin,
    productSummary,
    setProductSummary,
    targetUsers,
    setTargetUsers,
    sensitiveData,
    setSensitiveData,
    mustNotBreakFlows,
    setMustNotBreakFlows,
    deploymentTarget,
    setDeploymentTarget,
    scaleExpectation,
    setScaleExpectation,
    submitting,
    submitError,
    preFilled,
    isStep2Valid,
    prefillFromProject,
    handleSubmit,
  };

  return (
    <ScanWizardContext.Provider value={value}>
      {children}
    </ScanWizardContext.Provider>
  );
}
