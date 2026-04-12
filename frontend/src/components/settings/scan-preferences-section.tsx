"use client";

import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";

import type {
  TechnicalLevel,
  ExplanationStyle,
  ShippingPosture,
  CodingTool,
  UserProfile,
} from "@/lib/api/types";

import { Card } from "@/components/ui/card";
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

interface ScanPreferencesSectionProps {
  profile: UserProfile | null;
  onSave: (prefs: {
    technical_level: TechnicalLevel;
    explanation_style: ExplanationStyle;
    shipping_posture: ShippingPosture;
    coding_tool: CodingTool;
    coding_tool_other?: string | null;
  }) => Promise<void>;
  saving: boolean;
}

export function ScanPreferencesSection({
  profile,
  onSave,
  saving,
}: ScanPreferencesSectionProps) {
  const [technicalLevel, setTechnicalLevel] = useState<TechnicalLevel>("engineer");
  const [explanationStyle, setExplanationStyle] = useState<ExplanationStyle>("just_steps");
  const [shippingPosture, setShippingPosture] = useState<ShippingPosture>("balanced");
  const [codingTool, setCodingTool] = useState<CodingTool>("claude_code");
  const [codingToolOther, setCodingToolOther] = useState("");

  // Pre-fill from profile when it loads
  useEffect(() => {
    if (!profile) return;
    if (profile.technical_level) setTechnicalLevel(profile.technical_level);
    if (profile.explanation_style) setExplanationStyle(profile.explanation_style);
    if (profile.shipping_posture) setShippingPosture(profile.shipping_posture);
    if (profile.coding_tool) setCodingTool(profile.coding_tool);
    if (profile.coding_tool_other) setCodingToolOther(profile.coding_tool_other);
  }, [profile]);

  const handleSave = () => {
    onSave({
      technical_level: technicalLevel,
      explanation_style: explanationStyle,
      shipping_posture: shippingPosture,
      coding_tool: codingTool,
      coding_tool_other: codingTool === "other" ? codingToolOther : null,
    });
  };

  const saveDisabled = saving || (codingTool === "other" && !codingToolOther.trim());

  return (
    <Card className="p-5 lg:col-span-2">
      <div className="mb-4">
        <h2 className="text-lg font-semibold mb-1">Scan Preferences</h2>
        <p className="text-sm text-[#8692A8]">
          These influence how FORGE explains findings and filters noise.
        </p>
      </div>

      <div className="grid gap-5">
        {/* Technical Level */}
        <div className="space-y-2">
          <Label className="text-foreground">Technical Level</Label>
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
                    ? "border-forge-emerald/50 bg-forge-emerald/5"
                    : "border-white/[0.06] hover:border-white/[0.08]"
                }`}
              >
                <RadioGroupItem value={value} className="sr-only" />
                <span className="text-sm font-medium text-neutral-200">{label}</span>
                <span className="text-xs text-[#4E586E] text-center">{desc}</span>
              </label>
            ))}
          </RadioGroup>
        </div>

        {/* Explanation Style */}
        <div className="space-y-2">
          <Label className="text-foreground">Explanation Style</Label>
          <Select
            value={explanationStyle}
            onValueChange={(v) => setExplanationStyle(v as ExplanationStyle)}
          >
            <SelectTrigger className="bg-forge-surface border-white/[0.06] text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-forge-surface border-white/[0.06]">
              <SelectItem value="just_steps">Just Steps -- tell me what to do</SelectItem>
              <SelectItem value="teach_me">Explain Why -- teach me the reasoning</SelectItem>
              <SelectItem value="cto_brief">Deep Dive -- executive summary</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Shipping Posture */}
        <div className="space-y-2">
          <Label className="text-foreground">Shipping Posture</Label>
          <Select
            value={shippingPosture}
            onValueChange={(v) => setShippingPosture(v as ShippingPosture)}
          >
            <SelectTrigger className="bg-forge-surface border-white/[0.06] text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-forge-surface border-white/[0.06]">
              <SelectItem value="ship_fast">Move Fast -- speed over perfection</SelectItem>
              <SelectItem value="balanced">Balanced -- pragmatic trade-offs</SelectItem>
              <SelectItem value="production_first">Careful -- stability above all</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Coding Tool */}
        <div className="space-y-2">
          <Label className="text-foreground">Coding Tool</Label>
          <Select
            value={codingTool}
            onValueChange={(v) => setCodingTool(v as CodingTool)}
          >
            <SelectTrigger className="bg-forge-surface border-white/[0.06] text-foreground">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-forge-surface border-white/[0.06]">
              <SelectItem value="claude_code">Claude Code</SelectItem>
              <SelectItem value="cursor">Cursor</SelectItem>
              <SelectItem value="lovable">Lovable</SelectItem>
              <SelectItem value="codex">Codex</SelectItem>
              <SelectItem value="replit">Replit</SelectItem>
              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
          {codingTool === "other" && (
            <Input
              value={codingToolOther}
              onChange={(e) => setCodingToolOther(e.target.value)}
              placeholder="Please state..."
              className="bg-forge-surface border-white/[0.06] text-foreground"
            />
          )}
        </div>
      </div>

      <div className="mt-5">
        <Button
          onClick={handleSave}
          disabled={saveDisabled}
          className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
        >
          {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
          {saving ? "Saving..." : "Save Preferences"}
        </Button>
      </div>
    </Card>
  );
}
