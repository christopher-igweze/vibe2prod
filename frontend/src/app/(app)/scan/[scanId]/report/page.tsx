"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeHighlight from "rehype-highlight"
import {
  Shield,
  Heart,
  Zap,
  TrendingUp,
  Download,
  ArrowLeft,
  FileCode,
  ChevronRight,
  Loader2,
  AlertCircle,
} from "lucide-react"

import { apiFetch, ApiError } from "@/lib/api/client"
import type {
  Tier1Finding,
  Actionability,
  ReportArtifact,
} from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { Separator } from "@/components/ui/separator"

/* ---------- types ---------- */

interface ScanDetail {
  id: string
  status: string
  health_score: number | null
  security_score: number | null
  reliability_score: number | null
  scalability_score: number | null
  report_data: {
    findings: Array<{
      id: string
      title: string
      description: string
      category: string
      severity: string
      file_path: string
      line_number: number | null
      code_snippet?: string
    }>
    tier1?: {
      summary?: {
        counts?: {
          by_actionability?: Record<string, number>
        }
        strengths?: string[]
        next_steps?: string[]
      }
    }
  } | null
  repo_name?: string
  repo_url?: string
}

interface ReportData {
  scores: {
    health_score: number
    security_score: number
    reliability_score: number
    scalability_score: number
  }
  findings: Tier1Finding[]
  markdownContent: string
}

/* ---------- helpers ---------- */

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400"
  if (score >= 60) return "text-yellow-400"
  return "text-red-400"
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-emerald-500/10 border-emerald-500/20"
  if (score >= 60) return "bg-yellow-500/10 border-yellow-500/20"
  return "bg-red-500/10 border-red-500/20"
}

function scoreBarBg(score: number): string {
  if (score >= 80) return "bg-emerald-500"
  if (score >= 60) return "bg-yellow-500"
  return "bg-red-500"
}

const ACTIONABILITY_CONFIG: Record<
  Actionability,
  { label: string; accent: string; badgeBg: string; order: number }
> = {
  must_fix: {
    label: "Must Fix",
    accent: "border-l-red-500",
    badgeBg: "bg-red-500/15 text-red-400 border-red-500/25",
    order: 0,
  },
  should_fix: {
    label: "Should Fix",
    accent: "border-l-orange-500",
    badgeBg: "bg-orange-500/15 text-orange-400 border-orange-500/25",
    order: 1,
  },
  consider: {
    label: "Consider",
    accent: "border-l-yellow-500",
    badgeBg: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
    order: 2,
  },
  informational: {
    label: "Informational",
    accent: "border-l-blue-500",
    badgeBg: "bg-blue-500/15 text-blue-400 border-blue-500/25",
    order: 3,
  },
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/25",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/25",
  medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
  low: "bg-blue-500/15 text-blue-400 border-blue-500/25",
}

function groupByActionability(
  findings: Tier1Finding[]
): Record<Actionability, Tier1Finding[]> {
  const groups: Record<Actionability, Tier1Finding[]> = {
    must_fix: [],
    should_fix: [],
    consider: [],
    informational: [],
  }
  for (const f of findings) {
    const key = f.actionability || "informational"
    groups[key].push(f)
  }
  return groups
}

/**
 * Parse findings from the markdown report content.
 * Looks for structured data in the report — falls back to empty if not parseable.
 */
function parseFindingsFromMarkdown(md: string): Tier1Finding[] {
  // The markdown report embeds a JSON findings block fenced as ```json ... ```
  // after a "## Findings Data" heading. Try to extract it.
  const jsonBlockPattern = /```json\s*\n(\[[\s\S]*?\])\s*\n```/
  const match = md.match(jsonBlockPattern)
  if (match) {
    try {
      return JSON.parse(match[1]) as Tier1Finding[]
    } catch {
      // fall through
    }
  }
  return []
}

/**
 * Parse scores from markdown report if available.
 */
function parseScoresFromMarkdown(md: string): ReportData["scores"] | null {
  const scorePattern = /```json\s*\n(\{[\s\S]*?"health_score"[\s\S]*?\})\s*\n```/
  const match = md.match(scorePattern)
  if (match) {
    try {
      return JSON.parse(match[1]) as ReportData["scores"]
    } catch {
      // fall through
    }
  }
  return null
}

/* ---------- component ---------- */

export default function ReportPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()

  const scanId = params.scanId

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [report, setReport] = useState<ReportData | null>(null)

  const fetchReport = useCallback(async () => {
    try {
      const token = await getToken()
      if (!token) {
        router.push("/dashboard")
        return
      }

      // Fetch scan detail (structured data) and markdown artifact in parallel
      const [scanDetail, artifact] = await Promise.all([
        apiFetch<ScanDetail>(`/api/user/scans/${scanId}`, { token }),
        apiFetch<ReportArtifact>(
          `/api/report-artifacts/${scanId}?artifact_type=markdown`,
          { token }
        ).catch(() => null),
      ])

      // Scores from structured data
      const scores = {
        health_score: scanDetail.health_score ?? 0,
        security_score: scanDetail.security_score ?? 0,
        reliability_score: scanDetail.reliability_score ?? 0,
        scalability_score: scanDetail.scalability_score ?? 0,
      }

      // Findings from report_data
      const rawFindings = scanDetail.report_data?.findings ?? []
      const findings: Tier1Finding[] = rawFindings.map((f) => ({
        check_id: f.id || "",
        title: f.title,
        description: f.description,
        category: (f.category || "security") as Tier1Finding["category"],
        severity: (f.severity || "medium") as Tier1Finding["severity"],
        status: "fail" as const,
        confidence: 1,
        actionability: "should_fix" as const,
        data_flow: "",
        pattern_id: "",
        pattern_slug: "",
        engine: "",
        file_path: f.file_path || "",
        line_number: f.line_number,
        evidence: f.code_snippet || "",
        why_it_matters: "",
        suggested_fix: "",
      }))

      // Markdown content
      let markdownContent = ""
      if (artifact) {
        markdownContent =
          artifact.content_encoding === "base64"
            ? atob(artifact.content)
            : artifact.content
      }

      setReport({ scores, findings, markdownContent })
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          router.push("/dashboard")
          return
        }
        setError(err.detail)
      } else {
        setError("Failed to load report")
      }
    } finally {
      setLoading(false)
    }
  }, [scanId, getToken, router])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="size-6 animate-spin text-neutral-400" />
        <span className="ml-3 text-neutral-400">Loading report...</span>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="space-y-4">
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">{error || "Report not available"}</p>
              <Button variant="outline" size="sm" asChild>
                <Link href="/dashboard">
                  <ArrowLeft className="size-4" />
                  Back to Dashboard
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { scores, findings, markdownContent } = report
  const grouped = groupByActionability(findings)
  const actionabilityOrder: Actionability[] = [
    "must_fix",
    "should_fix",
    "consider",
    "informational",
  ]

  const actionabilityCounts = actionabilityOrder.map((a) => ({
    key: a,
    ...ACTIONABILITY_CONFIG[a],
    count: grouped[a].length,
  }))

  return (
    <div className="space-y-8">
      {/* back nav */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/scan/${scanId}`}>
            <ArrowLeft className="size-4" />
            Back to Scan
          </Link>
        </Button>
      </div>

      {/* score dashboard */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <ScoreCard label="Health" score={scores.health_score} icon={Heart} />
        <ScoreCard label="Security" score={scores.security_score} icon={Shield} />
        <ScoreCard
          label="Reliability"
          score={scores.reliability_score}
          icon={Zap}
        />
        <ScoreCard
          label="Scalability"
          score={scores.scalability_score}
          icon={TrendingUp}
        />
      </div>

      {/* actionability summary bar */}
      {findings.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {actionabilityCounts.map((a) => (
            <span key={a.key} className="flex items-center gap-1.5">
              <span
                className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${a.badgeBg}`}
              >
                {a.count}
              </span>
              <span className="text-neutral-400">{a.label}</span>
            </span>
          ))}
        </div>
      )}

      {/* download bar */}
      <div className="flex flex-wrap items-center gap-3">
        <DownloadButton scanId={scanId} artifactType="markdown" label="Download Markdown" />
        <DownloadButton scanId={scanId} artifactType="pdf" label="Download PDF" />
      </div>

      <Separator />

      {/* tabs: findings view / markdown view */}
      <Tabs defaultValue="findings">
        <TabsList>
          <TabsTrigger value="findings">
            <Shield className="size-4" />
            Findings
          </TabsTrigger>
          <TabsTrigger value="markdown">
            <FileCode className="size-4" />
            Full Report
          </TabsTrigger>
        </TabsList>

        {/* findings tab */}
        <TabsContent value="findings" className="mt-6">
          {findings.length === 0 ? (
            <p className="text-sm text-neutral-400 py-8 text-center">
              No structured findings data available. View the Full Report tab for details.
            </p>
          ) : (
            <Accordion
              type="multiple"
              defaultValue={["must_fix"]}
              className="space-y-2"
            >
              {actionabilityOrder.map((actionability) => {
                const group = grouped[actionability]
                if (group.length === 0) return null
                const config = ACTIONABILITY_CONFIG[actionability]
                return (
                  <AccordionItem
                    key={actionability}
                    value={actionability}
                    className="rounded-lg border border-neutral-800 px-4"
                  >
                    <AccordionTrigger className="hover:no-underline">
                      <div className="flex items-center gap-3">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${config.badgeBg}`}
                        >
                          {group.length}
                        </span>
                        <span className="font-semibold">{config.label}</span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="space-y-3">
                        {group.map((finding, i) => (
                          <FindingCard
                            key={`${finding.check_id}-${i}`}
                            finding={finding}
                            accentBorder={config.accent}
                          />
                        ))}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                )
              })}
            </Accordion>
          )}
        </TabsContent>

        {/* markdown tab */}
        <TabsContent value="markdown" className="mt-6">
          <Card className="border-neutral-800">
            <CardContent className="py-6">
              <article className="prose prose-invert prose-neutral max-w-none prose-headings:text-neutral-100 prose-p:text-neutral-300 prose-a:text-emerald-400 prose-strong:text-neutral-100 prose-code:text-emerald-300 prose-code:bg-neutral-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-neutral-900 prose-pre:border prose-pre:border-neutral-800">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    img: ({ src, ...props }) =>
                      src ? <img src={src} {...props} /> : null,
                  }}
                >
                  {markdownContent}
                </ReactMarkdown>
              </article>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

/* ---------- sub-components ---------- */

function ScoreCard({
  label,
  score,
  icon: Icon,
}: {
  label: string
  score: number
  icon: React.ElementType
}) {
  return (
    <Card className={`border ${scoreBg(score)}`}>
      <CardContent className="space-y-3 py-4">
        <div className="flex items-center gap-2">
          <Icon className={`size-4 ${scoreColor(score)}`} />
          <p className="text-xs text-neutral-400 uppercase tracking-wide font-medium">
            {label}
          </p>
        </div>
        <p className={`text-3xl font-bold tabular-nums ${scoreColor(score)}`}>
          {score}
        </p>
        {/* score bar */}
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-800">
          <div
            className={`h-full rounded-full transition-all duration-500 ${scoreBarBg(score)}`}
            style={{ width: `${score}%` }}
          />
        </div>
      </CardContent>
    </Card>
  )
}

function FindingCard({
  finding,
  accentBorder,
}: {
  finding: Tier1Finding
  accentBorder: string
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`rounded-lg border border-neutral-800 border-l-4 ${accentBorder} bg-neutral-900/50 p-4 space-y-3`}
    >
      {/* header */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${SEVERITY_COLORS[finding.severity] || SEVERITY_COLORS.low}`}
        >
          {finding.severity}
        </span>
        <span className="text-sm font-semibold text-neutral-100">
          {finding.title}
        </span>
        {finding.pattern_id && (
          <Badge variant="outline" className="text-[10px] font-mono">
            {finding.pattern_id}
          </Badge>
        )}
      </div>

      {/* description */}
      <p className="text-sm text-neutral-300">{finding.description}</p>

      {/* data flow */}
      {finding.data_flow && (
        <div className="rounded-md bg-neutral-900 border border-neutral-800 p-3">
          <p className="text-[10px] uppercase tracking-wide text-neutral-500 mb-1.5 font-medium">
            Data Flow
          </p>
          <pre className="text-xs font-mono text-neutral-300 whitespace-pre-wrap">
            {finding.data_flow}
          </pre>
        </div>
      )}

      {/* file path */}
      {finding.file_path && (
        <p className="text-xs font-mono text-neutral-500">
          {finding.file_path}
          {finding.line_number ? `:${finding.line_number}` : ""}
        </p>
      )}

      {/* evidence */}
      {finding.evidence && (
        <div className="rounded-md bg-neutral-900 border border-neutral-800 p-3">
          <p className="text-[10px] uppercase tracking-wide text-neutral-500 mb-1.5 font-medium">
            Evidence
          </p>
          <pre className="text-xs font-mono text-neutral-300 whitespace-pre-wrap overflow-x-auto">
            {finding.evidence}
          </pre>
        </div>
      )}

      {/* suggested fix (expandable) */}
      {finding.suggested_fix && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            <ChevronRight
              className={`size-3.5 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
            />
            Suggested Fix
          </button>
          {expanded && (
            <div className="mt-2 rounded-md bg-emerald-500/5 border border-emerald-500/15 p-3">
              <p className="text-sm text-emerald-200 whitespace-pre-wrap">
                {finding.suggested_fix}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DownloadButton({
  scanId,
  artifactType,
  label,
}: {
  scanId: string
  artifactType: "markdown" | "pdf"
  label: string
}) {
  const { getToken } = useAuth()
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const token = await getToken()
      if (!token) return

      const artifact = await apiFetch<ReportArtifact>(
        `/api/report-artifacts/${scanId}?artifact_type=${artifactType}`,
        { token }
      )

      let blob: Blob
      if (artifact.content_encoding === "base64") {
        const binary = atob(artifact.content)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i)
        }
        blob = new Blob([bytes], { type: artifact.mime_type })
      } else {
        blob = new Blob([artifact.content], { type: artifact.mime_type })
      }

      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = artifact.filename || `report.${artifactType === "pdf" ? "pdf" : "md"}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      // silently fail download — could add toast later
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Button variant="outline" onClick={handleDownload} disabled={downloading}>
      {downloading ? (
        <Loader2 className="size-4 animate-spin" />
      ) : (
        <Download className="size-4" />
      )}
      {label}
    </Button>
  )
}
