"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface GuidedTourSectionProps {
  resetting: boolean;
  onRestart: () => void;
}

export function GuidedTourSection({ resetting, onRestart }: GuidedTourSectionProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold mb-1">Guided Tour</h2>
          <p className="text-sm text-[#8692A8]">
            Retake the interactive walkthrough to learn how the platform works.
          </p>
        </div>
      </div>
      <div className="mt-4">
        <Button
          onClick={onRestart}
          disabled={resetting}
          className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
        >
          {resetting ? "Resetting..." : "Restart Tour"}
        </Button>
      </div>
    </Card>
  );
}
