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
  Loader2,
  AlertCircle,
} from "lucide-react"

import { apiFetch, ApiError } from "@/lib/api/client"
import type { ReportArtifact } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

/* ---------- types ---------- */

interface ScanDetail {
  id: string
  status: string
  health_score: number | null
  security_score: number | null
  reliability_score: number | null
  scalability_score: number | null
  repo_name?: string
  repo_url?: string
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

/* ---------- component ---------- */

export default function ReportPage() {
  const params = useParams<{ scanId: string }>()
  const router = useRouter()
  const { getToken } = useAuth()

  const scanId = params.scanId

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scores, setScores] = useState<{
    health_score: number
    security_score: number
    reliability_score: number
    scalability_score: number
  } | null>(null)
  const [markdownContent, setMarkdownContent] = useState("")

  const fetchReport = useCallback(async () => {
    try {
      const token = await getToken()
      if (!token) {
        router.push("/dashboard")
        return
      }

      // Fetch scan detail (scores) and markdown artifact in parallel
      const [scanDetail, artifact] = await Promise.all([
        apiFetch<ScanDetail>(`/api/user/scans/${scanId}`, { token }),
        apiFetch<ReportArtifact>(
          `/api/report-artifacts/${scanId}?artifact_type=markdown`,
          { token }
        ).catch(() => null),
      ])

      setScores({
        health_score: scanDetail.health_score ?? 0,
        security_score: scanDetail.security_score ?? 0,
        reliability_score: scanDetail.reliability_score ?? 0,
        scalability_score: scanDetail.scalability_score ?? 0,
      })

      if (artifact) {
        setMarkdownContent(
          artifact.content_encoding === "base64"
            ? atob(artifact.content)
            : artifact.content
        )
      }
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

  if (error || !scores) {
    return (
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
    )
  }

  return (
    <div className="space-y-8">
      {/* back nav */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/dashboard">
            <ArrowLeft className="size-4" />
            Back to Dashboard
          </Link>
        </Button>
      </div>

      {/* score dashboard */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <ScoreCard label="Health" score={scores.health_score} icon={Heart} />
        <ScoreCard label="Security" score={scores.security_score} icon={Shield} />
        <ScoreCard label="Reliability" score={scores.reliability_score} icon={Zap} />
        <ScoreCard label="Scalability" score={scores.scalability_score} icon={TrendingUp} />
      </div>

      {/* download bar */}
      <div className="flex flex-wrap items-center gap-3">
        <DownloadButton scanId={scanId} artifactType="markdown" label="Download Markdown" />
        <DownloadButton scanId={scanId} artifactType="pdf" label="Download PDF" />
      </div>

      {/* markdown report */}
      {markdownContent ? (
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
      ) : (
        <p className="text-sm text-neutral-400 py-8 text-center">
          Report content not available.
        </p>
      )}
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
      // silently fail download
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
