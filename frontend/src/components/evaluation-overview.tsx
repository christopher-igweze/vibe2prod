"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { EvaluationReport, AIVSSScore } from "@/lib/api/types"
import { scoreColor } from "@/lib/utils"
import { CheckCircle2, XCircle, Shield, Info, HelpCircle } from "lucide-react"

const DIMENSION_LABELS: Record<string, string> = {
  security: "Security",
  reliability: "Reliability",
  maintainability: "Maintainability",
  test_quality: "Test Quality",
  performance: "Performance",
  documentation: "Documentation",
  operations: "Operations",
}

const DIMENSION_DESCRIPTIONS: Record<string, string> = {
  security: "Hardcoded secrets, injection patterns, auth gaps, crypto",
  reliability: "Error handling, health checks, graceful shutdown",
  maintainability: "Complexity, nesting depth, code duplication",
  test_quality: "Test presence, coverage, structure, naming",
  performance: "N+1 queries, unbounded fetches, missing pagination",
  documentation: "README, API docs, inline docs, changelogs",
  operations: "CI/CD, Dockerfile, structured logging, env validation",
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

const BAND_DESCRIPTIONS: Record<string, string> = {
  A: "Meets elite team standards (Google PRR, Stripe)",
  B: "Minor gaps. Deployable with monitoring.",
  C: "Significant gaps. Fix critical issues before deploy.",
  D: "Fundamental issues across multiple dimensions.",
  F: "Critical vulnerabilities or missing fundamentals.",
}

const GATE_EXPLANATION = "The quality gate is a binary pass/fail check. It verifies minimum scores per dimension and zero new critical/high findings. Profile determines the strictness."

function DimensionBar({ name, score, checksPassed, checksFailed }: {
  name: string
  score: number
  checksPassed: number
  checksFailed: number
}) {
  const color = scoreColor(score)
  const label = DIMENSION_LABELS[name] || name
  const desc = DIMENSION_DESCRIPTIONS[name]

  return (
    <div className="space-y-1 group">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1.5">
          <span className="text-[#E8ECF4]">{label}</span>
          {desc && (
            <span className="text-[#4E586E] text-xs hidden group-hover:inline transition-opacity">
              — {desc}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {checksFailed > 0 && (
            <span className="text-xs text-red-400/70">
              {checksFailed} failed
            </span>
          )}
          <span className="text-xs text-[#4E586E]">
            {checksPassed}/{checksPassed + checksFailed}
          </span>
          <span className="font-mono font-medium w-8 text-right" style={{ color }}>{score}</span>
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
  const compositeColor = scoreColor(scores?.composite ?? 0)
  const bandDesc = BAND_DESCRIPTIONS[scores?.band ?? ""] ?? ""

  // Safe access for compliance
  const asvs = evaluation.compliance?.asvs
  const nist = evaluation.compliance?.nist
  const hasCompliance = (asvs && asvs.total_requirements > 0) || (nist && nist.total > 0)

  // Safe access for failures
  const failures = quality_gate?.failures ?? []

  return (
    <Card className="forge-glass-card p-6 space-y-6">
      {/* Header + Gate Badge */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-[#E8ECF4]">Production Readiness</h2>
        {quality_gate?.passed != null && (
          quality_gate.passed ? (
            <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 gap-1">
              <CheckCircle2 className="size-3.5" />
              Gate Passed
            </Badge>
          ) : (
            <Badge className="bg-red-500/10 text-red-400 border-red-500/20 gap-1">
              <XCircle className="size-3.5" />
              Gate Failed
            </Badge>
          )
        )}
      </div>

      {/* Hero: composite score + band + gate details */}
      <div className="flex items-start gap-6">
        <div className="text-center shrink-0">
          <div className="text-5xl font-bold font-mono" style={{ color: compositeColor }}>
            {scores?.composite ?? "—"}
          </div>
          <div className="text-xs text-[#4E586E] mt-1">/ 100</div>
        </div>

        <div className="space-y-2 min-w-0">
          {/* Band */}
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold" style={{ color: compositeColor }}>
              {scores?.band ?? "?"}
            </span>
            <span className="text-[#8692A8]">{scores?.label ?? ""}</span>
          </div>
          {bandDesc && (
            <p className="text-xs text-[#4E586E]">{bandDesc}</p>
          )}

          {/* Gate details */}
          {quality_gate && !quality_gate.passed && (
            <div className="mt-1 p-3 rounded-lg bg-red-500/5 border border-red-500/10">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Info className="size-3.5 text-red-400" />
                <span className="text-xs font-medium text-red-400">
                  Quality Gate Failed ({quality_gate.profile ?? "forge-way"} profile)
                </span>
              </div>
              {failures.length > 0 ? (
                <ul className="space-y-0.5">
                  {failures.map((f, i) => (
                    <li key={i} className="text-xs text-red-400/80 flex items-start gap-1.5">
                      <span className="mt-0.5 shrink-0">-</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-red-400/60">
                  One or more dimension scores or finding thresholds did not meet the minimum requirements.
                </p>
              )}
              <p className="text-xs text-[#4E586E] mt-2">{GATE_EXPLANATION}</p>
            </div>
          )}

          {quality_gate?.passed && (
            <div className="mt-1 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
              <p className="text-xs text-emerald-400/80">
                All dimension minimums met. No new critical or high findings. Ready for production deployment.
              </p>
            </div>
          )}
        </div>

        {/* AIVSS score */}
        {aivss && aivss.score != null && aivss.score > 0 && (
          <div className="ml-auto text-center border-l border-white/[0.06] pl-6 shrink-0">
            <div className="flex items-center gap-1.5 mb-1">
              <Shield className="size-4 text-[#8692A8]" />
              <span className="text-xs text-[#8692A8] uppercase tracking-wider">AI Risk</span>
            </div>
            <div
              className="text-3xl font-bold font-mono"
              style={{ color: aivss.score >= 7 ? "#ef4444" : aivss.score >= 4 ? "#eab308" : "#22c55e" }}
            >
              {aivss.score.toFixed(1)}
            </div>
            <div className="text-xs text-[#4E586E]">/ 10</div>
            <div className="text-xs text-[#8692A8] mt-0.5">{aivss.severity}</div>
          </div>
        )}
      </div>

      {/* 7 dimension bars */}
      {scores?.dimensions && Object.keys(scores.dimensions).length > 0 && (
        <div className="space-y-3 pt-2 border-t border-white/[0.06]">
          <div className="flex items-center justify-between">
            <p className="text-xs text-[#8692A8] uppercase tracking-wider">Dimensions</p>
            <p className="text-xs text-[#4E586E]">Deterministic checks — same code = same score, every time</p>
          </div>
          {DIMENSION_ORDER.map((key) => {
            const dim = scores.dimensions[key]
            if (!dim) return null
            return (
              <DimensionBar
                key={key}
                name={key}
                score={dim.score}
                checksPassed={dim.checks_passed ?? 0}
                checksFailed={dim.checks_failed ?? 0}
              />
            )
          })}
        </div>
      )}

      {/* Compliance summary */}
      {hasCompliance && (
        <div className="pt-2 border-t border-white/[0.06]">
          <div className="flex items-center gap-1.5 mb-3">
            <p className="text-xs text-[#8692A8] uppercase tracking-wider">Standards Compliance</p>
            <HelpCircle className="size-3 text-[#4E586E]" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {asvs && asvs.total_requirements > 0 && (
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                <p className="text-xs text-[#8692A8] font-medium mb-1">OWASP ASVS</p>
                <p className="text-sm text-[#E8ECF4]">
                  Level {asvs.estimated_level ?? 0}
                </p>
                <p className="text-xs text-[#4E586E] mt-0.5">
                  {Math.round((asvs.passed / asvs.total_requirements) * 100)}% of Level 1 requirements met
                  ({asvs.passed}/{asvs.total_requirements} checks)
                </p>
              </div>
            )}
            {nist && nist.total > 0 && (
              <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                <p className="text-xs text-[#8692A8] font-medium mb-1">NIST SSDF</p>
                <p className="text-sm text-[#E8ECF4]">
                  {nist.covered}/{nist.total} practices
                </p>
                <p className="text-xs text-[#4E586E] mt-0.5">
                  Evaluated against Secure Software Development Framework
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}
