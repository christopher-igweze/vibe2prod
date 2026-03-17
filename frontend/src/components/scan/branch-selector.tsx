"use client";

import { GitBranch, Loader2, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface GitHubBranch {
  name: string;
  protected: boolean;
}

interface BranchSelectorProps {
  branches: GitHubBranch[];
  branchesLoading: boolean;
  selectedBranch: string;
  defaultBranch: string;
  open: boolean;
  onToggle: () => void;
  onSelect: (branchName: string) => void;
}

export function BranchSelector({
  branches,
  branchesLoading,
  selectedBranch,
  defaultBranch,
  open,
  onToggle,
  onSelect,
}: BranchSelectorProps) {
  const displayBranch = selectedBranch || defaultBranch;

  return (
    <div className="ml-3 mt-1 relative">
      <div className="relative">
        <button
          type="button"
          onClick={onToggle}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-white/[0.06] bg-forge-surface text-xs text-neutral-300 hover:border-forge-border-hover transition-colors"
        >
          <GitBranch className="size-3 text-[#4E586E]" />
          {branchesLoading ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <span className="truncate max-w-[200px]">
              {displayBranch}
            </span>
          )}
          <ChevronDown className="size-3 text-[#4E586E]" />
        </button>
        {open && branches.length > 0 && (
          <div className="absolute top-full left-0 mt-1 z-50 w-64 max-h-48 overflow-y-auto rounded-md border border-white/[0.06] bg-forge-surface shadow-lg">
            {branches.map((b) => (
              <button
                key={b.name}
                type="button"
                onClick={() => onSelect(b.name)}
                className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center gap-2 ${
                  displayBranch === b.name
                    ? "bg-forge-emerald/10 text-forge-emerald"
                    : "text-neutral-300 hover:bg-forge-nav"
                }`}
              >
                <GitBranch className="size-3 shrink-0 text-[#4E586E]" />
                <span className="truncate">{b.name}</span>
                {b.name === defaultBranch && (
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
  );
}
