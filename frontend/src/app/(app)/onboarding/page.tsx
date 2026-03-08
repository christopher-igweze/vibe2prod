"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import { AlertTriangle, Loader2, Rocket } from "lucide-react"

import { apiFetch, ApiError } from "@/lib/api/client"
import type {
  OrgOnboardingPayload,
  TechnicalLevel,
  ExplanationStyle,
  ShippingPosture,
  CodingTool,
  AcquisitionSource,
} from "@/lib/api/types"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export default function OnboardingPage() {
  const router = useRouter()
  const { getToken } = useAuth()

  const [technicalLevel, setTechnicalLevel] = useState<TechnicalLevel>("engineer")
  const [explanationStyle, setExplanationStyle] = useState<ExplanationStyle>("just_steps")
  const [shippingPosture, setShippingPosture] = useState<ShippingPosture>("balanced")
  const [codingTool, setCodingTool] = useState<CodingTool>("claude_code")
  const [codingToolOther, setCodingToolOther] = useState("")
  const [acquisitionSource, setAcquisitionSource] = useState<AcquisitionSource>("hackathon")
  const [acquisitionOther, setAcquisitionOther] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    setSaving(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const payload: OrgOnboardingPayload = {
        technical_level: technicalLevel,
        explanation_style: explanationStyle,
        shipping_posture: shippingPosture,
        tool_tags: [],
        coding_tool: codingTool,
        coding_tool_other: codingTool === "other" ? codingToolOther : null,
        acquisition_source: acquisitionSource,
        acquisition_other: acquisitionSource === "other" ? acquisitionOther : null,
      }
      await apiFetch("/api/onboarding/org", {
        method: "POST",
        body: JSON.stringify(payload),
        token,
      })
      // Full reload to clear stale useUserRole cache
      window.location.href = "/dashboard"
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save onboarding")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-6">
      <div className="w-full max-w-lg space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-emerald-500/15 mb-2">
            <Rocket className="size-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-neutral-100">Welcome to Vibe2Prod</h1>
          <p className="text-neutral-400">
            Tell us a bit about yourself so we can tailor your audit reports.
          </p>
        </div>

        <div className="grid gap-5 rounded-xl border border-neutral-800 bg-neutral-950 p-6">
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

          {/* Coding Tool */}
          <div className="space-y-2">
            <Label className="text-neutral-300">What do you mostly build with?</Label>
            <Select value={codingTool} onValueChange={(v) => setCodingTool(v as CodingTool)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="claude_code">Claude Code</SelectItem>
                <SelectItem value="codex">Codex</SelectItem>
                <SelectItem value="antigravity">AntiGravity</SelectItem>
                <SelectItem value="cursor">Cursor</SelectItem>
                <SelectItem value="replit">Replit</SelectItem>
                <SelectItem value="lovable">Lovable</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
            {codingTool === "other" && (
              <Input
                value={codingToolOther}
                onChange={(e) => setCodingToolOther(e.target.value)}
                placeholder="Please state..."
                className="bg-neutral-900 border-neutral-800 text-neutral-200"
              />
            )}
          </div>

          {/* Acquisition */}
          <div className="space-y-2">
            <Label className="text-neutral-300">How did you find us?</Label>
            <Select value={acquisitionSource} onValueChange={(v) => setAcquisitionSource(v as AcquisitionSource)}>
              <SelectTrigger className="bg-neutral-900 border-neutral-800 text-neutral-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-neutral-900 border-neutral-800">
                <SelectItem value="hackathon">Hackathon</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="founder_begged_me">Founder Begged Me</SelectItem>
                <SelectItem value="x_twitter">X / Twitter</SelectItem>
                <SelectItem value="threads">Threads</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
            {acquisitionSource === "other" && (
              <Input
                value={acquisitionOther}
                onChange={(e) => setAcquisitionOther(e.target.value)}
                placeholder="Please state..."
                className="bg-neutral-900 border-neutral-800 text-neutral-200"
              />
            )}
          </div>

          {error && (
            <p className="text-sm text-red-400 flex items-center gap-1.5">
              <AlertTriangle className="size-3.5" />
              {error}
            </p>
          )}
        </div>

        <Button
          onClick={handleSubmit}
          disabled={saving || (codingTool === "other" && !codingToolOther.trim()) || (acquisitionSource === "other" && !acquisitionOther.trim())}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white h-11"
        >
          {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : null}
          Get Started
        </Button>
      </div>
    </div>
  )
}
