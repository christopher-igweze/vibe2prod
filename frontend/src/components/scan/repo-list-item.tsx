"use client";

import { Lock, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { BranchSelector } from "./branch-selector";

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

interface RepoListItemProps {
  repo: GitHubRepo;
  isSelected: boolean;
  selectedBranch: string;
  branches: GitHubBranch[];
  branchesLoading: boolean;
  branchDropdownOpen: boolean;
  onSelect: (repoGitUrl: string, defaultBranch: string) => void;
  onFetchBranches: (owner: string, name: string) => void;
  onBranchToggle: () => void;
  onBranchChange: (branchName: string) => void;
  formatDate: (dateStr: string) => string;
}

export function RepoListItem({
  repo,
  isSelected,
  selectedBranch,
  branches,
  branchesLoading,
  branchDropdownOpen,
  onSelect,
  onFetchBranches,
  onBranchToggle,
  onBranchChange,
  formatDate,
}: RepoListItemProps) {
  const repoGitUrl = `https://github.com/${repo.full_name}`;

  return (
    <div>
      <button
        type="button"
        onClick={() => {
          onSelect(repoGitUrl, repo.default_branch);
          onFetchBranches(repo.owner, repo.name);
        }}
        className={`w-full text-left rounded-lg border p-3 transition-colors ${
          isSelected
            ? "border-forge-emerald/50 bg-forge-emerald/5"
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
          <div className="flex items-center gap-1 mt-2 text-xs text-forge-emerald">
            <CheckCircle2 className="size-3" />
            Selected
          </div>
        )}
      </button>
      {/* Branch selector — shown below the selected repo */}
      {isSelected && (
        <BranchSelector
          branches={branches}
          branchesLoading={branchesLoading}
          selectedBranch={selectedBranch}
          defaultBranch={repo.default_branch}
          open={branchDropdownOpen}
          onToggle={onBranchToggle}
          onSelect={onBranchChange}
        />
      )}
    </div>
  );
}
