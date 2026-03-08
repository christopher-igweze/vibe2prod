"use client";

import { useState, useEffect } from "react";
import {
  ArrowLeft,
  Github,
  GitBranch,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Search,
  Lock,
  ExternalLink,
  ChevronDown,
} from "lucide-react";

import { apiFetch, ApiError } from "@/lib/api/client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GitHubRepo {
  full_name: string;
  name: string;
  owner: string;
  private: boolean;
  url: string;
  description: string | null;
  language: string | null;
  updated_at: string;
  default_branch: string;
}

interface GitHubBranch {
  name: string;
  protected: boolean;
}

interface GitHubStatus {
  connected: boolean;
  github_username?: string;
}

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
  const [status, setStatus] = useState<GitHubStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Branch state
  const [branches, setBranches] = useState<GitHubBranch[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  const [branchDropdownOpen, setBranchDropdownOpen] = useState(false);

  // Check GitHub connection status on mount
  useEffect(() => {
    let cancelled = false;
    const checkStatus = async () => {
      setStatusLoading(true);
      try {
        const token = await getToken();
        const result = await apiFetch<GitHubStatus>("/api/github/status", {
          token: token ?? undefined,
        });
        if (!cancelled) setStatus(result);
      } catch {
        if (!cancelled) setStatus({ connected: false });
      } finally {
        if (!cancelled) setStatusLoading(false);
      }
    };
    checkStatus();
    return () => { cancelled = true; };
  }, [getToken]);

  // Fetch repos when connected
  useEffect(() => {
    if (!status?.connected) return;
    let cancelled = false;
    const fetchRepos = async () => {
      setReposLoading(true);
      setFetchError(null);
      try {
        const token = await getToken();
        const result = await apiFetch<GitHubRepo[]>(
          `/api/github/repos?page=1&per_page=30`,
          { token: token ?? undefined }
        );
        if (!cancelled) {
          setRepos(result);
          setPage(1);
          setHasMore(result.length === 30);
        }
      } catch (err) {
        if (!cancelled) {
          setFetchError(
            err instanceof ApiError ? err.message : "Failed to load repositories"
          );
        }
      } finally {
        if (!cancelled) setReposLoading(false);
      }
    };
    fetchRepos();
    return () => { cancelled = true; };
  }, [status?.connected, getToken]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const token = await getToken();
      const nextPage = page + 1;
      const result = await apiFetch<GitHubRepo[]>(
        `/api/github/repos?page=${nextPage}&per_page=30`,
        { token: token ?? undefined }
      );
      setRepos((prev) => [...prev, ...result]);
      setPage(nextPage);
      setHasMore(result.length === 30);
    } catch {
      // Silently fail on load more -- user can retry
    } finally {
      setLoadingMore(false);
    }
  };

  // Fetch branches when a repo is selected
  const fetchBranches = async (owner: string, repoName: string) => {
    setBranchesLoading(true);
    setBranches([]);
    try {
      const token = await getToken();
      const result = await apiFetch<GitHubBranch[]>(
        `/api/github/repos/${owner}/${repoName}/branches?per_page=100`,
        { token: token ?? undefined }
      );
      setBranches(result);
    } catch {
      // Silently fail — user can still proceed with default branch
    } finally {
      setBranchesLoading(false);
    }
  };

  const filteredRepos = searchQuery.trim()
    ? repos.filter((r) => {
        const q = searchQuery.toLowerCase();
        return (
          r.name.toLowerCase().includes(q) ||
          r.full_name.toLowerCase().includes(q) ||
          (r.description && r.description.toLowerCase().includes(q))
        );
      })
    : repos;

  const formatDate = (dateStr: string) => {
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
  };

  // Loading state
  if (statusLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-[#8692A8]">
        <Loader2 className="size-4 animate-spin" />
        Checking GitHub connection...
      </div>
    );
  }

  // Not connected -- show fallback hint
  if (!status?.connected) {
    return (
      <div className="rounded-lg border border-white/[0.06] bg-forge-surface/30 p-4">
        <div className="flex items-center gap-2 text-sm text-[#8692A8]">
          <Github className="size-4" />
          <span>
            Connect GitHub in{" "}
            <a
              href="/settings"
              className="text-forge-amber hover:text-forge-amber-light underline underline-offset-2 transition-colors"
            >
              Settings
            </a>{" "}
            for repo browsing
          </span>
        </div>
      </div>
    );
  }

  // Connected -- but user chose manual input mode
  if (showManual) {
    return (
      <div className="space-y-3">
        <button
          type="button"
          onClick={() => onToggleManual(false)}
          className="text-xs text-forge-amber hover:text-forge-amber-light transition-colors flex items-center gap-1"
        >
          <ArrowLeft className="size-3" />
          Back to repo list
        </button>
      </div>
    );
  }

  // Connected -- show repo selector
  return (
    <div className="space-y-3">
      {/* Connected badge */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-[#8692A8]">
          <div className="size-2 rounded-full bg-forge-amber" />
          Connected as{" "}
          <span className="text-neutral-200 font-medium">
            {status.github_username}
          </span>
        </div>
      </div>

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-[#4E586E]" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search your repositories..."
          className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600 pl-9"
        />
      </div>

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
              const isSelected = selectedUrl === repoGitUrl;
              return (
                <div key={repo.full_name}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelect(repoGitUrl, repo.default_branch);
                      fetchBranches(repo.owner, repo.name);
                    }}
                    className={`w-full text-left rounded-lg border p-3 transition-colors ${
                      isSelected
                        ? "border-forge-amber/50 bg-forge-amber/5"
                        : "border-white/[0.06] hover:border-forge-border-hover bg-forge-surface/30"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-neutral-200 truncate">
                            {repo.name}
                          </span>
                          {repo.private && (
                            <Badge
                              variant="outline"
                              className="border-white/[0.08] text-[#4E586E] text-[10px] px-1.5 py-0 h-4 shrink-0"
                            >
                              <Lock className="size-2.5 mr-0.5" />
                              Private
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-[#4E586E] mt-0.5 truncate">
                          {repo.owner}/{repo.name}
                        </p>
                        {repo.description && (
                          <p className="text-xs text-[#8692A8] mt-1 line-clamp-1">
                            {repo.description}
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-1 shrink-0">
                        {repo.language && (
                          <Badge
                            variant="secondary"
                            className="bg-forge-nav text-neutral-300 border-white/[0.06] text-[10px] px-1.5 py-0 h-4"
                          >
                            {repo.language}
                          </Badge>
                        )}
                        <span className="text-[10px] text-neutral-600">
                          {formatDate(repo.updated_at)}
                        </span>
                      </div>
                    </div>
                    {isSelected && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-forge-amber">
                        <CheckCircle2 className="size-3" />
                        Selected
                      </div>
                    )}
                  </button>
                  {/* Branch selector — shown below the selected repo */}
                  {isSelected && (
                    <div className="ml-3 mt-1 relative">
                      <div className="relative">
                        <button
                          type="button"
                          onClick={() => setBranchDropdownOpen(!branchDropdownOpen)}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-white/[0.06] bg-forge-surface text-xs text-neutral-300 hover:border-forge-border-hover transition-colors"
                        >
                          <GitBranch className="size-3 text-[#4E586E]" />
                          {branchesLoading ? (
                            <Loader2 className="size-3 animate-spin" />
                          ) : (
                            <span className="truncate max-w-[200px]">
                              {selectedBranch || repo.default_branch}
                            </span>
                          )}
                          <ChevronDown className="size-3 text-[#4E586E]" />
                        </button>
                        {branchDropdownOpen && branches.length > 0 && (
                          <div className="absolute top-full left-0 mt-1 z-50 w-64 max-h-48 overflow-y-auto rounded-md border border-white/[0.06] bg-forge-surface shadow-lg">
                            {branches.map((b) => (
                              <button
                                key={b.name}
                                type="button"
                                onClick={() => {
                                  onBranchChange(b.name);
                                  setBranchDropdownOpen(false);
                                }}
                                className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center gap-2 ${
                                  (selectedBranch || repo.default_branch) === b.name
                                    ? "bg-forge-amber/10 text-forge-amber"
                                    : "text-neutral-300 hover:bg-forge-nav"
                                }`}
                              >
                                <GitBranch className="size-3 shrink-0 text-[#4E586E]" />
                                <span className="truncate">{b.name}</span>
                                {b.name === repo.default_branch && (
                                  <Badge
                                    variant="outline"
                                    className="border-white/[0.08] text-[#4E586E] text-[9px] px-1 py-0 h-3.5 ml-auto shrink-0"
                                  >
                                    default
                                  </Badge>
                                )}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
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
