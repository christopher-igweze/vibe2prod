"use client";

import { useState, useEffect } from "react";
import { apiFetch, ApiError } from "@/lib/api/client";

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

export interface UseRepoSelectionOptions {
  getToken: () => Promise<string | null>;
  selectedUrl: string;
}

export function useRepoSelection({ getToken, selectedUrl }: UseRepoSelectionOptions) {
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

          // Auto-fetch branches if a repo is already selected (rescan)
          if (selectedUrl) {
            const match = result.find(
              (r) => `https://github.com/${r.full_name}` === selectedUrl
            );
            if (match) {
              fetchBranches(match.owner, match.name);
              setBranchDropdownOpen(true);
            }
          }
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

  return {
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
  };
}
