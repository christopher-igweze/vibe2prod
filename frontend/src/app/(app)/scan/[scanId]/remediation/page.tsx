"use client"

export const dynamic = "force-dynamic"

import { useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2, AlertCircle, ArrowLeft, CheckCircle2 } from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

/* ---------- types ---------- */

interface ScanFixStatus {
  fix_attempt_id: string
  scan_id: string
  status: "pending" | "running" | "success" | "failed"
  findings_fixed: number | null
  findings_deferred: number | null
  readiness_score: number | null
  pr_url: string | null
  summary: string | null
  cost_usd: number | null
  duration_seconds: number | null
}

/* ---------- phase indicator ---------- */

function PhaseIndicator({
  label,
  state,
}: {
  label: string
  state: "done" | "active" | "pending"
}) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className={`size-8 rounded-full flex items-center justify-center ${
          state === "done"
            ? "bg-emerald-500/20 text-emerald-400"
            : state === "active"
              ? "bg-yellow-500/20 text-yellow-400"
              : "bg-neutral-800 text-neutral-500"
        }`}
      >
        {state === "done" ? (
          <CheckCircle2 className="size-5" />
        ) : state === "active" ? (
          <Loader2 className="size-5 animate-spin" />
        ) : (
          <div className="size-2 rounded-full bg-neutral-600" />
        )}
      </div>
      <span
        className={`text-xs font-medium ${
          state === "done"
            ? "text-emerald-400"
            : state === "active"
              ? "text-yellow-400"
              : "text-neutral-500"
        }`}
      >
        {label}
      </span>
    </div>
  )
}

/* ---------- component ---------- */

export default function RemediationProgressPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()
  const scanId = params.scanId

  const [status, setStatus] = useState<ScanFixStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanFixStatus>(
          `/api/fix-scan/${scanId}/status`,
          { token },
        )
        if (cancelled) return
        setStatus(data)

        if (data.status === "success") {
          if (intervalRef.current) clearInterval(intervalRef.current)
          router.push(`/scan/${scanId}/remediation/results`)
          return
        }

        if (data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      } catch {
        if (cancelled) return
        setError("Failed to load remediation status")
        if (intervalRef.current) clearInterval(intervalRef.current)
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 5000)

    return () => {
      cancelled = true
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [scanId, getToken, router])

  const isRunning =
    !status || status.status === "pending" || status.status === "running"
  const isFailed = status?.status === "failed"

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Running state */}
      {isRunning && !error && (
        <div className="flex flex-col items-center justify-center py-24 space-y-8">
          {/* Phase indicators */}
          <div className="flex items-center gap-6">
            <PhaseIndicator label="Discovery" state="done" />
            <div className="h-px w-8 bg-neutral-700" />
            <PhaseIndicator label="Remediation" state="active" />
            <div className="h-px w-8 bg-neutral-700" />
            <PhaseIndicator label="Validation" state="pending" />
          </div>

          <Loader2 className="size-12 text-emerald-500 animate-spin" />

          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold">Remediating your codebase</h1>
            <p className="text-neutral-400 text-sm max-w-md">
              FORGE is auto-fixing critical issues, generating tests, and
              validating the results.
            </p>
          </div>

          <div className="relative h-1.5 w-64 overflow-hidden rounded-full bg-neutral-800">
            <div className="absolute h-full w-1/3 animate-[shimmer_1.5s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
          </div>
        </div>
      )}

      {/* Failed state */}
      {isFailed && (
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">
                {status?.summary || "Remediation failed unexpectedly. Please try again."}
              </p>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/scan/${scanId}/report`}>
                  <ArrowLeft className="size-4" />
                  Back to Report
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error loading */}
      {error && (
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">{error}</p>
              <Button variant="outline" size="sm" asChild>
                <Link href={`/scan/${scanId}/report`}>
                  <ArrowLeft className="size-4" />
                  Back to Report
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
