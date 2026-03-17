"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface RepoSearchBarProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
}

export function RepoSearchBar({ searchQuery, onSearchChange }: RepoSearchBarProps) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-[#4E586E]" />
      <Input
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search your repositories..."
        className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600 pl-9"
      />
    </div>
  );
}
