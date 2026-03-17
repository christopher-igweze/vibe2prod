"use client";

import {
  ArrowLeft,
  Github,
  Loader2,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useRepoSelection } from "@/hooks/use-repo-selection";
import { RepoSearchBar } from "./repo-search-bar";
import { RepoListItem } from "./repo-list-item";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface RepoSelectorProps {
  getToken: () => Promise<string | null>;
  onSelect: (url: string, defaultBranch: string) => void;
  selectedUrl: string;
  selectedBranch: string;
  onBranchChange: (branch: string) => void;
  showManual: boolean;
  onToggleManual: (manual: boolean) => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return "today";
    if (diffDays === 1) return "yesterday";
    if (diffDays < 30) return `${diffDays}d ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
    return `${Math.floor(diffDays / 365)}y ago`;
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RepoSelector({
  getToken,
  onSelect,
  selectedUrl,
  selectedBranch,
  onBranchChange,
  showManual,
  onToggleManual,
}: RepoSelectorProps) {
  const {
    status,
    statusLoading,
    repos: filteredRepos,
    reposLoading,
    searchQuery,
    setSearchQuery,
    hasMore,
    loadingMore,
    loadMore,
    fetchError,
    branches,
    branchesLoading,
    branchDropdownOpen,
    setBranchDropdownOpen,
    fetchBranches,
  } = useRepoSelection({ getToken, selectedUrl });

  // Loading state
  if (statusLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-[#8692A8]">
        <Loader2 className="size-4 animate-spin" />
        Checking GitHub connection...
      </div>
    );
  }

  // Not connected
  if (!status?.connected) {
    return (
      <div className="rounded-lg border border-white/[0.06] bg-forge-surface/30 p-4">
        <div className="flex items-center gap-2 text-sm text-[#8692A8]">
          <Github className="size-4" />
          <span>
            Connect GitHub in{" "}
            <a
              href="/settings"
              className="text-forge-emerald hover:text-forge-emerald-light underline underline-offset-2 transition-colors"
            >
              Settings
            </a>{" "}
            for repo browsing
          </span>
        </div>
      </div>
    );
  }

  // Manual input mode
  if (showManual) {
    return (
      <div className="space-y-3">
        <button
          type="button"
          onClick={() => onToggleManual(false)}
          className="text-xs text-forge-emerald hover:text-forge-emerald-light transition-colors flex items-center gap-1"
        >
          <ArrowLeft className="size-3" />
          Back to repo list
        </button>
      </div>
    );
  }

  // Connected — repo selector
  return (
    <div className="space-y-3">
      {/* Connected badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-[#8692A8]">
          <div className="size-2 rounded-full bg-forge-emerald" />
          Connected as{" "}
          <span className="text-neutral-200 font-medium">
            {status.github_username}
          </span>
        </div>
      </div>

      <RepoSearchBar searchQuery={searchQuery} onSearchChange={setSearchQuery} />

      {/* Error state */}
      {fetchError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 flex items-start gap-2">
          <AlertTriangle className="size-4 text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{fetchError}</p>
        </div>
      )}

      {/* Repos list */}
      {reposLoading ? (
        <div className="flex items-center justify-center py-8 text-sm text-[#8692A8]">
          <Loader2 className="size-4 animate-spin mr-2" />
          Loading repositories...
        </div>
      ) : (
        <div className="max-h-[340px] overflow-y-auto space-y-2 pr-1 scrollbar-thin scrollbar-thumb-white/[0.06] scrollbar-track-transparent">
          {filteredRepos.length === 0 ? (
            <div className="text-center py-6 text-sm text-[#4E586E]">
              {searchQuery.trim()
                ? "No repositories match your search"
                : "No repositories found"}
            </div>
          ) : (
            filteredRepos.map((repo) => {
              const repoGitUrl = `https://github.com/${repo.full_name}`;
              return (
                <RepoListItem
                  key={repo.full_name}
                  repo={repo}
                  isSelected={selectedUrl === repoGitUrl}
                  selectedBranch={selectedBranch}
                  branches={branches}
                  branchesLoading={branchesLoading}
                  branchDropdownOpen={branchDropdownOpen}
                  onSelect={onSelect}
                  onFetchBranches={fetchBranches}
                  onBranchToggle={() => setBranchDropdownOpen(!branchDropdownOpen)}
                  onBranchChange={(name) => {
                    onBranchChange(name);
                    setBranchDropdownOpen(false);
                  }}
                  formatDate={formatDate}
                />
              );
            })
          )}

          {/* Load more button */}
          {hasMore && !searchQuery.trim() && (
            <div className="pt-2 pb-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={loadMore}
                disabled={loadingMore}
                className="w-full border-white/[0.06] text-[#8692A8] hover:text-neutral-200"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="size-3 animate-spin mr-1" />
                    Loading...
                  </>
                ) : (
                  "Load more"
                )}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Toggle to manual input */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => onToggleManual(true)}
          className="text-xs text-[#4E586E] hover:text-[#8692A8] transition-colors flex items-center gap-1"
        >
          <ExternalLink className="size-3" />
          Or paste a URL instead
        </button>
      </div>
    </div>
  );
}
