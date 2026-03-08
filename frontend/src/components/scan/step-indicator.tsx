"use client";

import { CheckCircle2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STEPS = [
  { number: 1, label: "Repository" },
  { number: 2, label: "Project Context" },
  { number: 3, label: "Submit" },
] as const;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface StepIndicatorProps {
  currentStep: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {STEPS.map((step, i) => (
        <div key={step.number} className="flex items-center gap-2">
          <div
            className={`flex items-center justify-center size-8 rounded-full text-sm font-medium transition-colors ${
              currentStep === step.number
                ? "bg-forge-amber text-[#0B0F19]"
                : currentStep > step.number
                  ? "bg-forge-amber/20 text-forge-amber"
                  : "bg-forge-surface text-[#4E586E] border border-white/[0.06]"
            }`}
          >
            {currentStep > step.number ? (
              <CheckCircle2 className="size-4" />
            ) : (
              step.number
            )}
          </div>
          <span
            className={`text-sm hidden sm:inline ${
              currentStep === step.number ? "text-foreground" : "text-[#4E586E]"
            }`}
          >
            {step.label}
          </span>
          {i < STEPS.length - 1 && (
            <div className="w-8 sm:w-12 h-px bg-white/[0.06] mx-1" />
          )}
        </div>
      ))}
    </div>
  );
}
