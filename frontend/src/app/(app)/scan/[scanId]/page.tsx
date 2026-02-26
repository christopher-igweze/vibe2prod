"use client"

export const dynamic = "force-dynamic"

import { useEffect, useRef, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import {
  Shield,
  Heart,
  Zap,
  TrendingUp,
  Download,
  ArrowLeft,
  FileText,
  AlertCircle,
} from "lucide-react"

import { connectSSE, type SSEEvent } from "@/lib/api/sse"
import type { Tier1Finding, ReportScores } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

/* ---------- types ---------- */

interface TimelineEvent {
  id: string
  event_type: string
  agent: string
  message: string
  level: "info" | "warn" | "error" | "success"
  timestamp: string
  data?: Record<string, unknown>
  finding?: Tier1Finding
}

interface ScanCompleteData extends ReportScores {
  findings_count: number
  quota_remaining: number
  report_artifact_available: boolean
  report_artifact_types: string[]
}

type ScanPhase = "scanning" | "completed" | "errored"

/* ---------- helpers ---------- */

const LEVEL_COLORS: Record<string, string> = {
  info: "bg-blue-500",
  warn: "bg-yellow-500",
  error: "bg-red-500",
  success: "bg-emerald-500",
}

const LEVEL_TEXT: Record<string, string> = {
  info: "text-blue-400",
  warn: "text-yellow-400",
  error: "text-red-400",
  success: "text-emerald-400",
}

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

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  } catch {
    return ""
  }
}

/* ---------- component ---------- */

export default function ScanProgressPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()

  const scanId = params.scanId

  const [phase, setPhase] = useState<ScanPhase>("scanning")
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [completeData, setCompleteData] = useState<ScanCompleteData | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [repoName, setRepoName] = useState<string>("")

  const timelineEndRef = useRef<HTMLDivElement>(null)
  const retryCountRef = useRef(0)
  const abortRef = useRef<(() => void) | null>(null)
  const MAX_RETRIES = 5

  // auto-scroll timeline to bottom
  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [events])

  const handleSSEEvent = useCallback((sseEvent: SSEEvent) => {
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(sseEvent.data)
    } catch {
      return
    }

    const eventType = (parsed.event_type as string) || sseEvent.event
    const agent = (parsed.agent as string) || ""
    const message = (parsed.message as string) || ""
    const level = (parsed.level as TimelineEvent["level"]) || "info"
    const timestamp = (parsed.timestamp as string) || new Date().toISOString()

    // extract repo name from first event if available
    if (parsed.repo_name) {
      setRepoName(parsed.repo_name as string)
    }

    const timelineEntry: TimelineEvent = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      event_type: eventType,
      agent,
      message,
      level,
      timestamp,
      data: parsed.data as Record<string, unknown> | undefined,
    }

    // handle finding events
    if (eventType === "finding" && parsed.data) {
      timelineEntry.finding = parsed.data as unknown as Tier1Finding
    }

    // handle terminal events
    if (eventType === "scan_complete") {
      const data = (parsed.data || parsed) as unknown as ScanCompleteData
      setCompleteData(data)
      setPhase("completed")
    } else if (eventType === "scan_error") {
      setErrorMessage(message || "Scan failed unexpectedly")
      setPhase("errored")
    }

    setEvents((prev) => [...prev, timelineEntry])
  }, [])

  const connect = useCallback(async () => {
    const token = await getToken()
    if (!token) {
      router.push("/dashboard")
      return
    }

    abortRef.current = connectSSE(scanId, token, handleSSEEvent, (error) => {
      // 403 -> no access
      if (error.status === 403) {
        router.push("/dashboard")
        return
      }

      // 429 -> rate limited, retry with backoff
      if (error.status === 429 && retryCountRef.current < MAX_RETRIES) {
        const delay = Math.min(3000 * 2 ** retryCountRef.current, 30000)
        retryCountRef.current++
        setEvents((prev) => [
          ...prev,
          {
            id: `retry-${Date.now()}`,
            event_type: "system",
            agent: "system",
            message: `Rate limited, retrying in ${Math.round(delay / 1000)}s...`,
            level: "warn",
            timestamp: new Date().toISOString(),
          },
        ])
        setTimeout(() => connect(), delay)
        return
      }

      // SSE disconnect -> auto-reconnect
      if (!error.status && retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current++
        setEvents((prev) => [
          ...prev,
          {
            id: `reconnect-${Date.now()}`,
            event_type: "system",
            agent: "system",
            message: `Connection lost, reconnecting (attempt ${retryCountRef.current}/${MAX_RETRIES})...`,
            level: "warn",
            timestamp: new Date().toISOString(),
          },
        ])
        setTimeout(() => connect(), 3000)
        return
      }

      // exhausted retries or other error
      setErrorMessage(error.message || "Connection failed")
      setPhase("errored")
    })
  }, [scanId, getToken, handleSSEEvent, router])

  useEffect(() => {
    connect()
    return () => {
      abortRef.current?.()
    }
  }, [connect])

  /* ---------- render helpers ---------- */

  const ScoreCard = ({
    label,
    score,
    icon: Icon,
  }: {
    label: string
    score: number
    icon: React.ElementType
  }) => (
    <Card className={`border ${scoreBg(score)}`}>
      <CardContent className="flex items-center gap-3 py-4">
        <Icon className={`size-5 ${scoreColor(score)}`} />
        <div>
          <p className="text-xs text-neutral-400 uppercase tracking-wide">{label}</p>
          <p className={`text-2xl font-bold tabular-nums ${scoreColor(score)}`}>{score}</p>
        </div>
      </CardContent>
    </Card>
  )

  return (
    <div className="space-y-6">
      {/* header */}
      <div className="flex items-center gap-3">
        {phase === "scanning" && (
          <span className="relative flex size-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex size-3 rounded-full bg-emerald-500" />
          </span>
        )}
        {phase === "completed" && (
          <span className="relative flex size-3">
            <span className="relative inline-flex size-3 rounded-full bg-emerald-500" />
          </span>
        )}
        {phase === "errored" && (
          <span className="relative flex size-3">
            <span className="relative inline-flex size-3 rounded-full bg-red-500" />
          </span>
        )}
        <h1 className="text-2xl font-bold">
          {phase === "scanning" && (
            <>Scanning {repoName ? <span className="text-emerald-400">{repoName}</span> : "repository"}...</>
          )}
          {phase === "completed" && <>Scan Complete</>}
          {phase === "errored" && <>Scan Failed</>}
        </h1>
      </div>

      {/* indeterminate progress bar */}
      {phase === "scanning" && (
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-neutral-800">
          <div className="absolute h-full w-1/3 animate-[shimmer_1.5s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
        </div>
      )}

      {/* score cards on completion */}
      {phase === "completed" && completeData && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <ScoreCard label="Health" score={completeData.health_score} icon={Heart} />
          <ScoreCard label="Security" score={completeData.security_score} icon={Shield} />
          <ScoreCard label="Reliability" score={completeData.reliability_score} icon={Zap} />
          <ScoreCard label="Scalability" score={completeData.scalability_score} icon={TrendingUp} />
        </div>
      )}

      {/* action buttons on completion */}
      {phase === "completed" && completeData && (
        <div className="flex flex-wrap items-center gap-3">
          <Button asChild>
            <Link href={`/scan/${scanId}/report`}>
              <FileText className="size-4" />
              View Full Report
            </Link>
          </Button>
          {completeData.report_artifact_types?.includes("markdown") && (
            <Button variant="outline" asChild>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/report-artifacts/${scanId}?artifact_type=markdown`}
                download
              >
                <Download className="size-4" />
                Download MD
              </a>
            </Button>
          )}
          {completeData.report_artifact_types?.includes("pdf") && (
            <Button variant="outline" asChild>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/report-artifacts/${scanId}?artifact_type=pdf`}
                download
              >
                <Download className="size-4" />
                Download PDF
              </a>
            </Button>
          )}
        </div>
      )}

      {/* error state */}
      {phase === "errored" && (
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">{errorMessage}</p>
              <Button variant="outline" size="sm" asChild>
                <Link href="/dashboard">
                  <ArrowLeft className="size-4" />
                  Back to Dashboard
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* event timeline */}
      <Card className="border-neutral-800">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-neutral-400 uppercase tracking-wide">
            Activity Log
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[28rem]">
            <div className="space-y-1 pr-4">
              {events.length === 0 && phase === "scanning" && (
                <p className="text-sm text-neutral-500 py-8 text-center">
                  Waiting for scan events...
                </p>
              )}
              {events.map((evt) => (
                <div key={evt.id}>
                  {/* regular event row */}
                  <div className="group flex items-start gap-3 rounded-md px-2 py-1.5 hover:bg-neutral-900/50">
                    {/* level dot */}
                    <span
                      className={`mt-1.5 size-2 shrink-0 rounded-full ${LEVEL_COLORS[evt.level] || LEVEL_COLORS.info}`}
                    />
                    {/* timestamp */}
                    <span className="shrink-0 w-16 text-xs font-mono text-neutral-500 mt-0.5">
                      {formatTime(evt.timestamp)}
                    </span>
                    {/* agent badge */}
                    {evt.agent && evt.agent !== "system" && (
                      <Badge
                        variant="secondary"
                        className="shrink-0 text-[10px] font-mono uppercase"
                      >
                        {evt.agent}
                      </Badge>
                    )}
                    {/* message */}
                    <span className={`text-sm ${LEVEL_TEXT[evt.level] || "text-neutral-300"}`}>
                      {evt.message}
                    </span>
                  </div>
                  {/* finding card inline */}
                  {evt.finding && (
                    <div className="ml-8 mb-2 mt-1 rounded-lg border border-neutral-800 bg-neutral-900/50 p-3 space-y-1">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={evt.finding.severity} />
                        <span className="text-sm font-medium text-neutral-100">
                          {evt.finding.title}
                        </span>
                        {evt.finding.pattern_id && (
                          <Badge variant="outline" className="text-[10px] font-mono">
                            {evt.finding.pattern_id}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-neutral-400">{evt.finding.description}</p>
                      {evt.finding.file_path && (
                        <p className="text-xs font-mono text-neutral-500">
                          {evt.finding.file_path}
                          {evt.finding.line_number ? `:${evt.finding.line_number}` : ""}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={timelineEndRef} />
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* summary counts on completion */}
      {phase === "completed" && completeData && (
        <p className="text-sm text-neutral-400 text-center">
          {completeData.findings_count} findings detected
          {completeData.quota_remaining != null && (
            <> &middot; {completeData.quota_remaining} scans remaining this month</>
          )}
        </p>
      )}
    </div>
  )
}

/* ---------- sub-components ---------- */

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: "bg-red-500/15 text-red-400 border-red-500/25",
    high: "bg-orange-500/15 text-orange-400 border-orange-500/25",
    medium: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
    low: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  }
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${map[severity] || map.low}`}
    >
      {severity}
    </span>
  )
}
