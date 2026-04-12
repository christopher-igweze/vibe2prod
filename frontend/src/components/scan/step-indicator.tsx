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
  /** When true, step 2 (Project Context) is hidden from the indicator */
  skipStep2?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function StepIndicator({ currentStep, skipStep2 = false }: StepIndicatorProps) {
  const visibleSteps = skipStep2
    ? STEPS.filter((s) => s.number !== 2)
    : STEPS;

  return (
    <div className="flex items-center gap-2 mb-8">
      {visibleSteps.map((step, i) => (
        <div key={step.number} className="flex items-center gap-2">
          <div
            className={`flex items-center justify-center size-8 rounded-full text-sm font-medium transition-colors ${
              currentStep === step.number
                ? "bg-forge-emerald text-[#0B0F19]"
                : currentStep > step.number
                  ? "bg-forge-emerald/20 text-forge-emerald"
                  : "bg-forge-surface text-[#4E586E] border border-white/[0.06]"
            }`}
          >
            {currentStep > step.number ? (
              <CheckCircle2 className="size-4" />
            ) : (
              skipStep2 ? i + 1 : step.number
            )}
          </div>
          <span
            className={`text-sm hidden sm:inline ${
              currentStep === step.number ? "text-foreground" : "text-[#4E586E]"
            }`}
          >
            {step.label}
          </span>
          {i < visibleSteps.length - 1 && (
            <div className="w-8 sm:w-12 h-px bg-white/[0.06] mx-1" />
          )}
        </div>
      ))}
    </div>
  );
}
