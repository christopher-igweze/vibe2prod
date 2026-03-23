"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import type { DiscoveryReport, Severity, EvaluationReport, AIVSSScore } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScoreGauge } from "@/components/score-gauge"
import { EvaluationOverview } from "@/components/evaluation-overview"
import { FailedChecksTable } from "@/components/failed-checks-table"

import { ReportHeader } from "./_components/report-header"
import { SeveritySummary } from "./_components/severity-summary"
import { ArchitectureContext } from "./_components/architecture-context"
import { FindingsTable } from "./_components/findings-table"
import { RemediationPlan } from "./_components/remediation-plan"
import { formatCharge, formatDuration } from "./_components/report-utils"

/* ---------- types ---------- */

interface ScanDetail {
  id: string
  status: string
  repo_url?: string
  repo_name?: string
  health_score?: number | null
  security_score?: number | null
  reliability_score?: number | null
  scalability_score?: number | null
  report_data?: {
    discovery_report?: DiscoveryReport
    evaluation?: EvaluationReport
    aivss_score?: AIVSSScore
  }
}

/* ---------- sidebar ---------- */

function ReportSidebar({
  scan,
  report,
  actionableCount,
}: {
  scan: ScanDetail
  report: DiscoveryReport
  actionableCount: number
}) {
  const formattedDate = new Date(report.generated_at).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })

  const scores = [
    { label: "Health", value: scan.health_score },
    { label: "Security", value: scan.security_score },
    { label: "Reliability", value: scan.reliability_score },
    { label: "Scalability", value: scan.scalability_score },
  ]
  const hasScores = scores.some((s) => s.value != null && s.value !== null)

  return (
    <aside className="w-[280px] shrink-0 space-y-5 sticky top-6 self-start hidden lg:block">
      {/* Quick stats */}
      <Card className="forge-glass-card p-4 space-y-3">
        <div>
          <p className="text-sm font-medium text-[#E8ECF4] truncate">
            {scan.repo_name || scan.repo_url}
          </p>
          <p className="text-xs text-[#4E586E] mt-0.5">{formattedDate}</p>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="outline" className="border-white/[0.08] text-[#8692A8]">
            {actionableCount} findings
          </Badge>
          <Badge variant="outline" className="border-white/[0.08] text-[#8692A8]">
            {report.loc_total.toLocaleString()} LOC
          </Badge>
          <Badge variant="outline" className="border-white/[0.08] text-[#8692A8]">
            {report.file_count} files
          </Badge>
          <Badge variant="outline" className="border-white/[0.08] text-[#8692A8]">
            {formatDuration(report.duration_seconds)}
          </Badge>
          {report.cost_usd > 0 && (
            <Badge variant="outline" className="border-forge-emerald/30 text-forge-emerald">
              {formatCharge(report.cost_usd)}
            </Badge>
          )}
        </div>
      </Card>

      {/* Score gauges */}
      {hasScores && (
        <Card className="forge-glass-card p-4" data-tour="score-gauges">
          <p className="text-xs text-[#8692A8] uppercase tracking-wider mb-3">Scores</p>
          <div className="grid grid-cols-2 gap-3">
            {scores.map((s) =>
              s.value != null ? (
                <ScoreGauge key={s.label} score={s.value} label={s.label} size={100} />
              ) : null
            )}
          </div>
        </Card>
      )}

      {/* Jump links */}
      <Card className="forge-glass-card p-4">
        <p className="text-xs text-[#8692A8] uppercase tracking-wider mb-2">Sections</p>
        <nav className="space-y-1">
          {[
            { id: "evaluation", label: "Evaluation" },
            { id: "summary", label: "Summary" },
            { id: "architecture", label: "Architecture" },
            { id: "findings", label: "Findings" },
            { id: "remediation", label: "Remediation" },
          ].map((link) => (
            <a
              key={link.id}
              href={`#${link.id}`}
              className="block text-sm text-[#8692A8] hover:text-forge-emerald transition-colors py-1"
            >
              {link.label}
            </a>
          ))}
        </nav>
      </Card>
    </aside>
  )
}

/* ---------- page ---------- */

export default function ReportPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const { getToken } = useAuth()

  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanDetail>(
          `/api/user/scans/${scanId}`,
          { token },
        )
        setScan(data)
      } catch {
        setError("Failed to load scan report.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scanId, getToken])

  const report = scan?.report_data?.discovery_report ?? null

  // Split findings: actionable vs intentional/informational
  const findings = report?.findings ?? []
  const actionableFindings = findings.filter(
    (f) => f.intent_signal !== "intentional" && f.actionability !== "informational"
  )
  const intentionalFindings = findings.filter(
    (f) => f.intent_signal === "intentional" || f.actionability === "informational"
  )

  // Recompute severity counts from actionable findings only
  const adjustedSeverity: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const f of actionableFindings) {
    if (f.severity in adjustedSeverity) adjustedSeverity[f.severity]++
  }

  /* ---------- loading / error states ---------- */

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="size-6 animate-spin text-[#4E586E]" />
      </div>
    )
  }

  if (error || !scan) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="size-8 text-red-400 mx-auto" />
        <p className="text-[#8692A8]">{error || "Scan not found."}</p>
        <Link href="/dashboard">
          <Button variant="outline" className="border-white/[0.08]">
            <ArrowLeft className="size-4 mr-1" /> Back to Dashboard
          </Button>
        </Link>
      </div>
    )
  }

  if (scan.status !== "completed") {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <Loader2 className="size-8 animate-spin text-[#4E586E] mx-auto" />
        <p className="text-[#8692A8]">
          Scan is {scan.status}. Waiting for results...
        </p>
        <Link href={`/scan/${scanId}`}>
          <Button variant="outline" className="border-white/[0.08]">
            View Progress
          </Button>
        </Link>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="size-8 text-yellow-400 mx-auto" />
        <p className="text-[#8692A8]">
          No discovery report data available for this scan.
        </p>
        <Link href="/dashboard">
          <Button variant="outline" className="border-white/[0.08]">
            <ArrowLeft className="size-4 mr-1" /> Back to Dashboard
          </Button>
        </Link>
      </div>
    )
  }

  /* ---------- render report ---------- */

  return (
    <div className="max-w-7xl mx-auto pb-16">
      {/* Navigation + Header */}
      <div className="space-y-4 mb-6">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="text-[#8692A8] hover:text-[#E8ECF4] -ml-2">
            <ArrowLeft className="size-4 mr-1" /> Dashboard
          </Button>
        </Link>

        <ReportHeader
          report={report}
          repoName={scan.repo_name}
          scanId={scanId}
          actionableCount={actionableFindings.length}
          evaluation={scan.report_data?.evaluation}
          aivss={scan.report_data?.aivss_score}
        />
      </div>

      {/* Two-column layout */}
      <div className="flex gap-6">
        {/* Sidebar */}
        <ReportSidebar
          scan={scan}
          report={report}
          actionableCount={actionableFindings.length}
        />

        {/* Main content */}
        <main className="flex-1 min-w-0 space-y-6">
          {/* v3 Evaluation Overview */}
          {scan.report_data?.evaluation && (
            <section id="evaluation">
              <EvaluationOverview
                evaluation={scan.report_data.evaluation}
                aivss={scan.report_data.aivss_score}
              />
            </section>
          )}

          {/* Failed checks detail */}
          {scan.report_data?.evaluation?.deterministic_checks && (
            <FailedChecksTable checks={scan.report_data.evaluation.deterministic_checks} />
          )}

          {/* Actionability summary */}
          <section id="summary">
            <SeveritySummary
              actionabilitySummary={report.actionability_summary}
            />
          </section>

          {/* Architecture Context */}
          {report.codebase_map && (
            <section id="architecture">
              <ArchitectureContext
                map={report.codebase_map}
                findings={actionableFindings}
              />
            </section>
          )}

          {/* Findings Table */}
          {findings.length > 0 && (
            <section id="findings" data-tour="findings-table">
              <FindingsTable
                actionableFindings={actionableFindings}
                intentionalFindings={intentionalFindings}
              />
            </section>
          )}

          {/* Remediation Plan */}
          {report.remediation_plan && report.remediation_plan.items.length > 0 && (
            <section id="remediation" data-tour="fix-button">
              <RemediationPlan plan={report.remediation_plan} />
            </section>
          )}

          {/* Empty state */}
          {actionableFindings.length === 0 && intentionalFindings.length === 0 && (
            <Card className="p-12 text-center">
              <p className="text-[#8692A8]">No findings detected. Your codebase looks clean!</p>
            </Card>
          )}
        </main>
      </div>
    </div>
  )
}
