"use client";

import { useState } from "react";
import { X, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface FlowTagInputProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  suggestedFlows: string[];
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FlowTagInput({
  tags,
  onChange,
  suggestedFlows,
}: FlowTagInputProps) {
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
            className="bg-forge-nav text-foreground border-white/[0.06] gap-1 pr-1"
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
          className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600"
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => addTag(inputValue)}
          disabled={!inputValue.trim() || tags.length >= 20}
          className="border-white/[0.08] shrink-0"
        >
          Add
        </Button>
      </div>
      {unusedSuggestions.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs text-[#4E586E] flex items-center gap-1">
            <Sparkles className="size-3" />
            Suggested from primer analysis
          </p>
          <div className="flex flex-wrap gap-1.5">
            {unusedSuggestions.map((flow) => (
              <button
                key={flow}
                type="button"
                onClick={() => addTag(flow)}
                className="text-xs px-2.5 py-1 rounded-md border border-dashed border-white/[0.06] text-[#8692A8] hover:text-forge-amber hover:border-forge-amber/40 transition-colors"
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
