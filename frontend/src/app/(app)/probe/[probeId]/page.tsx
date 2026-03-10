"use client"

export const dynamic = "force-dynamic"

import { useEffect, useRef, useState } from "react"
import { useParams } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import {
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Shield,
  Clock,
  ArrowLeft,
  Lock,
} from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import type { ProbeDetail, ProbeFinding } from "@/lib/api/types"
import { useUserRole } from "@/hooks/use-user-role"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScoreGauge } from "@/components/score-gauge"

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

function severityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical": return "bg-red-500/20 text-red-400 border-red-500/30"
    case "high": return "bg-orange-500/20 text-orange-400 border-orange-500/30"
    case "medium": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
    case "low": return "bg-blue-500/20 text-blue-400 border-blue-500/30"
    default: return "bg-[#131825] text-[#8692A8] border-white/[0.06]"
  }
}

function severityBadge(severity: string) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${severityColor(severity)}`}>
      {severity}
    </span>
  )
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "--"
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}

// ---------------------------------------------------------------------------
// Finding row (expandable)
// ---------------------------------------------------------------------------

function FindingRow({ finding }: { finding: ProbeFinding }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-white/[0.04] last:border-b-0">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
      >
        {expanded ? (
          <ChevronDown className="size-4 text-[#4E586E] shrink-0" />
        ) : (
          <ChevronRight className="size-4 text-[#4E586E] shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {severityBadge(finding.severity)}
            <span className="text-sm text-[#E8ECF4] truncate">{finding.title}</span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-xs text-[#8692A8]">
            <span>{finding.category}</span>
            {finding.owasp_category && <span>{finding.owasp_category}</span>}
            <span>{Math.round(finding.confidence * 100)}% confidence</span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pl-11 space-y-3">
          <p className="text-sm text-[#8692A8]">{finding.description}</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="rounded-md bg-[#0B0F19] border border-white/[0.04] p-3 space-y-1">
              <p className="text-[#4E586E] uppercase tracking-wider text-[10px]">URL Tested</p>
              <p className="text-[#E8ECF4] break-all">{finding.url_tested}</p>
            </div>
            <div className="rounded-md bg-[#0B0F19] border border-white/[0.04] p-3 space-y-1">
              <p className="text-[#4E586E] uppercase tracking-wider text-[10px]">Method</p>
              <p className="text-[#E8ECF4]">{finding.method}</p>
            </div>
          </div>

          {finding.evidence && (
            <div className="rounded-md bg-[#0B0F19] border border-white/[0.04] p-3 space-y-1">
              <p className="text-[#4E586E] uppercase tracking-wider text-[10px]">Evidence</p>
              <pre className="text-xs text-[#E8ECF4] whitespace-pre-wrap font-mono break-all">{finding.evidence}</pre>
            </div>
          )}

          {finding.request_summary && (
            <div className="rounded-md bg-[#0B0F19] border border-white/[0.04] p-3 space-y-1">
              <p className="text-[#4E586E] uppercase tracking-wider text-[10px]">Request</p>
              <pre className="text-xs text-[#8692A8] whitespace-pre-wrap font-mono break-all">{finding.request_summary}</pre>
            </div>
          )}

          {finding.response_summary && (
            <div className="rounded-md bg-[#0B0F19] border border-white/[0.04] p-3 space-y-1">
              <p className="text-[#4E586E] uppercase tracking-wider text-[10px]">Response</p>
              <pre className="text-xs text-[#8692A8] whitespace-pre-wrap font-mono break-all">{finding.response_summary}</pre>
            </div>
          )}

          <div className="flex items-center gap-3 text-xs text-[#4E586E]">
            {finding.cwe_id && <span>CWE: {finding.cwe_id}</span>}
            {finding.false_positive && (
              <Badge variant="outline" className="text-[10px] border-yellow-500/30 text-yellow-400">
                Possible False Positive
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ProbeResultPage() {
  const params = useParams<{ probeId: string }>()
  const { getToken } = useAuth()
  const probeId = params.probeId

  const { profile } = useUserRole()
  const isOnboarded = !!profile?.onboarding_complete

  const [probe, setProbe] = useState<ProbeDetail | null>(null)
  const [findings, setFindings] = useState<ProbeFinding[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Polling for probe status
  useEffect(() => {
    let cancelled = false
    let failures = 0

    const poll = async () => {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ProbeDetail>(`/api/probe/${probeId}`, { token })
        failures = 0
        if (cancelled) return

        setProbe(data)

        if (data.status === "completed" || data.status === "failed" || data.status === "cancelled") {
          if (pollRef.current) clearInterval(pollRef.current)
          setLoading(false)

          // Fetch findings on completion
          if (data.status === "completed") {
            try {
              const f = await apiFetch<ProbeFinding[]>(`/api/probe/${probeId}/findings`, { token })
              if (!cancelled) setFindings(f)
            } catch {
              // Findings fetch is non-critical
            }
          }
        } else {
          setLoading(false)
        }
      } catch {
        failures++
        if (failures >= 5) {
          setError("Lost connection to server. Please refresh the page.")
          if (pollRef.current) clearInterval(pollRef.current)
          setLoading(false)
        }
      }
    }

    poll()
    pollRef.current = setInterval(poll, 5000)

    return () => {
      cancelled = true
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [probeId, getToken])

  // ---------------------------------------------------------------------------
  // Loading state
  // ---------------------------------------------------------------------------

  if (loading && !probe) {
    return (
      <div className="max-w-3xl mx-auto flex items-center justify-center py-16">
        <Loader2 className="size-8 text-forge-emerald animate-spin" />
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Error state
  // ---------------------------------------------------------------------------

  if (error) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">{error}</p>
              <Button variant="outline" size="sm" asChild>
                <Link href="/dashboard">
                  <ArrowLeft className="size-4 mr-1.5" />
                  Back to Dashboard
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!probe) return null

  const isRunning = probe.status === "pending" || probe.status === "running"
  const isFailed = probe.status === "failed"
  const isCompleted = probe.status === "completed"

  // ---------------------------------------------------------------------------
  // Running state
  // ---------------------------------------------------------------------------

  if (isRunning) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <div className="flex flex-col items-center justify-center py-12 space-y-8">
          <Loader2 className="size-10 text-forge-emerald animate-spin" />
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">
              Security probe in progress...
            </h1>
            <p className="text-[#8692A8] text-sm">
              Testing{" "}
              <span className="text-[#E8ECF4] font-medium">{probe.target_url}</span>
              {" "}for vulnerabilities.
            </p>
            <p className="text-[#4E586E] text-xs mt-2">
              You can leave and check back from the{" "}
              <Link
                href="/dashboard"
                className="text-forge-emerald hover:text-forge-emerald/80 hover:underline"
              >
                dashboard
              </Link>
              .
            </p>
          </div>

          {/* Stage indicators */}
          <div className="w-full max-w-md space-y-3">
            {[
              { key: "connecting", label: "Connecting", desc: "Establishing connection to target" },
              { key: "probing", label: "Probing", desc: "Running security tests against target" },
            ].map((stage, i) => {
              const isActive = probe.status === "pending" ? i === 0 : i === 1
              const isComplete = probe.status === "running" && i === 0

              return (
                <div
                  key={stage.key}
                  className={`flex items-center gap-3 rounded-lg px-4 py-3 transition-all ${
                    isActive
                      ? "bg-forge-emerald/10 border border-forge-emerald/30"
                      : isComplete
                        ? "bg-[#131825]/80 border border-white/[0.06]"
                        : "bg-[#131825]/40 border border-transparent"
                  }`}
                >
                  {isComplete ? (
                    <Shield className="size-5 text-forge-emerald shrink-0" />
                  ) : isActive ? (
                    <Loader2 className="size-5 text-forge-emerald animate-spin shrink-0" />
                  ) : (
                    <div className="size-5 rounded-full border border-[#4E586E] shrink-0" />
                  )}
                  <div>
                    <p className={`text-sm font-medium ${isActive ? "text-forge-emerald" : isComplete ? "text-neutral-300" : "text-neutral-500"}`}>
                      {stage.label}
                    </p>
                    <p className={`text-xs mt-0.5 ${isActive ? "text-[#8692A8]" : "text-[#4E586E]"}`}>
                      {stage.desc}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Failed state
  // ---------------------------------------------------------------------------

  if (isFailed) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-6">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold text-red-300">Probe Failed</h2>
                <p className="text-sm text-[#8692A8] mt-1">
                  The security probe for {probe.target_url} encountered an error.
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href="/dashboard">
                    <ArrowLeft className="size-4 mr-1.5" />
                    Dashboard
                  </Link>
                </Button>
                <Button size="sm" asChild className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
                  <Link href="/probe/new">Try Again</Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Completed state
  // ---------------------------------------------------------------------------

  if (!isCompleted) return null

  const severityCounts = [
    { label: "Critical", count: probe.critical_count, color: "bg-red-500/20 text-red-400" },
    { label: "High", count: probe.high_count, color: "bg-orange-500/20 text-orange-400" },
    { label: "Medium", count: probe.medium_count, color: "bg-yellow-500/20 text-yellow-400" },
    { label: "Low", count: probe.low_count, color: "bg-blue-500/20 text-blue-400" },
  ]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/dashboard" className="text-[#4E586E] hover:text-[#8692A8] transition-colors">
              <ArrowLeft className="size-4" />
            </Link>
            <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">Probe Results</h1>
          </div>
          <p className="text-sm text-[#8692A8] break-all">{probe.target_url}</p>
        </div>
        <Button asChild className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
          <Link href="/probe/new">New Probe</Link>
        </Button>
      </div>

      {/* Score + Summary row */}
      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-6">
        {/* Score gauge */}
        {probe.probe_score !== null && (
          <Card className="forge-glass-card p-6 flex items-center justify-center">
            <ScoreGauge score={probe.probe_score} label="Probe Score" size={140} />
          </Card>
        )}

        {/* Summary stats */}
        <Card className="forge-glass-card p-6 space-y-4">
          <div className="flex items-center gap-2 text-sm text-[#8692A8]">
            <Shield className="size-4 text-forge-emerald" />
            <span>{probe.total_findings} finding{probe.total_findings !== 1 ? "s" : ""} detected</span>
          </div>

          {/* Severity badges */}
          <div className="flex flex-wrap gap-2">
            {severityCounts.map((s) => (
              <div
                key={s.label}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${s.color}`}
              >
                <span className="text-xs font-medium">{s.count}</span>
                <span className="text-xs">{s.label}</span>
              </div>
            ))}
          </div>

          {/* Duration */}
          <div className="flex items-center gap-4 text-xs text-[#4E586E]">
            <div className="flex items-center gap-1">
              <Clock className="size-3" />
              <span>Duration: {formatDuration(probe.duration_seconds)}</span>
            </div>
            {probe.completed_at && (
              <span>
                Completed: {new Date(probe.completed_at).toLocaleString("en-US", {
                  month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                })}
              </span>
            )}
          </div>
        </Card>
      </div>

      {/* Findings list */}
      {!isOnboarded ? (
        <Card className="forge-glass-card p-8 text-center space-y-4">
          <Lock className="size-8 text-forge-emerald mx-auto" />
          <div>
            <p className="text-sm text-[#E8ECF4] font-medium">
              {probe.total_findings} finding{probe.total_findings !== 1 ? "s" : ""} detected
            </p>
            <p className="text-xs text-[#8692A8] mt-1">
              Complete onboarding to see detailed findings, evidence, and remediation guidance.
            </p>
          </div>
          <Button asChild className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
            <Link href="/onboarding">Complete Onboarding</Link>
          </Button>
        </Card>
      ) : findings.length > 0 ? (
        <Card className="forge-glass-card overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <h2 className="text-sm font-semibold text-[#E8ECF4]">
              Findings ({findings.length})
            </h2>
          </div>
          <div>
            {findings.map((finding) => (
              <FindingRow key={finding.id} finding={finding} />
            ))}
          </div>
        </Card>
      ) : (
        <Card className="forge-glass-card p-8 text-center">
          <Shield className="size-8 text-forge-emerald mx-auto mb-3" />
          <p className="text-sm text-[#E8ECF4] font-medium">No vulnerabilities found</p>
          <p className="text-xs text-[#8692A8] mt-1">Your application passed all selected security tests.</p>
        </Card>
      )}
    </div>
  )
}
