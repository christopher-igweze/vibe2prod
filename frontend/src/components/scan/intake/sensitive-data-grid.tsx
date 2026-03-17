"use client";

import type { SensitiveDataType } from "@/lib/api/types";

import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SENSITIVE_DATA_OPTIONS: { value: SensitiveDataType; label: string; description: string }[] = [
  { value: "payments", label: "Payments", description: "Stripe, billing, transactions" },
  { value: "pii", label: "PII", description: "Names, emails, addresses" },
  { value: "health", label: "Health Data", description: "HIPAA-relevant records" },
  { value: "auth_secrets", label: "Auth Secrets", description: "API keys, tokens, passwords" },
  { value: "none", label: "None", description: "No sensitive data handled" },
  { value: "not_sure", label: "Not Sure", description: "I need help identifying this" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SensitiveDataGridProps {
  value: SensitiveDataType[];
  onChange: (data: SensitiveDataType[]) => void;
}

export function SensitiveDataGrid({ value, onChange }: SensitiveDataGridProps) {
  return (
    <div className="space-y-3">
      <div>
        <Label className="text-neutral-300">Sensitive data handled</Label>
        <p className="text-xs text-[#4E586E] mt-0.5">
          Select all that apply. This affects security severity scoring.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {SENSITIVE_DATA_OPTIONS.map((option) => {
          const isChecked = value.includes(option.value);
          const isExclusive = option.value === "none" || option.value === "not_sure";

          const toggle = () => {
            if (!isChecked) {
              if (isExclusive) {
                onChange([option.value]);
              } else {
                onChange(
                  [...value.filter((d) => d !== "none" && d !== "not_sure"), option.value]
                );
              }
            } else {
              onChange(value.filter((d) => d !== option.value));
            }
          };

          return (
            <div
              key={option.value}
              role="button"
              tabIndex={0}
              onClick={toggle}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } }}
              className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                isChecked
                  ? "border-forge-emerald/50 bg-forge-emerald/5"
                  : "border-white/[0.06] hover:border-forge-border-hover"
              }`}
            >
              <Checkbox
                checked={isChecked}
                onCheckedChange={() => toggle()}
                className="mt-0.5 pointer-events-none"
              />
              <div>
                <p className="text-sm text-neutral-200">{option.label}</p>
                <p className="text-xs text-[#4E586E]">{option.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
