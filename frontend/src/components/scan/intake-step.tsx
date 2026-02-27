"use client";

import { ArrowLeft, ArrowRight, Shield } from "lucide-react";

import type { ProjectOrigin, SensitiveDataType } from "@/lib/api/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";

import { FlowTagInput } from "@/components/scan/flow-tag-input";

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
    <Card className="bg-neutral-950 border-neutral-800">
      <CardHeader>
        <CardTitle className="text-neutral-100 flex items-center gap-2">
          <Shield className="size-5" />
          Project Context
        </CardTitle>
        <CardDescription className="text-neutral-400">
          This context drives how we classify and prioritize findings. Be specific -- it directly
          impacts audit quality.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Project Origin */}
        <div className="space-y-3">
          <Label className="text-neutral-300">How was this code created?</Label>
          <RadioGroup
            value={projectOrigin}
            onValueChange={(v) => setProjectOrigin(v as ProjectOrigin)}
            className="grid grid-cols-2 gap-3"
          >
            <label
              className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                projectOrigin === "inspired"
                  ? "border-emerald-500/50 bg-emerald-500/5"
                  : "border-neutral-800 hover:border-neutral-700"
              }`}
            >
              <RadioGroupItem value="inspired" className="mt-0.5" />
              <div>
                <p className="text-sm font-medium text-neutral-200">AI-Generated</p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Built with Cursor, Copilot, v0, Bolt, etc.
                </p>
              </div>
            </label>
            <label
              className={`flex items-start gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                projectOrigin === "external"
                  ? "border-emerald-500/50 bg-emerald-500/5"
                  : "border-neutral-800 hover:border-neutral-700"
              }`}
            >
              <RadioGroupItem value="external" className="mt-0.5" />
              <div>
                <p className="text-sm font-medium text-neutral-200">Human-Written</p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Traditional development, external team, etc.
                </p>
              </div>
            </label>
          </RadioGroup>
        </div>

        <Separator className="bg-neutral-800" />

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
            className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 min-h-20"
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
            className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 min-h-16"
            maxLength={400}
          />
          <p className="text-xs text-neutral-600 text-right">
            {targetUsers.length}/400
          </p>
        </div>

        <Separator className="bg-neutral-800" />

        {/* Sensitive Data */}
        <div className="space-y-3">
          <div>
            <Label className="text-neutral-300">Sensitive data handled</Label>
            <p className="text-xs text-neutral-500 mt-0.5">
              Select all that apply. This affects security severity scoring.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {SENSITIVE_DATA_OPTIONS.map((option) => {
              const isChecked = sensitiveData.includes(option.value);
              const isExclusive = option.value === "none" || option.value === "not_sure";

              const toggle = () => {
                if (!isChecked) {
                  if (isExclusive) {
                    setSensitiveData([option.value]);
                  } else {
                    setSensitiveData(
                      [...sensitiveData.filter((d) => d !== "none" && d !== "not_sure"), option.value]
                    );
                  }
                } else {
                  setSensitiveData(sensitiveData.filter((d) => d !== option.value));
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
                      ? "border-emerald-500/30 bg-emerald-500/5"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <Checkbox
                    checked={isChecked}
                    onCheckedChange={() => toggle()}
                    className="mt-0.5 pointer-events-none"
                  />
                  <div>
                    <p className="text-sm text-neutral-200">{option.label}</p>
                    <p className="text-xs text-neutral-500">{option.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <Separator className="bg-neutral-800" />

        {/* Must Not Break Flows */}
        <div className="space-y-2">
          <div>
            <Label className="text-neutral-300">Critical user flows that must not break</Label>
            <p className="text-xs text-neutral-500 mt-0.5">
              These get elevated to &quot;must_fix&quot; priority when issues are found in their paths.
            </p>
          </div>
          <FlowTagInput
            tags={mustNotBreakFlows}
            onChange={setMustNotBreakFlows}
            suggestedFlows={suggestedFlows}
          />
        </div>

        <Separator className="bg-neutral-800" />

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
            className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600"
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
            className="bg-neutral-900 border-neutral-800 text-neutral-200 placeholder:text-neutral-600"
            maxLength={200}
          />
        </div>

        {/* Navigation */}
        <div className="flex justify-between pt-2">
          <Button
            variant="outline"
            onClick={onBack}
            className="border-neutral-700"
          >
            <ArrowLeft className="size-4 mr-1" />
            Back
          </Button>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={onSkip}
              className="text-neutral-500 hover:text-neutral-300"
            >
              Skip for now
            </Button>
            <Button
              onClick={onContinue}
              disabled={!isValid}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Review & Submit
              <ArrowRight className="size-4 ml-1" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
