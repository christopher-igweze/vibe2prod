"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { EvaluationReport, AIVSSScore } from "@/lib/api/types"
import { scoreColor } from "@/lib/utils"
import { CheckCircle2, XCircle, Shield } from "lucide-react"

const DIMENSION_LABELS: Record<string, string> = {
  security: "Security",
  reliability: "Reliability",
  maintainability: "Maintainability",
  test_quality: "Test Quality",
  performance: "Performance",
  documentation: "Documentation",
  operations: "Operations",
}

const DIMENSION_ORDER = [
  "security",
  "reliability",
  "maintainability",
  "test_quality",
  "performance",
  "documentation",
  "operations",
]

function DimensionBar({ name, score, checksPassed, checksFailed }: {
  name: string
  score: number
  checksPassed: number
  checksFailed: number
}) {
  const color = scoreColor(score)
  const label = DIMENSION_LABELS[name] || name

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[#E8ECF4]">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#4E586E]">
            {checksPassed}/{checksPassed + checksFailed} checks
          </span>
          <span className="font-mono font-medium" style={{ color }}>{score}</span>
        </div>
      </div>
      <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${Math.max(2, score)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

export function EvaluationOverview({
  evaluation,
  aivss,
}: {
  evaluation: EvaluationReport
  aivss?: AIVSSScore | null
}) {
  const { scores, quality_gate } = evaluation
  const compositeColor = scoreColor(scores.composite)

  return (
    <Card className="forge-glass-card p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#E8ECF4]">Production Readiness</h2>
        {/* Quality gate badge */}
        {quality_gate.passed ? (
          <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1">
            <CheckCircle2 className="size-3.5" />
            Gate Passed
          </Badge>
        ) : (
          <Badge className="bg-red-500/10 text-red-400 border-red-500/20 gap-1">
            <XCircle className="size-3.5" />
            Gate Failed
          </Badge>
        )}
      </div>

      {/* Hero: composite score + band */}
      <div className="flex items-center gap-6">
        <div className="text-center">
          <div className="text-5xl font-bold font-mono" style={{ color: compositeColor }}>
            {scores.composite}
          </div>
          <div className="text-xs text-[#4E586E] mt-1">/ 100</div>
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span
              className="text-2xl font-bold"
              style={{ color: compositeColor }}
            >
              {scores.band}
            </span>
            <span className="text-[#8692A8]">{scores.label}</span>
          </div>
          <p className="text-xs text-[#4E586E]">
            Profile: {quality_gate.profile}
          </p>
          {!quality_gate.passed && quality_gate.failures.length > 0 && (
            <div className="mt-2 space-y-1">
              {quality_gate.failures.map((f, i) => (
                <p key={i} className="text-xs text-red-400">
                  {f}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* AIVSS score if present */}
        {aivss && aivss.score > 0 && (
          <div className="ml-auto text-center border-l border-white/[0.06] pl-6">
            <div className="flex items-center gap-1.5 mb-1">
              <Shield className="size-4 text-[#8692A8]" />
              <span className="text-xs text-[#8692A8] uppercase tracking-wider">AIVSS</span>
            </div>
            <div
              className="text-3xl font-bold font-mono"
              style={{ color: aivss.score >= 7 ? "#ef4444" : aivss.score >= 4 ? "#eab308" : "#22c55e" }}
            >
              {aivss.score.toFixed(1)}
            </div>
            <div className="text-xs text-[#4E586E]">/ 10 ({aivss.severity})</div>
          </div>
        )}
      </div>

      {/* 7 dimension bars */}
      <div className="space-y-3 pt-2 border-t border-white/[0.06]">
        <p className="text-xs text-[#8692A8] uppercase tracking-wider">Dimensions</p>
        {DIMENSION_ORDER.map((key) => {
          const dim = scores.dimensions[key]
          if (!dim) return null
          return (
            <DimensionBar
              key={key}
              name={key}
              score={dim.score}
              checksPassed={dim.checks_passed}
              checksFailed={dim.checks_failed}
            />
          )
        })}
      </div>

      {/* Compliance summary */}
      {evaluation.compliance && (
        <div className="pt-2 border-t border-white/[0.06]">
          <p className="text-xs text-[#8692A8] uppercase tracking-wider mb-2">Compliance</p>
          <div className="flex gap-4 text-xs">
            {evaluation.compliance.asvs && (
              <div className="text-[#8692A8]">
                OWASP ASVS: Level {evaluation.compliance.asvs.estimated_level}{" "}
                ({evaluation.compliance.asvs.level_1_percent}% of L1)
              </div>
            )}
            {evaluation.compliance.nist && (
              <div className="text-[#8692A8]">
                NIST SSDF: {evaluation.compliance.nist.practices_passing}/{evaluation.compliance.nist.practices_evaluated}
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}
