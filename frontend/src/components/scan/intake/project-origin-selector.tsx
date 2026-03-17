"use client";

import type { ProjectOrigin } from "@/lib/api/types";

import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

interface ProjectOriginSelectorProps {
  value: ProjectOrigin;
  onChange: (origin: ProjectOrigin) => void;
}

export function ProjectOriginSelector({ value, onChange }: ProjectOriginSelectorProps) {
  return (
    <div className="space-y-3">
      <Label className="text-neutral-300">How was this code created?</Label>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as ProjectOrigin)}
        className="grid grid-cols-2 gap-3"
      >
        <label
          className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
            value === "inspired"
              ? "border-forge-emerald/50 bg-forge-emerald/5"
              : "border-white/[0.06] hover:border-forge-border-hover"
          }`}
        >
          <RadioGroupItem value="inspired" className="mt-0.5" />
          <div>
            <p className="text-sm font-medium text-neutral-200">AI-Generated</p>
            <p className="text-xs text-[#4E586E] mt-0.5">
              Built with Cursor, Copilot, v0, Bolt, etc.
            </p>
          </div>
        </label>
        <label
          className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
            value === "external"
              ? "border-forge-emerald/50 bg-forge-emerald/5"
              : "border-white/[0.06] hover:border-forge-border-hover"
          }`}
        >
          <RadioGroupItem value="external" className="mt-0.5" />
          <div>
            <p className="text-sm font-medium text-neutral-200">Human-Written</p>
            <p className="text-xs text-[#4E586E] mt-0.5">
              Traditional development, external team, etc.
            </p>
          </div>
        </label>
      </RadioGroup>
    </div>
  );
}
