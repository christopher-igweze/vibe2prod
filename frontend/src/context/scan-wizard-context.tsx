"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

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
// Types
// ---------------------------------------------------------------------------

export interface ScanWizardState {
  // Navigation
  step: number;
  setStep: (step: number) => void;
  goToStep: (target: number) => void;

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

  // ---------------------------------------------------------------------------
  // Navigation with validation
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Step 2 validation
  // ---------------------------------------------------------------------------

  const isStep2Valid = useCallback((): boolean => {
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
  }, [productSummary, targetUsers, deploymentTarget, scaleExpectation]);

  // ---------------------------------------------------------------------------
  // Pre-fill from previous project
  // ---------------------------------------------------------------------------

  const prefillFromProject = useCallback(
    async (repoParam: string, getToken: () => Promise<string | null>) => {
      setRepoUrl(repoParam);

      try {
        const token = (await getToken()) ?? undefined;

        const projects = await apiFetch<ProjectSummary[]>("/api/user/projects", {
          token,
        });
        const match = projects.find((p) => p.repo_url === repoParam);
        if (!match) return;

        const intakeResp = await apiFetch<{ project_intake: ProjectIntake | null }>(
          `/api/user/projects/${match.id}/intake`,
          { token },
        );

        const intake = intakeResp.project_intake;
        if (!intake) return;

        setProjectOrigin(intake.project_origin);
        setProductSummary(intake.product_summary || "");
        setTargetUsers(intake.target_users || "");
        setSensitiveData(intake.sensitive_data || []);
        setMustNotBreakFlows(intake.must_not_break_flows || []);
        setDeploymentTarget(intake.deployment_target || "");
        setScaleExpectation(intake.scale_expectation || "");
        setPreFilled(true);
      } catch {
        // Silently fail -- user can still fill manually
      }
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

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
        const token = await getToken();

        const body: {
          repo_url: string;
          branch?: string;
          project_intake?: ProjectIntake;
          primer?: PrimerResult;
        } = {
          repo_url: repoUrl.trim(),
        };

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

        if (branch) body.branch = branch;
        if (primerResult) body.primer = primerResult;

        const result = await apiFetch<AuditResponse>("/api/audit", {
          method: "POST",
          body: JSON.stringify(body),
          token: token ?? undefined,
        });

        onSuccess(result.scan_id);
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 403) {
            const detail =
              typeof err.detail === "object" ? err.detail : { message: err.detail };
            const code = (detail as { code?: string })?.code;

            if (code === "waitlist_required") {
              onRedirect("/waitlist");
              return;
            }
            if (code === "onboarding_required") {
              onRedirect("/onboarding");
              return;
            }

            setSubmitError(
              (detail as { message?: string })?.message ||
                err.message ||
                "Access denied",
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

  // ---------------------------------------------------------------------------
  // Context value
  // ---------------------------------------------------------------------------

  const value: ScanWizardState = {
    step,
    setStep,
    goToStep,
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
