"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { ArrowLeft, Loader2, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import type { ProjectScanHistory, ScanHistoryItem } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { scoreColorClass } from "../../dashboard/_components/dashboard-utils"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusBadgeVariant(status: string) {
  switch (status) {
    case "completed": return "default" as const
    case "failed": return "destructive" as const
    default: return "secondary" as const
  }
}

function TrendArrow({ current, previous }: { current: number | null; previous: number | null }) {
  if (current === null || previous === null) return <Minus className="size-3 text-[#4E586E]" />
  const diff = current - previous
  if (diff > 0) return <TrendingUp className="size-3 text-forge-emerald" />
  if (diff < 0) return <TrendingDown className="size-3 text-red-400" />
  return <Minus className="size-3 text-[#4E586E]" />
}

function ScoreCell({ score }: { score: number | null }) {
  if (score === null) return <span className="text-[#4E586E]">--</span>
  return <span className={scoreColorClass(score)}>{score}</span>
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { getToken } = useAuth()

  const [data, setData] = useState<ProjectScanHistory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined
        const result = await apiFetch<ProjectScanHistory>(
          `/api/user/projects/${projectId}/scans`,
          { token },
        )
        setData(result)
      } catch {
        setError("Failed to load project data")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [getToken, projectId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="size-6 animate-spin text-forge-emerald" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-[#8692A8] hover:text-forge-emerald">
          <ArrowLeft className="size-4" /> Back to Dashboard
        </Link>
        <Card className="border-red-500/50 bg-red-950/20 p-6 text-center">
          <p className="text-red-400">{error || "Project not found"}</p>
        </Card>
      </div>
    )
  }

  const { project, scans } = data
  const displayName = project.repo_name || project.repo_url
  const firstScanDate = scans.length > 0
    ? new Date(scans[scans.length - 1].created_at).toLocaleDateString()
    : "N/A"
  const repoUrlEncoded = encodeURIComponent(project.repo_url)

  return (
    <div className="space-y-8">
      {/* Back link */}
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-sm text-[#8692A8] hover:text-forge-emerald">
        <ArrowLeft className="size-4" /> Back to Dashboard
      </Link>

      {/* Project header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">
            {displayName}
          </h1>
          <p className="text-sm text-[#8692A8] mt-1">
            {project.scan_count} scan{project.scan_count !== 1 ? "s" : ""} &middot; First scan {firstScanDate}
          </p>
        </div>
        <Link href={`/scan/new?repo_url=${repoUrlEncoded}`}>
          <Button className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19] gap-2">
            <RefreshCw className="size-4" /> Re-scan
          </Button>
        </Link>
      </div>

      {/* Score trend table */}
      {scans.filter((s) => s.status === "completed").length > 0 && (
        <Card className="forge-glass-card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.06]">
            <h2 className="text-sm font-semibold text-[#8692A8] uppercase tracking-wider">Score Trend</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-[#8692A8]">
                  <th className="text-left px-4 py-2 font-medium">Date</th>
                  <th className="text-center px-4 py-2 font-medium">Health</th>
                  <th className="text-center px-4 py-2 font-medium">Security</th>
                  <th className="text-center px-4 py-2 font-medium">Reliability</th>
                  <th className="text-center px-4 py-2 font-medium">Scalability</th>
                </tr>
              </thead>
              <tbody>
                {scans
                  .filter((s) => s.status === "completed")
                  .map((scan, idx, arr) => {
                    const prev: ScanHistoryItem | null = arr[idx + 1] ?? null
                    return (
                      <tr key={scan.id} className="border-b border-white/[0.04] hover:bg-white/[0.02]">
                        <td className="px-4 py-2 text-[#E8ECF4]">
                          {new Date(scan.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="inline-flex items-center gap-1">
                            <ScoreCell score={scan.health_score} />
                            <TrendArrow current={scan.health_score} previous={prev?.health_score ?? null} />
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="inline-flex items-center gap-1">
                            <ScoreCell score={scan.security_score} />
                            <TrendArrow current={scan.security_score} previous={prev?.security_score ?? null} />
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="inline-flex items-center gap-1">
                            <ScoreCell score={scan.reliability_score} />
                            <TrendArrow current={scan.reliability_score} previous={prev?.reliability_score ?? null} />
                          </span>
                        </td>
                        <td className="px-4 py-2 text-center">
                          <span className="inline-flex items-center gap-1">
                            <ScoreCell score={scan.scalability_score} />
                            <TrendArrow current={scan.scalability_score} previous={prev?.scalability_score ?? null} />
                          </span>
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Scan history */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Scan History</h2>
        {scans.length === 0 ? (
          <Card className="border-dashed p-8 text-center">
            <p className="text-[#8692A8] text-sm">No scans yet for this project.</p>
          </Card>
        ) : (
          scans.map((scan) => (
            <Card key={scan.id} className="forge-glass-hover p-4 transition-colors">
              <div className="flex items-center justify-between gap-3">
                <Link
                  href={scan.status === "completed" ? `/scan/${scan.id}/report` : `/scan/${scan.id}`}
                  className="flex-1 min-w-0"
                >
                  <div className="cursor-pointer">
                    <p className="font-medium text-[#E8ECF4]">
                      {new Date(scan.created_at).toLocaleDateString()} &middot; {scan.scan_tier}
                    </p>
                    <div className="flex items-center gap-4 mt-1 text-xs">
                      {scan.health_score !== null && (
                        <span className={scoreColorClass(scan.health_score)}>
                          Health: {scan.health_score}
                        </span>
                      )}
                      {scan.security_score !== null && (
                        <span className={scoreColorClass(scan.security_score)}>
                          Security: {scan.security_score}
                        </span>
                      )}
                      {scan.reliability_score !== null && (
                        <span className={scoreColorClass(scan.reliability_score)}>
                          Reliability: {scan.reliability_score}
                        </span>
                      )}
                      {scan.scalability_score !== null && (
                        <span className={scoreColorClass(scan.scalability_score)}>
                          Scalability: {scan.scalability_score}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
                <Badge variant={statusBadgeVariant(scan.status)}>
                  {scan.status}
                </Badge>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
