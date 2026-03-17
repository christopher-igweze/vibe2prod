"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface IntakeNavigationProps {
  onBack: () => void;
  onContinue: () => void;
  onSkip: () => void;
  isValid: boolean;
}

export function IntakeNavigation({ onBack, onContinue, onSkip, isValid }: IntakeNavigationProps) {
  return (
    <div className="flex justify-between pt-2">
      <Button
        variant="outline"
        onClick={onBack}
        className="border-white/[0.08]"
      >
        <ArrowLeft className="size-4 mr-1" />
        Back
      </Button>
      <div className="flex gap-2">
        <Button
          variant="ghost"
          onClick={onSkip}
          className="text-[#4E586E] hover:text-[#8692A8]"
        >
          Skip for now
        </Button>
        <Button
          onClick={onContinue}
          disabled={!isValid}
          className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
        >
          Review & Submit
          <ArrowRight className="size-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}
