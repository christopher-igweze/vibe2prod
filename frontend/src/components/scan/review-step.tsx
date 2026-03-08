"use client";

import {
  ArrowLeft,
  Github,
  Loader2,
  AlertTriangle,
  Zap,
} from "lucide-react";

import type {
  PrimerResult,
  ProjectOrigin,
  SensitiveDataType,
} from "@/lib/api/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ReviewStepProps {
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
  submitting: boolean;
  submitError: string | null;
  onEditRepo: () => void;
  onEditContext: () => void;
  onBack: () => void;
  onSubmit: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ReviewStep({
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
  submitting,
  submitError,
  onEditRepo,
  onEditContext,
  onBack,
  onSubmit,
}: ReviewStepProps) {
  // Render helpers
  const primerJson = primerResult?.primer_json;
  const repoName = (primerJson?.repo_full_name as string) || "";
  const displayBranch = branch || (primerJson?.default_branch as string) || "";

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <Card className="bg-background border-white/[0.06]">
        <CardHeader>
          <CardTitle className="text-neutral-100 flex items-center gap-2">
            <Zap className="size-5" />
            Review & Submit
          </CardTitle>
          <CardDescription className="text-[#8692A8]">
            Confirm your scan details before kicking off the audit.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Repo info */}
          <div className="rounded-lg border border-white/[0.06] bg-forge-surface/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-[#4E586E] uppercase tracking-wider font-medium">
                Repository
              </p>
              <button
                type="button"
                onClick={onEditRepo}
                className="text-xs text-forge-emerald hover:text-forge-emerald-light transition-colors"
              >
                Edit
              </button>
            </div>
            <div className="flex items-center gap-2">
              <Github className="size-4 text-[#8692A8]" />
              <span className="text-sm text-neutral-200 font-mono truncate">
                {repoUrl.trim()}
              </span>
            </div>
            {primerResult && (
              <div className="flex items-center gap-3 text-xs text-[#4E586E]">
                {repoName && <span>{repoName}</span>}
                {displayBranch && (
                  <>
                    <span className="text-white/[0.08]">|</span>
                    <span>{displayBranch}</span>
                  </>
                )}
                {primerResult.confidence > 0 && (
                  <>
                    <span className="text-white/[0.08]">|</span>
                    <span>Primer confidence: {primerResult.confidence}%</span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Project context summary */}
          <div className="rounded-lg border border-white/[0.06] bg-forge-surface/30 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-[#4E586E] uppercase tracking-wider font-medium">
                Project Context
              </p>
              <button
                type="button"
                onClick={onEditContext}
                className="text-xs text-forge-emerald hover:text-forge-emerald-light transition-colors"
              >
                Edit
              </button>
            </div>
            <div className="grid gap-2 text-sm">
              <div className="flex gap-2">
                <span className="text-[#4E586E] shrink-0 w-28">Origin:</span>
                <span className="text-neutral-200">
                  {projectOrigin === "inspired" ? "AI-Generated" : "Human-Written"}
                </span>
              </div>
              <div className="flex gap-2">
                <span className="text-[#4E586E] shrink-0 w-28">Product:</span>
                <span className="text-neutral-300 line-clamp-2">{productSummary}</span>
              </div>
              <div className="flex gap-2">
                <span className="text-[#4E586E] shrink-0 w-28">Users:</span>
                <span className="text-neutral-300 line-clamp-1">{targetUsers}</span>
              </div>
              <div className="flex gap-2">
                <span className="text-[#4E586E] shrink-0 w-28">Data:</span>
                <span className="text-neutral-300">
                  {sensitiveData.length > 0
                    ? sensitiveData.join(", ")
                    : "Not specified"}
                </span>
              </div>
              {mustNotBreakFlows.length > 0 && (
                <div className="flex gap-2">
                  <span className="text-[#4E586E] shrink-0 w-28">Critical flows:</span>
                  <span className="text-neutral-300">{mustNotBreakFlows.length} defined</span>
                </div>
              )}
              <div className="flex gap-2">
                <span className="text-[#4E586E] shrink-0 w-28">Deployment:</span>
                <span className="text-neutral-300 line-clamp-1">{deploymentTarget}</span>
              </div>
              <div className="flex gap-2">
                <span className="text-[#4E586E] shrink-0 w-28">Scale:</span>
                <span className="text-neutral-300 line-clamp-1">{scaleExpectation}</span>
              </div>
            </div>
          </div>

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
              onClick={onBack}
              className="border-white/[0.08]"
            >
              <ArrowLeft className="size-4 mr-1" />
              Back
            </Button>
            <Button
              onClick={onSubmit}
              disabled={submitting}
              className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19] min-w-32"
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
  );
}
