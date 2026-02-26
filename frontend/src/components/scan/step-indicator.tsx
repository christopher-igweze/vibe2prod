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
                ? "bg-emerald-600 text-white"
                : currentStep > step.number
                  ? "bg-emerald-600/20 text-emerald-400 border border-emerald-600/30"
                  : "bg-neutral-900 text-neutral-500 border border-neutral-800"
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
              currentStep === step.number ? "text-neutral-200" : "text-neutral-500"
            }`}
          >
            {step.label}
          </span>
          {i < STEPS.length - 1 && (
            <div className="w-8 sm:w-12 h-px bg-neutral-800 mx-1" />
          )}
        </div>
      ))}
    </div>
  );
}
