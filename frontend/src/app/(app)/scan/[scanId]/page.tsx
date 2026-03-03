"use client"

export const dynamic = "force-dynamic"

import { useCallback, useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import {
  Loader2,
  ArrowLeft,
  AlertCircle,
  Bot,
  Search,
  Filter,
  CheckCircle2,
} from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import { connectSSE, type SSEEvent } from "@/lib/api/sse"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

/* ---------- types ---------- */

interface ScanPoll {
  id: string
  status: "pending" | "scanning" | "completed" | "failed"
}

const PHASE_SEQUENCE = ["Discovery", "Triage", "Complete"] as const
type Phase = (typeof PHASE_SEQUENCE)[number]

/* ---------- component ---------- */

export default function ScanProgressPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()
  const scanId = params.scanId

  const [scan, setScan] = useState<ScanPoll | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // SSE-enhanced state
  const [agents, setAgents] = useState<string[]>([])
  const [logEntries, setLogEntries] = useState<string[]>([])
  const [findingsCount, setFindingsCount] = useState(0)
  const [currentPhase, setCurrentPhase] = useState<Phase>("Discovery")
  const [sseConnected, setSseConnected] = useState(false)

  const addLog = useCallback((line: string) => {
    setLogEntries((prev) => [...prev.slice(-49), line])
  }, [])

  // SSE connection
  useEffect(() => {
    let disconnectSSE: (() => void) | null = null
    let cancelled = false

    async function startSSE() {
      try {
        const token = await getToken()
        if (cancelled || !token) return

        disconnectSSE = connectSSE(
          scanId,
          token,
          (event: SSEEvent) => {
            if (cancelled) return

            let parsed: Record<string, unknown> = {}
            try {
              parsed = JSON.parse(event.data)
            } catch {
              // data may not be JSON
            }

            switch (event.event) {
              case "agent_start":
                setAgents((prev) => {
                  const name = (parsed.agent as string) || event.data
                  return prev.includes(name) ? prev : [...prev, name]
                })
                addLog(`Agent started: ${(parsed.agent as string) || event.data}`)
                break

              case "agent_log":
                addLog((parsed.message as string) || event.data)
                break

              case "agent_complete":
                setAgents((prev) =>
                  prev.filter((a) => a !== ((parsed.agent as string) || event.data))
                )
                addLog(`Agent complete: ${(parsed.agent as string) || event.data}`)
                break

              case "finding":
                setFindingsCount((prev) => prev + 1)
                break

              case "phase_change": {
                const phase = (parsed.phase as string) || event.data
                if (phase.toLowerCase().includes("triage")) setCurrentPhase("Triage")
                break
              }

              case "scan_complete":
                setCurrentPhase("Complete")
                setScan({ id: scanId, status: "completed" })
                router.push(`/scan/${scanId}/report`)
                break

              case "scan_error":
                setScan({ id: scanId, status: "failed" })
                setError((parsed.message as string) || "Scan failed")
                break

              case "heartbeat":
                // Backend is polling DB on our behalf — scan is still running
                break

              case "timeout":
                // SSE stream timed out — fall back to polling
                setSseConnected(false)
                startPolling()
                break

              default:
                // Handle status events from the proxy
                if (parsed.status === "completed") {
                  setCurrentPhase("Complete")
                  setScan({ id: scanId, status: "completed" })
                  router.push(`/scan/${scanId}/report`)
                } else if (parsed.status === "failed") {
                  setScan({ id: scanId, status: "failed" })
                  setError((parsed.message as string) || "Scan failed")
                }
                break
            }
          },
          () => {
            // SSE error — fall back to polling
            if (!cancelled) {
              setSseConnected(false)
              startPolling()
            }
          },
        )

        setSseConnected(true)
      } catch {
        if (!cancelled) {
          setSseConnected(false)
          startPolling()
        }
      }
    }

    function startPolling() {
      if (intervalRef.current) return // already polling
      poll()
      intervalRef.current = setInterval(poll, 4000)
    }

    let pollFailures = 0

    async function poll() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanPoll>(`/api/user/scans/${scanId}`, { token })
        if (cancelled) return
        pollFailures = 0
        setScan(data)

        if (data.status === "completed") {
          if (intervalRef.current) clearInterval(intervalRef.current)
          router.push(`/scan/${scanId}/report`)
          return
        }

        if (data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current)
          setError("Scan failed")
        }
      } catch {
        if (cancelled) return
        pollFailures++
        // Only show error after 5 consecutive failures (~20s)
        if (pollFailures >= 5) {
          setError("Failed to load scan status")
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      }
    }

    startSSE()

    return () => {
      cancelled = true
      if (disconnectSSE) disconnectSSE()
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [scanId, getToken, router, addLog])

  const isRunning = !scan || scan.status === "pending" || scan.status === "scanning"
  const isFailed = scan?.status === "failed"

  const phaseIndex = PHASE_SEQUENCE.indexOf(currentPhase)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Running state */}
      {isRunning && !error && (
        <div className="flex flex-col items-center justify-center py-16 space-y-8">
          <Loader2 className="size-12 text-emerald-500 animate-spin" />
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold">Scanning your codebase</h1>
            <p className="text-neutral-400 text-sm">
              This typically takes 2-5 minutes. You can leave this page and check back from the dashboard.
            </p>
          </div>

          {/* Phase progress */}
          <div className="flex items-center gap-3">
            {PHASE_SEQUENCE.map((phase, i) => {
              const isActive = i === phaseIndex
              const isDone = i < phaseIndex
              const Icon = i === 0 ? Search : i === 1 ? Filter : CheckCircle2
              return (
                <div key={phase} className="flex items-center gap-2">
                  {i > 0 && (
                    <div
                      className={`w-8 h-px ${isDone ? "bg-emerald-500" : "bg-neutral-700"}`}
                    />
                  )}
                  <div
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : isDone
                        ? "bg-emerald-500/10 text-emerald-500/70"
                        : "bg-neutral-800 text-neutral-500"
                    }`}
                  >
                    <Icon className="size-3" />
                    {phase}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Shimmer bar */}
          <div className="relative h-1.5 w-64 overflow-hidden rounded-full bg-neutral-800">
            <div className="absolute h-full w-1/3 animate-[shimmer_1.5s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
          </div>

          {/* Active agents */}
          {agents.length > 0 && (
            <div className="flex flex-wrap justify-center gap-2">
              {agents.map((agent) => (
                <Badge
                  key={agent}
                  variant="outline"
                  className="border-emerald-500/30 text-emerald-400 text-xs gap-1.5"
                >
                  <Bot className="size-3 animate-pulse" />
                  {agent}
                </Badge>
              ))}
            </div>
          )}

          {/* Findings counter */}
          {findingsCount > 0 && (
            <p className="text-sm text-neutral-400">
              <span className="text-emerald-400 font-semibold">{findingsCount}</span>{" "}
              {findingsCount === 1 ? "finding" : "findings"} detected so far
            </p>
          )}

          {/* Log lines */}
          {sseConnected && logEntries.length > 0 && (
            <div className="w-full max-h-32 overflow-y-auto rounded-lg border border-neutral-800 bg-neutral-950 p-3">
              {logEntries.slice(-5).map((line, i) => (
                <p
                  key={i}
                  className="text-xs text-neutral-500 font-mono truncate leading-relaxed"
                >
                  {line}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">{error || "Scan failed unexpectedly. Please try again."}</p>
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

      {/* Error loading */}
      {error && !isFailed && (
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">{error}</p>
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
    </div>
  )
}
