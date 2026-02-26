"use client";

import { useState, useEffect } from "react";
import {
  ArrowLeft,
  Github,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Search,
  Lock,
  ExternalLink,
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

interface GitHubStatus {
  connected: boolean;
  github_username?: string;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface RepoSelectorProps {
  getToken: () => Promise<string | null>;
  onSelect: (url: string) => void;
  selectedUrl: string;
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
            err instanceof ApiError ? err.detail : "Failed to load repositories"
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
      <div className="flex items-center gap-2 py-4 text-sm text-neutral-400">
        <Loader2 className="size-4 animate-spin" />
        Checking GitHub connection...
      </div>
    );
  }

  // Not connected -- show fallback hint
  if (!status?.connected) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4">
        <div className="flex items-center gap-2 text-sm text-neutral-400">
          <Github className="size-4" />
          <span>
            Connect GitHub in{" "}
            <a
              href="/settings"
              className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2 transition-colors"
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
          className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors flex items-center gap-1"
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
        <div className="flex items-center gap-2 text-xs text-neutral-400">
          <div className="size-2 rounded-full bg-emerald-500" />
          Connected as{" "}
          <span className="text-neutral-200 font-medium">
            {status.github_username}
          </span>
        </div>
      </div>

      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-neutral-500" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search your repositories..."
          className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 pl-9"
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
        <div className="flex items-center justify-center py-8 text-sm text-neutral-400">
          <Loader2 className="size-4 animate-spin mr-2" />
          Loading repositories...
        </div>
      ) : (
        <div className="max-h-[340px] overflow-y-auto space-y-2 pr-1 scrollbar-thin scrollbar-thumb-neutral-800 scrollbar-track-transparent">
          {filteredRepos.length === 0 ? (
            <div className="text-center py-6 text-sm text-neutral-500">
              {searchQuery.trim()
                ? "No repositories match your search"
                : "No repositories found"}
            </div>
          ) : (
            filteredRepos.map((repo) => {
              const repoGitUrl = `https://github.com/${repo.full_name}`;
              const isSelected = selectedUrl === repoGitUrl;
              return (
                <button
                  key={repo.full_name}
                  type="button"
                  onClick={() => onSelect(repoGitUrl)}
                  className={`w-full text-left rounded-lg border p-3 transition-colors ${
                    isSelected
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-neutral-800 hover:border-neutral-700 bg-neutral-900/30"
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
                            className="border-neutral-700 text-neutral-500 text-[10px] px-1.5 py-0 h-4 shrink-0"
                          >
                            <Lock className="size-2.5 mr-0.5" />
                            Private
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-neutral-500 mt-0.5 truncate">
                        {repo.owner}/{repo.name}
                      </p>
                      {repo.description && (
                        <p className="text-xs text-neutral-400 mt-1 line-clamp-1">
                          {repo.description}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 shrink-0">
                      {repo.language && (
                        <Badge
                          variant="secondary"
                          className="bg-neutral-800 text-neutral-300 border-neutral-700 text-[10px] px-1.5 py-0 h-4"
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
                    <div className="flex items-center gap-1 mt-2 text-xs text-emerald-400">
                      <CheckCircle2 className="size-3" />
                      Selected
                    </div>
                  )}
                </button>
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
                className="w-full border-neutral-800 text-neutral-400 hover:text-neutral-200"
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
          className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors flex items-center gap-1"
        >
          <ExternalLink className="size-3" />
          Or paste a URL instead
        </button>
      </div>
    </div>
  );
}
