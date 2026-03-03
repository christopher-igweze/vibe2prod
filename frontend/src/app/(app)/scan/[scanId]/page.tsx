"use client"

export const dynamic = "force-dynamic"

import { useEffect, useRef, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2, ArrowLeft, AlertCircle } from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

/* ---------- types ---------- */

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

  const [scan, setScan] = useState<ScanPoll | null>(null)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let cancelled = false
    let failures = 0

    async function poll() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanPoll>(`/api/user/scans/${scanId}`, {
          token,
        })
        if (cancelled) return
        failures = 0
        setScan(data)

        if (data.status === "completed") {
          if (intervalRef.current) clearInterval(intervalRef.current)
          router.push(`/scan/${scanId}/report`)
          return
        }

        if (data.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current)
          setError("Scan failed. Please try again from the dashboard.")
        }
      } catch {
        if (cancelled) return
        failures++
        if (failures >= 5) {
          setError("Lost connection to server. Please refresh the page.")
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      }
    }

    // Poll immediately, then every 4 seconds
    poll()
    intervalRef.current = setInterval(poll, 4000)

    return () => {
      cancelled = true
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [scanId, getToken, router])

  const isRunning =
    !scan || scan.status === "pending" || scan.status === "scanning"
  const isFailed = scan?.status === "failed"

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Running state */}
      {isRunning && !error && (
        <div className="flex flex-col items-center justify-center py-16 space-y-8">
          <Loader2 className="size-12 text-emerald-500 animate-spin" />
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-bold">Scanning your codebase</h1>
            <p className="text-neutral-400 text-sm">
              This typically takes 2-5 minutes. You can leave and check back
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

          {/* Shimmer bar */}
          <div className="relative h-1.5 w-64 overflow-hidden rounded-full bg-neutral-800">
            <div className="absolute h-full w-1/3 animate-[shimmer_1.5s_ease-in-out_infinite] rounded-full bg-gradient-to-r from-transparent via-emerald-500 to-transparent" />
          </div>
        </div>
      )}

      {/* Failed state */}
      {(isFailed || error) && (
        <Card className="border border-red-500/20 bg-red-500/5">
          <CardContent className="flex items-start gap-3 py-4">
            <AlertCircle className="mt-0.5 size-5 text-red-400 shrink-0" />
            <div className="space-y-2">
              <p className="text-sm text-red-300">
                {error || "Scan failed unexpectedly. Please try again."}
              </p>
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
