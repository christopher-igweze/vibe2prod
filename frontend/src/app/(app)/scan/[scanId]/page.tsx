"use client"

export const dynamic = "force-dynamic"

import { useEffect, useRef, useState } from "react"
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
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

/* ---------- types ---------- */

type Phase = "connecting" | "scanning" | "complete"

interface StageInfo {
  label: string
  description: string
}

const STAGES: Record<Phase, StageInfo> = {
  connecting: { label: "Connecting", description: "Setting up scan environment" },
  scanning: { label: "Scanning", description: "Analyzing codebase structure and security" },
  complete: { label: "Complete", description: "Scan finished" },
}

const PHASE_ORDER: Phase[] = ["connecting", "scanning", "complete"]

interface ScanPoll {
  id: string
  status: "pending" | "scanning" | "completed" | "failed"
  failure_reason?: string | null
}

/* ---------- component ---------- */

export default function ScanProgressPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()
  const scanId = params.scanId

  const [phase, setPhase] = useState<Phase>("connecting")
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let cancelled = false
    let failures = 0

    const poll = async () => {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanPoll>(`/api/user/scans/${scanId}`, { token })
        failures = 0

        if (cancelled) return

        if (data.status === "scanning") {
          setPhase("scanning")
        } else if (data.status === "completed") {
          setPhase("complete")
          setDone(true)
          if (pollRef.current) clearInterval(pollRef.current)
          setTimeout(() => {
            if (!cancelled) router.push(`/scan/${scanId}/report`)
          }, 1500)
        } else if (data.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current)
          setError(
            data.failure_reason || "Scan failed. Please try again from the dashboard."
          )
        }
      } catch {
        failures++
        if (failures >= 5) {
          setError("Lost connection to server. Please refresh the page.")
          if (pollRef.current) clearInterval(pollRef.current)
        }
      }
    }

    // Poll immediately, then every 5 seconds
    poll()
    pollRef.current = setInterval(poll, 5000)

    return () => {
      cancelled = true
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [scanId, getToken, router])

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
            {PHASE_ORDER.filter((p) => p !== "complete").map((p, i) => {
              const stage = STAGES[p]
              const isActive = i === currentIndex
              const isComplete = i < currentIndex

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
                  {!isActive && !isComplete && (
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
                    <p className={`text-xs mt-0.5 ${isActive ? "text-neutral-400" : "text-neutral-500"}`}>
                      {stage.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
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
