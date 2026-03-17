"use client";

import { Shield } from "lucide-react";

import type { ProjectOrigin, SensitiveDataType } from "@/lib/api/types";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";

import { FlowTagInput } from "@/components/scan/flow-tag-input";
import { ProjectOriginSelector } from "@/components/scan/intake/project-origin-selector";
import { SensitiveDataGrid } from "@/components/scan/intake/sensitive-data-grid";
import { IntakeNavigation } from "@/components/scan/intake/intake-navigation";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface IntakeStepProps {
  projectOrigin: ProjectOrigin;
  setProjectOrigin: (origin: ProjectOrigin) => void;
  productSummary: string;
  setProductSummary: (summary: string) => void;
  targetUsers: string;
  setTargetUsers: (users: string) => void;
  sensitiveData: SensitiveDataType[];
  setSensitiveData: (data: SensitiveDataType[]) => void;
  mustNotBreakFlows: string[];
  setMustNotBreakFlows: (flows: string[]) => void;
  deploymentTarget: string;
  setDeploymentTarget: (target: string) => void;
  scaleExpectation: string;
  setScaleExpectation: (expectation: string) => void;
  suggestedFlows: string[];
  onBack: () => void;
  onContinue: () => void;
  onSkip: () => void;
  isValid: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function IntakeStep({
  projectOrigin,
  setProjectOrigin,
  productSummary,
  setProductSummary,
  targetUsers,
  setTargetUsers,
  sensitiveData,
  setSensitiveData,
  mustNotBreakFlows,
  setMustNotBreakFlows,
  deploymentTarget,
  setDeploymentTarget,
  scaleExpectation,
  setScaleExpectation,
  suggestedFlows,
  onBack,
  onContinue,
  onSkip,
  isValid,
}: IntakeStepProps) {
  return (
    <Card className="bg-background border-white/[0.06]">
      <CardHeader>
        <CardTitle className="text-neutral-100 flex items-center gap-2">
          <Shield className="size-5" />
          Project Context
        </CardTitle>
        <CardDescription className="text-[#8692A8]">
          This context drives how we classify and prioritize findings. Be specific -- it directly
          impacts audit quality.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Project Origin */}
        <ProjectOriginSelector value={projectOrigin} onChange={setProjectOrigin} />

        <Separator className="bg-white/[0.06]" />

        {/* Product Summary */}
        <div className="space-y-2">
          <Label htmlFor="product-summary" className="text-neutral-300">
            What does your product do?
          </Label>
          <Textarea
            id="product-summary"
            value={productSummary}
            onChange={(e) => setProductSummary(e.target.value)}
            placeholder="e.g. A SaaS platform that helps freelancers track invoices and get paid faster..."
            className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600 min-h-20"
            maxLength={800}
          />
          <p className="text-xs text-neutral-600 text-right">
            {productSummary.length}/800
          </p>
        </div>

        {/* Target Users */}
        <div className="space-y-2">
          <Label htmlFor="target-users" className="text-neutral-300">
            Who uses this?
          </Label>
          <Textarea
            id="target-users"
            value={targetUsers}
            onChange={(e) => setTargetUsers(e.target.value)}
            placeholder="e.g. Small business owners and freelancers managing their client billing..."
            className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600 min-h-16"
            maxLength={400}
          />
          <p className="text-xs text-neutral-600 text-right">
            {targetUsers.length}/400
          </p>
        </div>

        <Separator className="bg-white/[0.06]" />

        {/* Sensitive Data */}
        <SensitiveDataGrid value={sensitiveData} onChange={setSensitiveData} />

        <Separator className="bg-white/[0.06]" />

        {/* Must Not Break Flows */}
        <div className="space-y-2">
          <div>
            <Label className="text-neutral-300">Critical user flows that must not break</Label>
            <p className="text-xs text-[#4E586E] mt-0.5">
              These get elevated to &quot;must_fix&quot; priority when issues are found in their paths.
            </p>
          </div>
          <FlowTagInput
            tags={mustNotBreakFlows}
            onChange={setMustNotBreakFlows}
            suggestedFlows={suggestedFlows}
          />
        </div>

        <Separator className="bg-white/[0.06]" />

        {/* Deployment Target */}
        <div className="space-y-2">
          <Label htmlFor="deployment-target" className="text-neutral-300">
            Where is this deployed?
          </Label>
          <Input
            id="deployment-target"
            value={deploymentTarget}
            onChange={(e) => setDeploymentTarget(e.target.value)}
            placeholder="e.g. Vercel (frontend) + Railway (backend) + Supabase (DB)"
            className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600"
            maxLength={200}
          />
        </div>

        {/* Scale Expectation */}
        <div className="space-y-2">
          <Label htmlFor="scale-expectation" className="text-neutral-300">
            Expected scale/traffic?
          </Label>
          <Input
            id="scale-expectation"
            value={scaleExpectation}
            onChange={(e) => setScaleExpectation(e.target.value)}
            placeholder="e.g. ~500 DAU currently, expecting 5k within 3 months"
            className="bg-forge-surface border-white/[0.06] text-neutral-200 placeholder:text-neutral-600"
            maxLength={200}
          />
        </div>

        {/* Navigation */}
        <IntakeNavigation
          onBack={onBack}
          onContinue={onContinue}
          onSkip={onSkip}
          isValid={isValid}
        />
      </CardContent>
    </Card>
  );
}
