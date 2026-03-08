"use client";

import { useState } from "react";
import {
  ArrowRight,
  Github,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

import { apiFetch, ApiError } from "@/lib/api/client";
import type { PrimerResponse, PrimerResult } from "@/lib/api/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RepoSelector } from "@/components/scan/repo-selector";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GITHUB_URL_REGEX = /^https?:\/\/(www\.)?github\.com\/[\w.-]+\/[\w.-]+\/?$/;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface RepoStepProps {
  getToken: () => Promise<string | null>;
  repoUrl: string;
  setRepoUrl: (url: string) => void;
  branch: string;
  setBranch: (branch: string) => void;
  primerResult: PrimerResult | null;
  setPrimerResult: (result: PrimerResult | null) => void;
  setSuggestedFlows: (flows: string[]) => void;
  repoSelectorManual: boolean;
  setRepoSelectorManual: (manual: boolean) => void;
  onContinue: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RepoStep({
  getToken,
  repoUrl,
  setRepoUrl,
  branch,
  setBranch,
  primerResult,
  setPrimerResult,
  setSuggestedFlows,
  repoSelectorManual,
  setRepoSelectorManual,
  onContinue,
}: RepoStepProps) {
  // Local state for primer loading / errors
  const [repoUrlError, setRepoUrlError] = useState<string | null>(null);
  const [primerLoading, setPrimerLoading] = useState(false);
  const [primerWarning, setPrimerWarning] = useState<string | null>(null);

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

  const runPrimer = async () => {
    setPrimerLoading(true);
    setPrimerResult(null);
    setPrimerWarning(null);
    setSuggestedFlows([]);

    try {
      const token = await getToken();
      const primerBody: { repo_url: string; branch?: string } = {
        repo_url: repoUrl.trim(),
      };
      if (branch) primerBody.branch = branch;

      const result = await apiFetch<PrimerResponse>("/api/primer", {
        method: "POST",
        body: JSON.stringify(primerBody),
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
        setPrimerWarning(`Primer analysis failed: ${err.message}. You can still continue.`);
      } else {
        setPrimerWarning("Could not analyze repository. You can still continue manually.");
      }
    } finally {
      setPrimerLoading(false);
    }
  };

  const handleContinue = () => {
    if (!validateUrl(repoUrl)) return;
    // Kick off primer in the background if not already done
    if (!primerResult && !primerLoading) {
      runPrimer();
    }
    onContinue();
  };

  // Render helpers
  const primerJson = primerResult?.primer_json;
  const fileCount = Array.isArray(primerJson?.file_tree_sample)
    ? (primerJson.file_tree_sample as string[]).length
    : 0;
  const repoName = (primerJson?.repo_full_name as string) || "";
  const displayBranch = branch || (primerJson?.default_branch as string) || "";

  return (
    <Card className="bg-background border-white/[0.06]">
      <CardHeader>
        <CardTitle className="text-neutral-100 flex items-center gap-2">
          <Github className="size-5" />
          Repository
        </CardTitle>
        <CardDescription className="text-[#8692A8]">
          Select a repository from your GitHub account, or paste a URL manually.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* GitHub Repo Selector */}
        <RepoSelector
          getToken={getToken}
          onSelect={(url, defaultBranchName) => {
            setRepoUrl(url);
            setBranch(defaultBranchName);
            if (repoUrlError) setRepoUrlError(null);
            setRepoSelectorManual(false);
          }}
          selectedUrl={repoUrl}
          selectedBranch={branch}
          onBranchChange={setBranch}
          showManual={repoSelectorManual}
          onToggleManual={setRepoSelectorManual}
        />

        {/* Manual URL Input -- always visible as fallback */}
        <div className="space-y-2">
          <Label htmlFor="repo-url" className="text-neutral-300">
            GitHub URL
          </Label>
          <Input
            id="repo-url"
            value={repoUrl}
            onChange={(e) => {
              setRepoUrl(e.target.value);
              if (repoUrlError) setRepoUrlError(null);
            }}
            placeholder="https://github.com/owner/repo"
            className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleContinue();
              }
            }}
          />
          {repoUrlError && (
            <p className="text-sm text-red-400 flex items-center gap-1.5">
              <AlertTriangle className="size-3.5 shrink-0" />
              {repoUrlError}
            </p>
          )}
        </div>

        {/* Primer Loading State */}
        {primerLoading && (
          <div className="rounded-lg border border-white/[0.06] bg-forge-surface/50 p-4">
            <div className="flex items-center gap-3">
              <Loader2 className="size-5 animate-spin text-forge-emerald" />
              <div>
                <p className="text-sm text-neutral-200">Analyzing repository...</p>
                <p className="text-xs text-[#4E586E]">
                  Cloning, scanning file tree, and identifying patterns
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Primer Warning */}
        {primerWarning && !primerLoading && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="size-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-emerald-200">{primerWarning}</p>
                <p className="text-xs text-neutral-500 mt-1">
                  You can still continue -- the audit will work without primer data.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Primer Results */}
        {primerResult && !primerLoading && (
          <div className="rounded-lg border border-forge-emerald/20 bg-forge-emerald/5 p-4 space-y-4">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="size-5 text-forge-emerald shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-forge-emerald">Repository analyzed</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
                  {repoName && (
                    <div>
                      <p className="text-xs text-[#4E586E]">Repository</p>
                      <p className="text-sm text-neutral-200 truncate">{repoName}</p>
                    </div>
                  )}
                  {displayBranch && (
                    <div>
                      <p className="text-xs text-[#4E586E]">Branch</p>
                      <p className="text-sm text-neutral-200">{displayBranch}</p>
                    </div>
                  )}
                  {fileCount > 0 && (
                    <div>
                      <p className="text-xs text-[#4E586E]">Files found</p>
                      <p className="text-sm text-neutral-200">{fileCount}+</p>
                    </div>
                  )}
                </div>

                {primerResult.summary && (
                  <div className="mt-3 pt-3 border-t border-forge-emerald/10">
                    <p className="text-xs text-[#4E586E] mb-1">AI Summary</p>
                    <p className="text-sm text-neutral-300 whitespace-pre-line leading-relaxed">
                      {primerResult.summary}
                    </p>
                  </div>
                )}

              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-end pt-2">
          <Button
            onClick={handleContinue}
            disabled={!repoUrl.trim() || primerLoading}
            className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
          >
            {primerLoading ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                Continue
                <ArrowRight className="size-4 ml-1" />
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
