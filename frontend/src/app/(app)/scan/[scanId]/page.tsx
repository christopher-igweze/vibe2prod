"use client"

export const dynamic = "force-dynamic"

import { useEffect, useRef, useState, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import {
  Loader2,
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Circle,
} from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import { connectSSE } from "@/lib/api/sse"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

/* ---------- types ---------- */

type Phase = "connecting" | "discovery" | "triage"

interface StageInfo {
  label: string
  description: string
}

const STAGES: Record<Phase, StageInfo> = {
  connecting: { label: "Connecting", description: "Setting up scan environment" },
  discovery: { label: "Discovery", description: "Analyzing codebase structure and security" },
  triage: { label: "Triage", description: "Classifying and prioritizing findings" },
}

const PHASE_ORDER: Phase[] = ["connecting", "discovery", "triage"]

interface LogEntry {
  message: string
  timestamp: Date
  type: "start" | "log" | "complete" | "error"
}

interface ScanPoll {
  id: string
  status: "pending" | "scanning" | "completed" | "failed"
}

/* ---------- component ---------- */

export default function ScanProgressPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()
  const scanId = params.scanId

  const [phase, setPhase] = useState<Phase>("connecting")
  const [latestMessage, setLatestMessage] = useState<string>("Initializing scan...")
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const disconnectRef = useRef<(() => void) | null>(null)
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  // Determine phase from FORGE log message
  const inferPhase = useCallback((message: string): Phase | null => {
    const lower = message.toLowerCase()
    if (lower.includes("discovery")) return "discovery"
    if (lower.includes("triage")) return "triage"
    if (lower.includes("agent 1") || lower.includes("agent 2") || lower.includes("agent 3") || lower.includes("agent 4")) return "discovery"
    if (lower.includes("agent 5") || lower.includes("agent 6")) return "triage"
    return null
  }, [])

  // Fallback to polling if SSE fails
  const startFallbackPolling = useCallback(() => {
    if (fallbackRef.current) return
    let failures = 0

    const poll = async () => {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanPoll>(`/api/user/scans/${scanId}`, { token })
        failures = 0
        if (data.status === "completed") {
          if (fallbackRef.current) clearInterval(fallbackRef.current)
          router.push(`/scan/${scanId}/report`)
        } else if (data.status === "failed") {
          if (fallbackRef.current) clearInterval(fallbackRef.current)
          setError("Scan failed. Please try again from the dashboard.")
        }
      } catch {
        failures++
        if (failures >= 5) {
          setError("Lost connection to server. Please refresh the page.")
          if (fallbackRef.current) clearInterval(fallbackRef.current)
        }
      }
    }

    fallbackRef.current = setInterval(poll, 5000)
  }, [getToken, scanId, router])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs])

  useEffect(() => {
    let cancelled = false

    async function connect() {
      const token = (await getToken()) ?? ""
      if (cancelled) return

      const disconnect = connectSSE(
        scanId,
        token,
        // onEvent
        (event) => {
          if (cancelled) return

          try {
            const data = JSON.parse(event.data)

            switch (event.event) {
              case "agent_start":
              case "agent_log":
              case "agent_complete": {
                const msg = data.message || ""
                if (msg) {
                  setLatestMessage(msg)
                  setLogs(prev => [...prev, {
                    message: msg,
                    timestamp: new Date(),
                    type: event.event === "agent_start" ? "start"
                        : event.event === "agent_complete" ? "complete"
                        : "log",
                  }])
                }
                const newPhase = inferPhase(msg)
                if (newPhase) setPhase(newPhase)
                break
              }
              case "scan_complete":
                setDone(true)
                setLatestMessage(data.message || "Scan complete!")
                setLogs(prev => [...prev, {
                  message: data.message || "Scan complete!",
                  timestamp: new Date(),
                  type: "complete",
                }])
                setTimeout(() => {
                  if (!cancelled) router.push(`/scan/${scanId}/report`)
                }, 1500)
                break
              case "scan_error":
                setError(data.message || "Scan failed unexpectedly.")
                setLogs(prev => [...prev, {
                  message: data.message || "Scan failed unexpectedly.",
                  timestamp: new Date(),
                  type: "error",
                }])
                break
              case "heartbeat":
                // Keep-alive from backend — no action needed
                break
            }
          } catch {
            // Malformed data — ignore
          }
        },
        // onError
        (err) => {
          if (cancelled) return
          // SSE connection failed — fall back to polling
          console.warn("SSE connection failed, falling back to polling:", err.message)
          startFallbackPolling()
        },
      )

      disconnectRef.current = disconnect
    }

    connect()

    return () => {
      cancelled = true
      disconnectRef.current?.()
      if (fallbackRef.current) clearInterval(fallbackRef.current)
    }
  }, [scanId, getToken, router, inferPhase, startFallbackPolling])

  const currentIndex = PHASE_ORDER.indexOf(phase)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Progress state */}
      {!error && !done && (
        <div className="flex flex-col items-center justify-center py-12 space-y-8">
          <Loader2 className="size-10 text-emerald-500 animate-spin" />
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold">Scanning your codebase</h1>
            <p className="text-neutral-400 text-sm">
              This typically takes 2-10 minutes. You can leave and check back
              from the{" "}
              <Link
                href="/dashboard"
                className="text-emerald-400 hover:underline"
              >
                dashboard
              </Link>
              .
            </p>
          </div>

          {/* Stage indicators */}
          <div className="w-full max-w-md space-y-3">
            {PHASE_ORDER.map((p, i) => {
              const stage = STAGES[p]
              const isActive = i === currentIndex
              const isComplete = i < currentIndex
              const isPending = i > currentIndex

              return (
                <div
                  key={p}
                  className={`flex items-center gap-3 rounded-lg px-4 py-3 transition-all ${
                    isActive
                      ? "bg-emerald-500/10 border border-emerald-500/30"
                      : isComplete
                        ? "bg-neutral-800/50 border border-neutral-700/30"
                        : "bg-neutral-900/30 border border-transparent"
                  }`}
                >
                  {isComplete && (
                    <CheckCircle2 className="size-5 text-emerald-500 shrink-0" />
                  )}
                  {isActive && (
                    <Loader2 className="size-5 text-emerald-400 animate-spin shrink-0" />
                  )}
                  {isPending && (
                    <Circle className="size-5 text-neutral-600 shrink-0" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p
                      className={`text-sm font-medium ${
                        isActive
                          ? "text-emerald-300"
                          : isComplete
                            ? "text-neutral-300"
                            : "text-neutral-500"
                      }`}
                    >
                      {stage.label}
                    </p>
                    {isActive && (
                      <p className="text-xs text-neutral-400 mt-0.5">
                        {latestMessage}
                      </p>
                    )}
                    {!isActive && (
                      <p className="text-xs text-neutral-500 mt-0.5">
                        {stage.description}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Live log feed */}
          {logs.length > 0 && (
            <Card className="w-full max-w-md border border-neutral-800 bg-neutral-900/50">
              <CardContent className="p-0">
                <ScrollArea className="h-48">
                  <div className="p-4 space-y-2">
                    {logs.map((log, i) => (
                      <div key={i} className="flex items-start gap-3 text-xs">
                        <span className="text-neutral-600 font-mono shrink-0 pt-0.5">
                          {log.timestamp.toLocaleTimeString()}
                        </span>
                        {log.type === "complete" ? (
                          <CheckCircle2 className="size-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        ) : log.type === "start" ? (
                          <Circle className="size-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        ) : log.type === "error" ? (
                          <AlertCircle className="size-3.5 text-red-400 shrink-0 mt-0.5" />
                        ) : (
                          <Circle className="size-3.5 text-neutral-600 shrink-0 mt-0.5" />
                        )}
                        <span className={log.type === "error" ? "text-red-300" : "text-neutral-300"}>
                          {log.message}
                        </span>
                      </div>
                    ))}
                    <div ref={logEndRef} />
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Completed state (brief flash before redirect) */}
      {done && !error && (
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <CheckCircle2 className="size-12 text-emerald-500" />
          <h1 className="text-2xl font-bold">Scan Complete</h1>
          <p className="text-neutral-400 text-sm">Redirecting to report...</p>
        </div>
      )}

      {/* Failed state */}
      {error && (
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
