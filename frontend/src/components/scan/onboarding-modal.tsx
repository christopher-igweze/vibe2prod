"use client";

import { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

import { apiFetch, ApiError } from "@/lib/api/client";
import type {
  OrgOnboardingPayload,
  TechnicalLevel,
  ExplanationStyle,
  ShippingPosture,
  CodingAgentProvider,
  AcquisitionSource,
} from "@/lib/api/types";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface OnboardingModalProps {
  open: boolean;
  onClose: () => void;
  onComplete: () => void;
  getToken: () => Promise<string | null>;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OnboardingModal({
  open,
  onClose,
  onComplete,
  getToken,
}: OnboardingModalProps) {
  const [technicalLevel, setTechnicalLevel] = useState<TechnicalLevel>("engineer");
  const [explanationStyle, setExplanationStyle] = useState<ExplanationStyle>("just_steps");
  const [shippingPosture, setShippingPosture] = useState<ShippingPosture>("balanced");
  const [codingAgentProvider, setCodingAgentProvider] = useState<CodingAgentProvider>("anthropic");
  const [codingAgentModel, setCodingAgentModel] = useState("claude-sonnet-4");
  const [acquisitionSource, setAcquisitionSource] = useState<AcquisitionSource>("google_search");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setSaving(true);
    setError(null);
    try {
      const token = await getToken();
      const payload: OrgOnboardingPayload = {
        technical_level: technicalLevel,
        explanation_style: explanationStyle,
        shipping_posture: shippingPosture,
        tool_tags: [],
        acquisition_source: acquisitionSource,
        coding_agent_provider: codingAgentProvider,
        coding_agent_model: codingAgentModel,
      };
      await apiFetch("/api/onboarding/org", {
        method: "POST",
        body: JSON.stringify(payload),
        token: token ?? undefined,
      });
      onComplete();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save onboarding");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-lg bg-neutral-950 border-neutral-800">
        <DialogHeader>
          <DialogTitle className="text-neutral-100">Quick Setup</DialogTitle>
          <DialogDescription className="text-neutral-400">
            Tell us a bit about yourself so we can tailor your audit reports.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-2">
          {/* Technical Level */}
          <div className="space-y-2">
            <Label className="text-neutral-300">What describes you best?</Label>
            <RadioGroup
              value={technicalLevel}
              onValueChange={(v) => setTechnicalLevel(v as TechnicalLevel)}
              className="grid grid-cols-3 gap-2"
            >
              {(
                [
                  ["engineer", "Engineer", "I write code daily"],
                  ["vibe_coder", "Vibe Coder", "I use AI to build"],
                  ["founder", "Founder", "I ship products"],
                ] as const
              ).map(([value, label, desc]) => (
                <label
                  key={value}
                  className={`flex flex-col items-center gap-1 rounded-lg border p-3 cursor-pointer transition-colors ${
                    technicalLevel === value
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-neutral-800 hover:border-neutral-700"
                  }`}
                >
                  <RadioGroupItem value={value} className="sr-only" />
                  <span className="text-sm font-medium text-neutral-200">{label}</span>
                  <span className="text-xs text-neutral-500 text-center">{desc}</span>
                </label>
              ))}
            </RadioGroup>
          </div>

          {/* Explanation Style */}
          <div className="space-y-2">
            <Label className="text-neutral-300">How should we explain findings?</Label>
            <Select value={explanationStyle} onValueChange={(v) => setExplanationStyle(v as ExplanationStyle)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="teach_me">Teach Me -- explain the why</SelectItem>
                <SelectItem value="just_steps">Just Steps -- tell me what to do</SelectItem>
                <SelectItem value="cto_brief">CTO Brief -- executive summary</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Shipping Posture */}
          <div className="space-y-2">
            <Label className="text-neutral-300">Shipping priority?</Label>
            <Select value={shippingPosture} onValueChange={(v) => setShippingPosture(v as ShippingPosture)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="ship_fast">Ship Fast -- speed over perfection</SelectItem>
                <SelectItem value="balanced">Balanced -- pragmatic trade-offs</SelectItem>
                <SelectItem value="production_first">Production First -- stability above all</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Coding Agent */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label className="text-neutral-300">AI Provider</Label>
              <Select value={codingAgentProvider} onValueChange={(v) => setCodingAgentProvider(v as CodingAgentProvider)}>
                <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-neutral-900 border-neutral-800">
                  <SelectItem value="anthropic">Anthropic</SelectItem>
                  <SelectItem value="openai">OpenAI</SelectItem>
                  <SelectItem value="google">Google</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-neutral-300">Model</Label>
              <Input
                value={codingAgentModel}
                onChange={(e) => setCodingAgentModel(e.target.value)}
                placeholder="e.g. claude-sonnet-4"
                className="bg-neutral-900 border-neutral-800 text-neutral-200"
              />
            </div>
          </div>

          {/* Acquisition */}
          <div className="space-y-2">
            <Label className="text-neutral-300">How did you find us?</Label>
            <Select value={acquisitionSource} onValueChange={(v) => setAcquisitionSource(v as AcquisitionSource)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="x_twitter">X / Twitter</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="youtube">YouTube</SelectItem>
                <SelectItem value="reddit">Reddit</SelectItem>
                <SelectItem value="product_hunt">Product Hunt</SelectItem>
                <SelectItem value="hacker_news">Hacker News</SelectItem>
                <SelectItem value="google_search">Google Search</SelectItem>
                <SelectItem value="referral">Referral</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p className="text-sm text-red-400 flex items-center gap-1.5">
              <AlertTriangle className="size-3.5" />
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="border-neutral-700">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={saving || !codingAgentModel.trim()}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            {saving ? <Loader2 className="size-4 animate-spin" /> : "Save & Continue"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
