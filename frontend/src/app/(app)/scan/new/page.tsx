"use client";

export const dynamic = "force-dynamic";

import { useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Github,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  X,
  Sparkles,
  Shield,
  Zap,
} from "lucide-react";

import { apiFetch, ApiError } from "@/lib/api/client";
import type {
  PrimerResponse,
  PrimerResult,
  AuditResponse,
  QuotaLimits,
  ProjectOrigin,
  SensitiveDataType,
  ProjectIntake,
  OrgOnboardingPayload,
  TechnicalLevel,
  ExplanationStyle,
  ShippingPosture,
  CodingAgentProvider,
  AcquisitionSource,
} from "@/lib/api/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GITHUB_URL_REGEX = /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$/;

const SENSITIVE_DATA_OPTIONS: { value: SensitiveDataType; label: string; description: string }[] = [
  { value: "payments", label: "Payments", description: "Stripe, billing, transactions" },
  { value: "pii", label: "PII", description: "Names, emails, addresses" },
  { value: "health", label: "Health Data", description: "HIPAA-relevant records" },
  { value: "auth_secrets", label: "Auth Secrets", description: "API keys, tokens, passwords" },
  { value: "none", label: "None", description: "No sensitive data handled" },
  { value: "not_sure", label: "Not Sure", description: "I need help identifying this" },
];

const STEPS = [
  { number: 1, label: "Repository" },
  { number: 2, label: "Project Context" },
  { number: 3, label: "Submit" },
] as const;

// ---------------------------------------------------------------------------
// Onboarding Modal
// ---------------------------------------------------------------------------

function OnboardingModal({
  open,
  onClose,
  onComplete,
  getToken,
}: {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
  getToken: () => Promise<string | null>;
}) {
  const [technicalLevel, setTechnicalLevel] = useState<TechnicalLevel>("engineer");
  const [explanationStyle, setExplanationStyle] = useState<ExplanationStyle>("just_steps");
  const [shippingPosture, setShippingPosture] = useState<ShippingPosture>("balanced");
  const [codingAgentProvider, setCodingAgentProvider] = useState<CodingAgentProvider>("anthropic");
  const [codingAgentModel, setCodingAgentModel] = useState("claude-sonnet-4");
  const [acquisitionSource, setAcquisitionSource] = useState<AcquisitionSource>("google_search");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      const token = await getToken();
      const payload: OrgOnboardingPayload = {
        technical_level: technicalLevel,
        explanation_style: explanationStyle,
        shipping_posture: shippingPosture,
        tool_tags: [],
        acquisition_source: acquisitionSource,
        coding_agent_provider: codingAgentProvider,
        coding_agent_model: codingAgentModel,
      };
      await apiFetch("/api/onboarding/org", {
        method: "POST",
        body: JSON.stringify(payload),
        token: token ?? undefined,
      });
      onComplete();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to save onboarding");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-lg bg-neutral-950 border-neutral-800">
        <DialogHeader>
          <DialogTitle className="text-neutral-100">Quick Setup</DialogTitle>
          <DialogDescription className="text-neutral-400">
            Tell us a bit about yourself so we can tailor your audit reports.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-2">
          {/* Technical Level */}
          <div className="space-y-2">
            <Label className="text-neutral-300">What describes you best?</Label>
            <RadioGroup
              value={technicalLevel}
              onValueChange={(v) => setTechnicalLevel(v as TechnicalLevel)}
              className="grid grid-cols-3 gap-2"
            >
              {(
                [
                  ["engineer", "Engineer", "I write code daily"],
                  ["vibe_coder", "Vibe Coder", "I use AI to build"],
                  ["founder", "Founder", "I ship products"],
                ] as const
              ).map(([value, label, desc]) => (
                <label
                  key={value}
                  className={`flex flex-col items-center gap-1 rounded-lg border p-3 cursor-pointer transition-colors ${
                    technicalLevel === value
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <RadioGroupItem value={value} className="sr-only" />
                  <span className="text-sm font-medium text-neutral-200">{label}</span>
                  <span className="text-xs text-neutral-500 text-center">{desc}</span>
                </label>
              ))}
            </RadioGroup>
          </div>

          {/* Explanation Style */}
          <div className="space-y-2">
            <Label className="text-neutral-300">How should we explain findings?</Label>
            <Select value={explanationStyle} onValueChange={(v) => setExplanationStyle(v as ExplanationStyle)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="teach_me">Teach Me -- explain the why</SelectItem>
                <SelectItem value="just_steps">Just Steps -- tell me what to do</SelectItem>
                <SelectItem value="cto_brief">CTO Brief -- executive summary</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Shipping Posture */}
          <div className="space-y-2">
            <Label className="text-neutral-300">Shipping priority?</Label>
            <Select value={shippingPosture} onValueChange={(v) => setShippingPosture(v as ShippingPosture)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="ship_fast">Ship Fast -- speed over perfection</SelectItem>
                <SelectItem value="balanced">Balanced -- pragmatic trade-offs</SelectItem>
                <SelectItem value="production_first">Production First -- stability above all</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Coding Agent */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label className="text-neutral-300">AI Provider</Label>
              <Select value={codingAgentProvider} onValueChange={(v) => setCodingAgentProvider(v as CodingAgentProvider)}>
                <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-neutral-900 border-neutral-800">
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="google">Google</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-neutral-300">Model</Label>
              <Input
                value={codingAgentModel}
                onChange={(e) => setCodingAgentModel(e.target.value)}
                placeholder="e.g. claude-sonnet-4"
                className="bg-neutral-900 border-neutral-800 text-neutral-200"
              />
            </div>
          </div>

          {/* Acquisition */}
          <div className="space-y-2">
            <Label className="text-neutral-300">How did you find us?</Label>
            <Select value={acquisitionSource} onValueChange={(v) => setAcquisitionSource(v as AcquisitionSource)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="x_twitter">X / Twitter</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="youtube">YouTube</SelectItem>
                <SelectItem value="reddit">Reddit</SelectItem>
                <SelectItem value="product_hunt">Product Hunt</SelectItem>
                <SelectItem value="hacker_news">Hacker News</SelectItem>
                <SelectItem value="google_search">Google Search</SelectItem>
                <SelectItem value="referral">Referral</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p className="text-sm text-red-400 flex items-center gap-1.5">
              <AlertTriangle className="size-3.5" />
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="border-neutral-700">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={saving || !codingAgentModel.trim()}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            {saving ? <Loader2 className="size-4 animate-spin" /> : "Save & Continue"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Step Indicator
// ---------------------------------------------------------------------------

function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {STEPS.map((step, i) => (
        <div key={step.number} className="flex items-center gap-2">
          <div
            className={`flex items-center justify-center size-8 rounded-full text-sm font-medium transition-colors ${
              currentStep === step.number
                ? "bg-emerald-600 text-white"
                : currentStep > step.number
                  ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30"
                  : "bg-neutral-900 text-neutral-500 border border-neutral-800"
            }`}
          >
            {currentStep > step.number ? (
              <CheckCircle2 className="size-4" />
            ) : (
              step.number
            )}
          </div>
          <span
            className={`text-sm hidden sm:inline ${
              currentStep === step.number ? "text-neutral-200" : "text-neutral-500"
            }`}
          >
            {step.label}
          </span>
          {i < STEPS.length - 1 && (
            <div className="w-8 sm:w-12 h-px bg-neutral-800 mx-1" />
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Flow Tag Input
// ---------------------------------------------------------------------------

function FlowTagInput({
  tags,
  onChange,
  suggestedFlows,
}: {
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestedFlows: string[];
}) {
  const [inputValue, setInputValue] = useState("");

  const addTag = (tag: string) => {
    const trimmed = tag.trim();
    if (trimmed && !tags.includes(trimmed) && tags.length < 20) {
      onChange([...tags, trimmed]);
    }
    setInputValue("");
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag(inputValue);
    }
  };

  const unusedSuggestions = suggestedFlows.filter((f) => !tags.includes(f));

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Badge
            key={tag}
            variant="secondary"
            className="bg-neutral-800 text-neutral-200 border-neutral-700 gap-1 pr-1"
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="ml-1 hover:text-red-400 transition-colors rounded-full p-0.5"
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a flow and press Enter..."
          className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addTag(inputValue)}
          disabled={!inputValue.trim() || tags.length >= 20}
          className="border-neutral-700 shrink-0"
        >
          Add
        </Button>
      </div>
      {unusedSuggestions.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-neutral-500 flex items-center gap-1">
            <Sparkles className="size-3" />
            Suggested from primer analysis
          </p>
          <div className="flex flex-wrap gap-1.5">
            {unusedSuggestions.map((flow) => (
              <button
                key={flow}
                type="button"
                onClick={() => addTag(flow)}
                className="text-xs px-2.5 py-1 rounded-md border border-dashed border-neutral-700 text-neutral-400 hover:text-emerald-400 hover:border-emerald-600/40 transition-colors"
              >
                + {flow}
              </button>
            ))}
          </div>
        </div>
      )}
      {tags.length >= 20 && (
        <p className="text-xs text-amber-400">Maximum 20 flows reached.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function NewScanPage() {
  const { getToken } = useAuth();
  const router = useRouter();

  // Wizard state
  const [step, setStep] = useState(1);

  // Step 1: Repo URL + Primer
  const [repoUrl, setRepoUrl] = useState("");
  const [repoUrlError, setRepoUrlError] = useState<string | null>(null);
  const [primerLoading, setPrimerLoading] = useState(false);
  const [primerResult, setPrimerResult] = useState<PrimerResult | null>(null);
  const [suggestedFlows, setSuggestedFlows] = useState<string[]>([]);
  const [primerWarning, setPrimerWarning] = useState<string | null>(null);

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

  // -------------------------------------------------------------------------
  // Step 1: Analyze repo
  // -------------------------------------------------------------------------

  const validateUrl = (url: string): boolean => {
    if (!url.trim()) {
      setRepoUrlError("Please enter a GitHub repository URL");
      return false;
    }
    if (!GITHUB_URL_REGEX.test(url.trim())) {
      setRepoUrlError("Must be a valid GitHub URL (e.g. https://github.com/owner/repo)");
      return false;
    }
    setRepoUrlError(null);
    return true;
  };

  const handleAnalyze = async () => {
    if (!validateUrl(repoUrl)) return;

    setPrimerLoading(true);
    setPrimerResult(null);
    setPrimerWarning(null);
    setSuggestedFlows([]);

    try {
      const token = await getToken();
      const result = await apiFetch<PrimerResponse>("/api/primer", {
        method: "POST",
        body: JSON.stringify({ repo_url: repoUrl.trim() }),
        token: token ?? undefined,
      });

      setPrimerResult(result.primer);
      setSuggestedFlows(result.suggested_flows);

      if (result.primer.failure_reason) {
        setPrimerWarning(
          "Primer analysis partially failed. You can still continue with manual intake."
        );
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setPrimerWarning(`Primer analysis failed: ${err.detail}. You can still continue.`);
      } else {
        setPrimerWarning("Could not analyze repository. You can still continue manually.");
      }
    } finally {
      setPrimerLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Step 2 validation
  // -------------------------------------------------------------------------

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

  // -------------------------------------------------------------------------
  // Step 3: Check quota + submit
  // -------------------------------------------------------------------------

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
        project_intake: ProjectIntake;
        primer?: PrimerResult;
      } = {
        repo_url: repoUrl.trim(),
        project_intake: intake,
      };

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

  // -------------------------------------------------------------------------
  // Step navigation
  // -------------------------------------------------------------------------

  const goToStep = (target: number) => {
    if (target === 2 && !repoUrl.trim()) return;
    if (target === 3) {
      if (!isStep2Valid()) return;
      checkQuota();
    }
    setStep(target);
  };

  // -------------------------------------------------------------------------
  // Render helpers
  // -------------------------------------------------------------------------

  const primerJson = primerResult?.primer_json;
  const fileCount = Array.isArray(primerJson?.file_tree_sample)
    ? (primerJson.file_tree_sample as string[]).length
    : 0;
  const repoName = (primerJson?.repo_full_name as string) || "";
  const defaultBranch = (primerJson?.default_branch as string) || "";

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

      {/* ================================================================= */}
      {/* Step 1: Repository URL + Primer                                   */}
      {/* ================================================================= */}
      {step === 1 && (
        <Card className="bg-neutral-950 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-neutral-100 flex items-center gap-2">
              <Github className="size-5" />
              Repository
            </CardTitle>
            <CardDescription className="text-neutral-400">
              Paste your GitHub repository URL. We will pre-analyze it to help with the audit.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* URL Input */}
            <div className="space-y-2">
              <Label htmlFor="repo-url" className="text-neutral-300">
                GitHub URL
              </Label>
              <div className="flex gap-2">
                <Input
                  id="repo-url"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    if (repoUrlError) setRepoUrlError(null);
                  }}
                  placeholder="https://github.com/owner/repo"
                  className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 flex-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAnalyze();
                    }
                  }}
                />
                <Button
                  onClick={handleAnalyze}
                  disabled={primerLoading || !repoUrl.trim()}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white shrink-0"
                >
                  {primerLoading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    "Analyze"
                  )}
                </Button>
              </div>
              {repoUrlError && (
                <p className="text-sm text-red-400 flex items-center gap-1.5">
                  <AlertTriangle className="size-3.5 shrink-0" />
                  {repoUrlError}
                </p>
              )}
            </div>

            {/* Primer Loading State */}
            {primerLoading && (
              <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
                <div className="flex items-center gap-3">
                  <Loader2 className="size-5 animate-spin text-emerald-400" />
                  <div>
                    <p className="text-sm text-neutral-200">Analyzing repository...</p>
                    <p className="text-xs text-neutral-500">
                      Cloning, scanning file tree, and identifying patterns
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Primer Warning */}
            {primerWarning && !primerLoading && (
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="size-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-amber-200">{primerWarning}</p>
                    <p className="text-xs text-neutral-500 mt-1">
                      You can still continue -- the audit will work without primer data.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Primer Results */}
            {primerResult && !primerLoading && (
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="size-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-emerald-300">Repository analyzed</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
                      {repoName && (
                        <div>
                          <p className="text-xs text-neutral-500">Repository</p>
                          <p className="text-sm text-neutral-200 truncate">{repoName}</p>
                        </div>
                      )}
                      {defaultBranch && (
                        <div>
                          <p className="text-xs text-neutral-500">Branch</p>
                          <p className="text-sm text-neutral-200">{defaultBranch}</p>
                        </div>
                      )}
                      {fileCount > 0 && (
                        <div>
                          <p className="text-xs text-neutral-500">Files found</p>
                          <p className="text-sm text-neutral-200">{fileCount}+</p>
                        </div>
                      )}
                    </div>

                    {primerResult.summary && (
                      <div className="mt-3 pt-3 border-t border-emerald-500/10">
                        <p className="text-xs text-neutral-500 mb-1">AI Summary</p>
                        <p className="text-sm text-neutral-300 whitespace-pre-line leading-relaxed">
                          {primerResult.summary}
                        </p>
                      </div>
                    )}

                    {primerResult.confidence > 0 && (
                      <div className="mt-3 flex items-center gap-2">
                        <span className="text-xs text-neutral-500">Confidence</span>
                        <Progress
                          value={primerResult.confidence}
                          className="flex-1 h-1.5 bg-neutral-800"
                        />
                        <span className="text-xs text-neutral-400">
                          {primerResult.confidence}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-end pt-2">
              <Button
                onClick={() => goToStep(2)}
                disabled={!repoUrl.trim()}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                Continue
                <ArrowRight className="size-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================================================================= */}
      {/* Step 2: Project Intake Form                                       */}
      {/* ================================================================= */}
      {step === 2 && (
        <Card className="bg-neutral-950 border-neutral-800">
          <CardHeader>
            <CardTitle className="text-neutral-100 flex items-center gap-2">
              <Shield className="size-5" />
              Project Context
            </CardTitle>
            <CardDescription className="text-neutral-400">
              This context drives how we classify and prioritize findings. Be specific -- it directly
              impacts audit quality.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Project Origin */}
            <div className="space-y-3">
              <Label className="text-neutral-300">How was this code created?</Label>
              <RadioGroup
                value={projectOrigin}
                onValueChange={(v) => setProjectOrigin(v as ProjectOrigin)}
                className="grid grid-cols-2 gap-3"
              >
                <label
                  className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                    projectOrigin === "inspired"
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <RadioGroupItem value="inspired" className="mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-neutral-200">AI-Generated</p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      Built with Cursor, Copilot, v0, Bolt, etc.
                    </p>
                  </div>
                </label>
                <label
                  className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                    projectOrigin === "external"
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <RadioGroupItem value="external" className="mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-neutral-200">Human-Written</p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      Traditional development, external team, etc.
                    </p>
                  </div>
                </label>
              </RadioGroup>
            </div>

            <Separator className="bg-neutral-800" />

            {/* Product Summary */}
            <div className="space-y-2">
              <Label htmlFor="product-summary" className="text-neutral-300">
                What does your product do?
              </Label>
              <Textarea
                id="product-summary"
                value={productSummary}
                onChange={(e) => setProductSummary(e.target.value)}
                placeholder="e.g. A SaaS platform that helps freelancers track invoices and get paid faster..."
                className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 min-h-20"
                maxLength={800}
              />
              <p className="text-xs text-neutral-600 text-right">
                {productSummary.length}/800
              </p>
            </div>

            {/* Target Users */}
            <div className="space-y-2">
              <Label htmlFor="target-users" className="text-neutral-300">
                Who uses this?
              </Label>
              <Textarea
                id="target-users"
                value={targetUsers}
                onChange={(e) => setTargetUsers(e.target.value)}
                placeholder="e.g. Small business owners and freelancers managing their client billing..."
                className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 min-h-16"
                maxLength={400}
              />
              <p className="text-xs text-neutral-600 text-right">
                {targetUsers.length}/400
              </p>
            </div>

            <Separator className="bg-neutral-800" />

            {/* Sensitive Data */}
            <div className="space-y-3">
              <div>
                <Label className="text-neutral-300">Sensitive data handled</Label>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Select all that apply. This affects security severity scoring.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {SENSITIVE_DATA_OPTIONS.map((option) => {
                  const isChecked = sensitiveData.includes(option.value);
                  const isExclusive = option.value === "none" || option.value === "not_sure";

                  return (
                    <label
                      key={option.value}
                      className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                        isChecked
                          ? "border-emerald-500/30 bg-emerald-500/5"
                          : "border-neutral-800 hover:border-neutral-700"
                      }`}
                    >
                      <Checkbox
                        checked={isChecked}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            if (isExclusive) {
                              setSensitiveData([option.value]);
                            } else {
                              setSensitiveData(
                                [...sensitiveData.filter((d) => d !== "none" && d !== "not_sure"), option.value]
                              );
                            }
                          } else {
                            setSensitiveData(sensitiveData.filter((d) => d !== option.value));
                          }
                        }}
                        className="mt-0.5"
                      />
                      <div>
                        <p className="text-sm text-neutral-200">{option.label}</p>
                        <p className="text-xs text-neutral-500">{option.description}</p>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            <Separator className="bg-neutral-800" />

            {/* Must Not Break Flows */}
            <div className="space-y-2">
              <div>
                <Label className="text-neutral-300">Critical user flows that must not break</Label>
                <p className="text-xs text-neutral-500 mt-0.5">
                  These get elevated to &quot;must_fix&quot; priority when issues are found in their paths.
                </p>
              </div>
              <FlowTagInput
                tags={mustNotBreakFlows}
                onChange={setMustNotBreakFlows}
                suggestedFlows={suggestedFlows}
              />
            </div>

            <Separator className="bg-neutral-800" />

            {/* Deployment Target */}
            <div className="space-y-2">
              <Label htmlFor="deployment-target" className="text-neutral-300">
                Where is this deployed?
              </Label>
              <Input
                id="deployment-target"
                value={deploymentTarget}
                onChange={(e) => setDeploymentTarget(e.target.value)}
                placeholder="e.g. Vercel (frontend) + Railway (backend) + Supabase (DB)"
                className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600"
                maxLength={200}
              />
            </div>

            {/* Scale Expectation */}
            <div className="space-y-2">
              <Label htmlFor="scale-expectation" className="text-neutral-300">
                Expected scale/traffic?
              </Label>
              <Input
                id="scale-expectation"
                value={scaleExpectation}
                onChange={(e) => setScaleExpectation(e.target.value)}
                placeholder="e.g. ~500 DAU currently, expecting 5k within 3 months"
                className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600"
                maxLength={200}
              />
            </div>

            {/* Navigation */}
            <div className="flex justify-between pt-2">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                className="border-neutral-700"
              >
                <ArrowLeft className="size-4 mr-1" />
                Back
              </Button>
              <Button
                onClick={() => goToStep(3)}
                disabled={!isStep2Valid()}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                Review & Submit
                <ArrowRight className="size-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================================================================= */}
      {/* Step 3: Review & Submit                                           */}
      {/* ================================================================= */}
      {step === 3 && (
        <div className="space-y-6">
          {/* Summary Card */}
          <Card className="bg-neutral-950 border-neutral-800">
            <CardHeader>
              <CardTitle className="text-neutral-100 flex items-center gap-2">
                <Zap className="size-5" />
                Review & Submit
              </CardTitle>
              <CardDescription className="text-neutral-400">
                Confirm your scan details before kicking off the audit.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Repo info */}
              <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">
                    Repository
                  </p>
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    Edit
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <Github className="size-4 text-neutral-400" />
                  <span className="text-sm text-neutral-200 font-mono truncate">
                    {repoUrl.trim()}
                  </span>
                </div>
                {primerResult && (
                  <div className="flex items-center gap-3 text-xs text-neutral-500">
                    {repoName && <span>{repoName}</span>}
                    {defaultBranch && (
                      <>
                        <span className="text-neutral-700">|</span>
                        <span>{defaultBranch}</span>
                      </>
                    )}
                    {primerResult.confidence > 0 && (
                      <>
                        <span className="text-neutral-700">|</span>
                        <span>Primer confidence: {primerResult.confidence}%</span>
                      </>
                    )}
                  </div>
                )}
              </div>

              {/* Project context summary */}
              <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-neutral-500 uppercase tracking-wider font-medium">
                    Project Context
                  </p>
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    Edit
                  </button>
                </div>
                <div className="grid gap-2 text-sm">
                  <div className="flex gap-2">
                    <span className="text-neutral-500 shrink-0 w-28">Origin:</span>
                    <span className="text-neutral-200">
                      {projectOrigin === "inspired" ? "AI-Generated" : "Human-Written"}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-neutral-500 shrink-0 w-28">Product:</span>
                    <span className="text-neutral-300 line-clamp-2">{productSummary}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-neutral-500 shrink-0 w-28">Users:</span>
                    <span className="text-neutral-300 line-clamp-1">{targetUsers}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-neutral-500 shrink-0 w-28">Data:</span>
                    <span className="text-neutral-300">
                      {sensitiveData.length > 0
                        ? sensitiveData.join(", ")
                        : "Not specified"}
                    </span>
                  </div>
                  {mustNotBreakFlows.length > 0 && (
                    <div className="flex gap-2">
                      <span className="text-neutral-500 shrink-0 w-28">Critical flows:</span>
                      <span className="text-neutral-300">{mustNotBreakFlows.length} defined</span>
                    </div>
                  )}
                  <div className="flex gap-2">
                    <span className="text-neutral-500 shrink-0 w-28">Deployment:</span>
                    <span className="text-neutral-300 line-clamp-1">{deploymentTarget}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="text-neutral-500 shrink-0 w-28">Scale:</span>
                    <span className="text-neutral-300 line-clamp-1">{scaleExpectation}</span>
                  </div>
                </div>
              </div>

              {/* Quota info */}
              {quotaChecking && (
                <div className="flex items-center gap-2 text-sm text-neutral-400">
                  <Loader2 className="size-4 animate-spin" />
                  Checking scan quota...
                </div>
              )}

              {quota && !quotaError && (
                <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-400">Scans remaining this month</span>
                    <span className="text-sm font-medium text-neutral-200">
                      {quota.reports_remaining} / {quota.reports_limit}
                    </span>
                  </div>
                  <Progress
                    value={((quota.reports_limit - quota.reports_remaining) / quota.reports_limit) * 100}
                    className="mt-2 h-1.5 bg-neutral-800"
                  />
                </div>
              )}

              {quotaError && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 flex items-start gap-3">
                  <AlertTriangle className="size-5 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-300">{quotaError}</p>
                </div>
              )}

              {submitError && (
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 flex items-start gap-3">
                  <AlertTriangle className="size-5 text-red-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-red-300">{submitError}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-between pt-2">
                <Button
                  variant="outline"
                  onClick={() => setStep(2)}
                  className="border-neutral-700"
                >
                  <ArrowLeft className="size-4 mr-1" />
                  Back
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={
                    submitting ||
                    (quota !== null && quota.reports_remaining <= 0)
                  }
                  className="bg-emerald-600 hover:bg-emerald-700 text-white min-w-32"
                >
                  {submitting ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Starting scan...
                    </>
                  ) : (
                    <>
                      <Zap className="size-4" />
                      Start Audit
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
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
