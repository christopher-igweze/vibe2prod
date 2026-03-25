"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import {
  Download,
  FileText,
  Printer,
  Trash2,
  Loader2,
  Copy,
  Check,
  MoreHorizontal,
} from "lucide-react"

import type { DiscoveryReport, EvaluationReport, AIVSSScore } from "@/lib/api/types"
import { reportToMarkdown } from "@/lib/report/to-markdown"
import { openPdfReport } from "@/lib/report/to-pdf-html"
import { apiFetch, sanitizeFilename } from "@/lib/api/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { formatDuration, formatCharge } from "./report-utils"

interface ReportHeaderProps {
  report: DiscoveryReport
  repoName?: string
  scanId: string
  actionableCount?: number
  evaluation?: EvaluationReport | null
  aivss?: AIVSSScore | null
}

function downloadJson(report: DiscoveryReport, repoName?: string) {
  const slug = sanitizeFilename((repoName || "repo").replace(/\//g, "-"))
  const date = new Date().toISOString().slice(0, 10)
  const filename = `scan-report-${slug}-${date}.json`

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

function downloadMarkdown(
  report: DiscoveryReport,
  repoName?: string,
  evaluation?: EvaluationReport | null,
  aivss?: AIVSSScore | null,
) {
  const slug = sanitizeFilename((repoName || "repo").replace(/\//g, "-"))
  const date = new Date().toISOString().slice(0, 10)
  const filename = `scan-report-${slug}-${date}.md`

  const md = reportToMarkdown(report, repoName, evaluation, aivss)
  const blob = new Blob([md], { type: "text/markdown" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ReportHeader({ report, repoName, scanId, actionableCount, evaluation, aivss }: ReportHeaderProps) {
  const router = useRouter()
  const { getToken } = useAuth()
  const [deleting, setDeleting] = useState(false)
  const [copied, setCopied] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const formattedDate = report.generated_at
    ? new Date(report.generated_at).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : ""

  async function handleCopy() {
    try {
      const md = reportToMarkdown(report, repoName, evaluation, aivss)
      await navigator.clipboard.writeText(md)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard API unavailable
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
    <div className="flex items-start justify-between gap-4">
      <div className="space-y-2 min-w-0">
        <h1 className="text-2xl font-bold text-[#E8ECF4] font-[family-name:var(--font-heading)]">
          Scan Report
        </h1>
        {repoName && (
          <p className="text-[#8692A8] text-sm truncate">{repoName}</p>
        )}
        <p className="text-[#4E586E] text-xs">{formattedDate}</p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {/* Inline stat badges */}
        <div className="hidden md:flex items-center gap-2 text-xs">
          <Badge variant="outline" className="border-white/[0.08] text-[#E8ECF4]">
            {actionableCount ?? report.total_findings ?? 0} findings
          </Badge>
          {report.loc_total != null && (
            <Badge variant="outline" className="border-white/[0.08] text-[#E8ECF4]">
              {report.loc_total.toLocaleString()} LOC
            </Badge>
          )}
          {report.duration_seconds != null && (
            <Badge variant="outline" className="border-white/[0.08] text-[#E8ECF4]">
              {formatDuration(report.duration_seconds)}
            </Badge>
          )}
          {report.cost_usd > 0 && (
            <Badge variant="outline" className="border-forge-emerald/30 text-forge-emerald">
              Cost: {formatCharge(report.cost_usd)}
            </Badge>
          )}
        </div>

        {/* Actions dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="border-white/[0.08] text-[#8692A8] hover:text-[#E8ECF4]"
            >
              <MoreHorizontal className="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={() => downloadJson(report, repoName)}>
              <Download className="size-4 mr-2" />
              Download JSON
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => downloadMarkdown(report, repoName, evaluation, aivss)}>
              <FileText className="size-4 mr-2" />
              Download Markdown
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => openPdfReport(report, repoName, evaluation, aivss)}>
              <Printer className="size-4 mr-2" />
              Save as PDF
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleCopy}>
              {copied ? (
                <Check className="size-4 mr-2 text-forge-emerald" />
              ) : (
                <Copy className="size-4 mr-2" />
              )}
              {copied ? "Copied!" : "Copy Report"}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-red-400 focus:text-red-400"
              onClick={() => setDeleteOpen(true)}
              disabled={deleting}
            >
              {deleting ? (
                <Loader2 className="size-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="size-4 mr-2" />
              )}
              Delete Scan
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <AlertDialogContent className="bg-forge-surface border-white/[0.06]">
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
              <AlertDialogDescription className="text-[#8692A8]">
                This will permanently delete the scan report and all associated
                data. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="border-white/[0.08]">
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
    </div>
  )
}
