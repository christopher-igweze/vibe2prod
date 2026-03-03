"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Download, FileText, Printer, Trash2, Loader2, Copy, Check, Wrench } from "lucide-react"

import type { DiscoveryReport, FixResponse } from "@/lib/api/types"
import { reportToMarkdown } from "@/lib/report/to-markdown"
import { apiFetch } from "@/lib/api/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { formatDuration, formatCost } from "./report-utils"

interface ReportHeaderProps {
  report: DiscoveryReport
  repoName?: string
  scanId: string
  actionableCount?: number
  fixAttemptStatus?: 'pending' | 'running' | 'success' | 'failed' | null
}

function downloadJson(report: DiscoveryReport, repoName?: string) {
  const slug = (repoName || "repo").replace(/\//g, "-")
  const date = new Date().toISOString().slice(0, 10)
  const filename = `forge-report-${slug}-${date}.json`

  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadMarkdown(report: DiscoveryReport, repoName?: string) {
  const slug = (repoName || "repo").replace(/\//g, "-")
  const date = new Date().toISOString().slice(0, 10)
  const filename = `forge-report-${slug}-${date}.md`

  const md = reportToMarkdown(report, repoName)
  const blob = new Blob([md], { type: "text/markdown" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ReportHeader({ report, repoName, scanId, actionableCount, fixAttemptStatus }: ReportHeaderProps) {
  const router = useRouter()
  const { getToken } = useAuth()
  const [deleting, setDeleting] = useState(false)
  const [copied, setCopied] = useState(false)
  const [fixing, setFixing] = useState(false)

  const truncatedRunId = report.run_id.slice(0, 12)
  const formattedDate = new Date(report.generated_at).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(report, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable
    }
  }

  async function handleFix() {
    setFixing(true)
    try {
      const token = (await getToken()) ?? undefined
      await apiFetch<FixResponse>(`/api/fix-scan/${scanId}`, {
        method: "POST",
        token,
      })
      router.push(`/scan/${scanId}/remediation`)
    } catch {
      setFixing(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    try {
      const token = (await getToken()) ?? undefined
      await apiFetch(`/api/user/scans/${scanId}`, {
        method: "DELETE",
        token,
      })
      router.push("/dashboard")
    } catch {
      setDeleting(false)
    }
  }

  return (
    <div className="text-center space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-neutral-100">
          FORGE Report
        </h1>

        {/* Phase badges */}
        <div className="flex items-center justify-center gap-2 mt-3">
          <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
            Discovery ✓
          </Badge>
          {fixAttemptStatus === 'running' && (
            <Badge className="bg-yellow-500/15 text-yellow-400 border-yellow-500/30">
              Remediation ⏳
            </Badge>
          )}
          {fixAttemptStatus === 'success' && (
            <>
              <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                Remediation ✓
              </Badge>
              <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                Validation ✓
              </Badge>
            </>
          )}
        </div>
        {repoName && (
          <p className="text-neutral-400 text-base mt-1">{repoName}</p>
        )}
        <p className="text-neutral-500 text-sm mt-2">
          <span className="font-mono">{truncatedRunId}</span>
          <span className="mx-2 text-neutral-700">|</span>
          {formattedDate}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3 text-xs">
        <Badge variant="outline" className="border-neutral-700 text-neutral-300">
          {actionableCount ?? report.total_findings} actionable findings
        </Badge>
        <Badge variant="outline" className="border-neutral-700 text-neutral-300">
          {report.loc_total.toLocaleString()} LOC
        </Badge>
        <Badge variant="outline" className="border-neutral-700 text-neutral-300">
          {report.file_count.toLocaleString()} files
        </Badge>
        <Badge variant="outline" className="border-neutral-700 text-neutral-300">
          {formatDuration(report.duration_seconds)}
        </Badge>
        {report.cost_usd > 0 && (
          <Badge variant="outline" className="border-neutral-700 text-neutral-300">
            {formatCost(report.cost_usd)}
          </Badge>
        )}
        {report.primary_language && (
          <Badge variant="outline" className="border-neutral-700 text-neutral-300">
            {report.primary_language}
          </Badge>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-center gap-2">
        <Button
          size="sm"
          className="bg-emerald-600 hover:bg-emerald-700 text-white"
          onClick={handleFix}
          disabled={fixing || fixAttemptStatus === 'running' || fixAttemptStatus === 'pending'}
        >
          {fixing ? (
            <Loader2 className="size-4 mr-1.5 animate-spin" />
          ) : (
            <Wrench className="size-4 mr-1.5" />
          )}
          Fix with FORGE
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="border-neutral-700 text-neutral-300 hover:text-neutral-100"
          onClick={() => downloadJson(report, repoName)}
        >
          <Download className="size-4 mr-1.5" />
          JSON
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="border-neutral-700 text-neutral-300 hover:text-neutral-100"
          onClick={() => downloadMarkdown(report, repoName)}
        >
          <FileText className="size-4 mr-1.5" />
          Markdown
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="border-neutral-700 text-neutral-300 hover:text-neutral-100"
          onClick={() => window.print()}
        >
          <Printer className="size-4 mr-1.5" />
          Save as PDF
        </Button>

        <Button
          variant="outline"
          size="sm"
          className="border-neutral-700 text-neutral-300 hover:text-neutral-100"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="size-4 mr-1.5 text-emerald-400" />
          ) : (
            <Copy className="size-4 mr-1.5" />
          )}
          {copied ? "Copied!" : "Copy Report"}
        </Button>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="border-neutral-700 text-red-400 hover:text-red-300 hover:border-red-700"
              disabled={deleting}
            >
              {deleting ? (
                <Loader2 className="size-4 mr-1.5 animate-spin" />
              ) : (
                <Trash2 className="size-4 mr-1.5" />
              )}
              Delete Scan
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="bg-neutral-900 border-neutral-800">
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
              <AlertDialogDescription className="text-neutral-400">
                This will permanently delete the scan report and all associated
                data. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="border-neutral-700">
                Cancel
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {fixAttemptStatus === 'success' && (
        <Link
          href={`/scan/${scanId}/remediation/results`}
          className="text-emerald-400 hover:text-emerald-300 text-sm underline"
        >
          View Remediation Results →
        </Link>
      )}
    </div>
  )
}
