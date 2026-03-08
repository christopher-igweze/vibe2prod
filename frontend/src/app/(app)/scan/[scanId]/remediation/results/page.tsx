"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import {
  Loader2,
  AlertCircle,
  ArrowLeft,
  ExternalLink,
  Download,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Clock,
  Zap,
  ListChecks,
  RotateCcw,
  Search,
} from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import type { ScanFixStatus, FixResponse } from "@/lib/api/types"
import { openRemediationPdfReport } from "@/lib/report/remediation-to-pdf-html"
import { ScoreGauge } from "@/components/score-gauge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

/* ---------- helpers ---------- */

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "--"
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

function formatCost(cost: number | null): string {
  if (cost === null) return "--"
  return `$${cost.toFixed(2)}`
}

function severityColor(severity: string): string {
  switch (severity) {
    case "critical":
      return "bg-red-500/15 text-red-400 border-red-500/30"
    case "high":
      return "bg-orange-500/15 text-orange-400 border-orange-500/30"
    case "medium":
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30"
    case "low":
      return "bg-blue-500/15 text-blue-400 border-blue-500/30"
    default:
      return "bg-neutral-500/15 text-neutral-400 border-neutral-500/30"
  }
}

function scoreBarColor(score: number): string {
  if (score >= 70) return "bg-emerald-500"
  if (score >= 40) return "bg-yellow-500"
  return "bg-red-500"
}

/* ---------- collapsible section ---------- */

function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <Card className="bg-[#131825]/80 backdrop-blur-sm border-white/[0.06]">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left"
      >
        <span className="font-semibold text-neutral-100">{title}</span>
        {open ? (
          <ChevronDown className="size-4 text-neutral-400" />
        ) : (
          <ChevronRight className="size-4 text-neutral-400" />
        )}
      </button>
      {open && <CardContent className="pt-0">{children}</CardContent>}
    </Card>
  )
}

/* ---------- component ---------- */

export default function RemediationResultsPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()
  const scanId = params.scanId

  const [status, setStatus] = useState<ScanFixStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)

  async function handleRetryRemediation() {
    setRetrying(true)
    try {
      const token = (await getToken()) ?? undefined
      await apiFetch<FixResponse>(`/api/fix-scan/${scanId}`, {
        method: "POST",
        token,
      })
      router.push(`/scan/${scanId}/remediation`)
    } catch {
      setRetrying(false)
    }
  }

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanFixStatus>(
          `/api/fix-scan/${scanId}/status`,
          { token },
        )
        setStatus(data)

        // If still running or pending, redirect to progress page
        if (data.status === "pending" || data.status === "running") {
          router.push(`/scan/${scanId}/remediation`)
          return
        }
      } catch {
        setError("Failed to load remediation results.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scanId, getToken, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="size-6 animate-spin text-neutral-500" />
      </div>
    )
  }

  if (error || !status) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="size-8 text-red-400 mx-auto" />
        <p className="text-neutral-400">{error || "Results not found."}</p>
        <Link href={`/scan/${scanId}/report`}>
          <Button variant="outline" className="border-white/[0.06]">
            <ArrowLeft className="size-4 mr-1" /> Back to Report
          </Button>
        </Link>
      </div>
    )
  }

  const readiness = status.readiness_report
  const overallScore = status.readiness_score ?? readiness?.overall_score ?? 0
  const findingsFixed = status.findings_fixed ?? 0
  const findingsDeferred = status.findings_deferred ?? 0
  const totalFindings = findingsFixed + findingsDeferred
  const isFailed = status.status === "failed"

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      {/* Navigation */}
      <Link href={`/scan/${scanId}/report`}>
        <Button
          variant="ghost"
          size="sm"
          className="text-neutral-400 hover:text-neutral-200 -ml-2"
        >
          <ArrowLeft className="size-4 mr-1" /> Discovery Report
        </Button>
      </Link>

      {/* ── Hero Section ── */}
      <div className="text-center space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-neutral-100 font-[family-name:var(--font-heading)]">
            Production Readiness Report
          </h1>
          <div className="flex items-center justify-center gap-2 mt-3">
            <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
              Discovery ✓
            </Badge>
            {isFailed ? (
              <Badge className="bg-red-500/15 text-red-400 border-red-500/30">
                Remediation ✗
              </Badge>
            ) : (
              <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                Remediation ✓
              </Badge>
            )}
          </div>
        </div>

        <ScoreGauge score={overallScore} label="Production Readiness" size={180} />

        <p className={`text-sm max-w-2xl mx-auto leading-relaxed ${isFailed ? "text-red-400" : "text-neutral-400"}`}>
          {isFailed
            ? (status.error || status.summary || "Remediation failed.")
            : (readiness?.investor_summary || status.summary || "")}
        </p>
      </div>

      {/* ── Category Breakdown ── */}
      {readiness?.category_scores && readiness.category_scores.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-100 mb-4 font-[family-name:var(--font-heading)]">
            Category Breakdown
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {readiness.category_scores.map((cat) => (
              <Card
                key={cat.name}
                className="bg-[#131825]/80 backdrop-blur-sm border-white/[0.06]"
              >
                <CardContent className="py-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-neutral-200">
                      {cat.name}
                    </span>
                    <span className="text-sm font-[family-name:var(--font-code)] text-neutral-400">
                      {cat.score}/100
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-[#131825] overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${scoreBarColor(cat.score)}`}
                      style={{ width: `${cat.score}%` }}
                    />
                  </div>
                  {cat.details && (
                    <p className="text-xs text-neutral-500">{cat.details}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ── Remediation Stats ── */}
      <div>
        <h2 className="text-lg font-semibold text-neutral-100 mb-4 font-[family-name:var(--font-heading)]">
          Remediation Stats
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {/* Findings */}
          <Card className="bg-[#131825]/80 backdrop-blur-sm border-white/[0.06]">
            <CardContent className="py-4 text-center space-y-1">
              <ListChecks className="size-5 text-neutral-400 mx-auto" />
              <p className="text-xs text-neutral-500">Findings</p>
              <p className="text-lg font-bold text-neutral-200">
                {totalFindings}
              </p>
              <div className="flex items-center justify-center gap-2 text-xs">
                <span className="text-emerald-400">{findingsFixed} fixed</span>
                <span className="text-neutral-600">/</span>
                <span className="text-yellow-400">{findingsDeferred} deferred</span>
              </div>
            </CardContent>
          </Card>

          {/* Agent Stats */}
          <Card className="bg-[#131825]/80 backdrop-blur-sm border-white/[0.06]">
            <CardContent className="py-4 text-center space-y-1">
              <Zap className="size-5 text-neutral-400 mx-auto" />
              <p className="text-xs text-neutral-500">Agent Invocations</p>
              <p className="text-lg font-bold text-neutral-200">
                {status.agent_invocations ?? "--"}
              </p>
            </CardContent>
          </Card>

          {/* Duration & Cost */}
          <Card className="bg-[#131825]/80 backdrop-blur-sm border-white/[0.06]">
            <CardContent className="py-4 text-center space-y-1">
              <Clock className="size-5 text-neutral-400 mx-auto" />
              <p className="text-xs text-neutral-500">Duration</p>
              <p className="text-lg font-bold text-neutral-200">
                {formatDuration(status.duration_seconds)}
              </p>
              <p className="text-xs text-neutral-500">
                {formatCost(status.cost_usd)}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Findings Detail ── */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-neutral-100 font-[family-name:var(--font-heading)]">
          Findings Detail
        </h2>

        {/* Fixed findings */}
        <CollapsibleSection title={`Fixed Findings (${findingsFixed})`} defaultOpen>
          {status.summary ? (
            <p className="text-sm text-neutral-400 leading-relaxed">
              {status.summary}
            </p>
          ) : (
            <p className="text-sm text-neutral-500">
              No detailed fix summary available yet.
            </p>
          )}
        </CollapsibleSection>

        {/* Deferred / Debt Items */}
        {readiness?.debt_items && readiness.debt_items.length > 0 && (
          <CollapsibleSection title={`Deferred Items (${readiness.debt_items.length})`}>
            <div className="space-y-3">
              {readiness.debt_items.map((item, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 border-b border-white/[0.06] pb-3 last:border-0 last:pb-0"
                >
                  <Badge className={severityColor(item.severity)}>
                    {item.severity.toUpperCase()}
                  </Badge>
                  <div>
                    <p className="text-sm font-medium text-neutral-200">
                      {item.title}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {item.description}
                    </p>
                    {item.reason_deferred && (
                      <p className="text-xs text-neutral-600 mt-0.5">
                        Deferred: {item.reason_deferred}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CollapsibleSection>
        )}

        {/* Recommendations */}
        {readiness?.recommendations && readiness.recommendations.length > 0 && (
          <CollapsibleSection title="Recommendations">
            <ul className="space-y-2">
              {readiness.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-neutral-400">
                  <CheckCircle2 className="size-4 text-emerald-400 mt-0.5 shrink-0" />
                  {rec}
                </li>
              ))}
            </ul>
          </CollapsibleSection>
        )}
      </div>

      {/* ── Actions ── */}
      <div className="flex items-center justify-center gap-3 pt-4 flex-wrap">
        {/* Retry Remediation — always available */}
        <Button
          className={isFailed
            ? "bg-emerald-600 hover:bg-emerald-700 text-white"
            : "border-white/[0.06] text-neutral-300"}
          variant={isFailed ? "default" : "outline"}
          onClick={handleRetryRemediation}
          disabled={retrying}
        >
          {retrying ? (
            <Loader2 className="size-4 mr-1.5 animate-spin" />
          ) : (
            <RotateCcw className="size-4 mr-1.5" />
          )}
          {isFailed ? "Retry Remediation" : "Re-run Remediation"}
        </Button>

        {status.pr_url && (
          <Button asChild className="bg-emerald-600 hover:bg-emerald-700 text-white">
            <a href={status.pr_url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="size-4 mr-1.5" />
              View Pull Request
            </a>
          </Button>
        )}

        <Button variant="outline" className="border-white/[0.06]" asChild>
          <Link href={`/scan/${scanId}/report`}>
            <ArrowLeft className="size-4 mr-1.5" />
            Discovery Report
          </Link>
        </Button>

        <Button
          variant="outline"
          className="border-white/[0.06] text-neutral-300"
          onClick={() => openRemediationPdfReport(status)}
        >
          <Download className="size-4 mr-1.5" />
          Download Report
        </Button>

        {/* New Scan — go back to dashboard */}
        <Button variant="outline" className="border-white/[0.06] text-neutral-300" asChild>
          <Link href="/dashboard">
            <Search className="size-4 mr-1.5" />
            New Scan
          </Link>
        </Button>
      </div>
    </div>
  )
}
