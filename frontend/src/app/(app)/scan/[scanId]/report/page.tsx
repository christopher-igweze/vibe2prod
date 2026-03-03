"use client"

export const dynamic = "force-dynamic"

import { useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { ArrowLeft, Loader2, AlertCircle, Copy, Check } from "lucide-react"

import { apiFetch, ApiError } from "@/lib/api/client"
import type { DiscoveryReport, Severity } from "@/lib/api/types"
import { reportToMarkdown } from "@/lib/report/to-markdown"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import { ReportHeader } from "./_components/report-header"
import { SeveritySummary } from "./_components/severity-summary"
import { ArchitectureContext } from "./_components/architecture-context"
import { FindingsTable } from "./_components/findings-table"
import { RemediationPlan } from "./_components/remediation-plan"

/* ---------- types ---------- */

interface ScanDetail {
  id: string
  status: string
  repo_url?: string
  repo_name?: string
  report_data?: {
    discovery_report?: DiscoveryReport
  }
}

type FixStatus = 'pending' | 'running' | 'success' | 'failed'

interface ScanFixStatus {
  status: FixStatus
}

/* ---------- page ---------- */

export default function ReportPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const { getToken } = useAuth()
  const router = useRouter()

  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [fixAttemptStatus, setFixAttemptStatus] = useState<FixStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [mdCopied, setMdCopied] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanDetail>(
          `/api/user/scans/${scanId}`,
          { token },
        )
        setScan(data)

        // Fetch fix status (404 = no fix attempt yet, which is fine)
        try {
          const fixData = await apiFetch<ScanFixStatus>(
            `/api/fix-scan/${scanId}/status`,
            { token },
          )
          setFixAttemptStatus(fixData.status)
        } catch (e) {
          if (e instanceof ApiError && e.status === 404) {
            // No fix attempt — leave as null
          }
          // Silently ignore other errors for fix status
        }
      } catch {
        setError("Failed to load scan report.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scanId, getToken])

  const report = scan?.report_data?.discovery_report ?? null

  // useMemo must be called unconditionally (React rules of hooks)
  const markdown = useMemo(
    () => (report ? reportToMarkdown(report, scan?.repo_name) : ""),
    [report, scan?.repo_name],
  )

  // Split findings: actionable vs intentional/informational
  const actionableFindings = report?.findings.filter(
    (f) => f.intent_signal !== "intentional" && f.actionability !== "informational"
  ) ?? []
  const intentionalFindings = report?.findings.filter(
    (f) => f.intent_signal === "intentional" || f.actionability === "informational"
  ) ?? []

  // Recompute severity counts from actionable findings only
  const adjustedSeverity: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 }
  for (const f of actionableFindings) {
    if (f.severity in adjustedSeverity) adjustedSeverity[f.severity]++
  }

  /* ---------- loading / error states ---------- */

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="size-6 animate-spin text-neutral-500" />
      </div>
    )
  }

  if (error || !scan) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="size-8 text-red-400 mx-auto" />
        <p className="text-neutral-400">{error || "Scan not found."}</p>
        <Link href="/dashboard">
          <Button variant="outline" className="border-neutral-700">
            <ArrowLeft className="size-4 mr-1" /> Back to Dashboard
          </Button>
        </Link>
      </div>
    )
  }

  if (scan.status !== "completed") {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <Loader2 className="size-8 animate-spin text-neutral-500 mx-auto" />
        <p className="text-neutral-400">
          Scan is {scan.status}. Waiting for results...
        </p>
        <Link href={`/scan/${scanId}`}>
          <Button variant="outline" className="border-neutral-700">
            View Progress
          </Button>
        </Link>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
        <AlertCircle className="size-8 text-yellow-400 mx-auto" />
        <p className="text-neutral-400">
          No discovery report data available for this scan.
        </p>
        <Link href="/dashboard">
          <Button variant="outline" className="border-neutral-700">
            <ArrowLeft className="size-4 mr-1" /> Back to Dashboard
          </Button>
        </Link>
      </div>
    )
  }

  async function handleCopyMarkdown() {
    try {
      await navigator.clipboard.writeText(markdown)
      setMdCopied(true)
      setTimeout(() => setMdCopied(false), 2000)
    } catch {
      // Clipboard API unavailable
    }
  }

  /* ---------- render report ---------- */

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-16">
      {/* Navigation */}
      <Link href="/dashboard">
        <Button variant="ghost" size="sm" className="text-neutral-400 hover:text-neutral-200 -ml-2">
          <ArrowLeft className="size-4 mr-1" /> Dashboard
        </Button>
      </Link>

      {/* Header */}
      <ReportHeader
        report={report}
        repoName={scan.repo_name}
        scanId={scanId}
        actionableCount={actionableFindings.length}
        fixAttemptStatus={fixAttemptStatus}
      />

      {/* Tabbed content: Report / Markdown */}
      <Tabs defaultValue="report">
        <TabsList className="bg-neutral-900 border border-neutral-800">
          <TabsTrigger
            value="report"
            className="data-[state=active]:bg-neutral-800 data-[state=active]:text-neutral-100 text-neutral-400"
          >
            Report
          </TabsTrigger>
          <TabsTrigger
            value="markdown"
            className="data-[state=active]:bg-neutral-800 data-[state=active]:text-neutral-100 text-neutral-400"
          >
            Markdown
          </TabsTrigger>
        </TabsList>

        <TabsContent value="report" className="space-y-6 mt-4">
          {/* Severity Summary — only actionable findings */}
          <SeveritySummary
            breakdown={adjustedSeverity}
            actionabilitySummary={report.actionability_summary}
          />

          {/* Architecture Context */}
          {report.codebase_map && (
            <ArchitectureContext
              map={report.codebase_map}
              findings={actionableFindings}
            />
          )}

          {/* Findings Table — grouped by actionability */}
          {report.findings.length > 0 && (
            <FindingsTable
              actionableFindings={actionableFindings}
              intentionalFindings={intentionalFindings}
            />
          )}

          {/* Remediation Plan */}
          {report.remediation_plan && report.remediation_plan.items.length > 0 && (
            <RemediationPlan plan={report.remediation_plan} />
          )}

          {/* Empty state */}
          {actionableFindings.length === 0 && intentionalFindings.length === 0 && (
            <Card className="bg-neutral-900 border-neutral-800 p-12 text-center">
              <p className="text-neutral-400">No findings detected. Your codebase looks clean!</p>
            </Card>
          )}

        </TabsContent>

        <TabsContent value="markdown" className="mt-4">
          <div className="relative">
            <Button
              variant="outline"
              size="sm"
              className="absolute top-3 right-3 border-neutral-700 text-neutral-300 hover:text-neutral-100 z-10"
              onClick={handleCopyMarkdown}
            >
              {mdCopied ? (
                <Check className="size-4 mr-1.5 text-emerald-400" />
              ) : (
                <Copy className="size-4 mr-1.5" />
              )}
              {mdCopied ? "Copied!" : "Copy Markdown"}
            </Button>
            <pre className="bg-neutral-900 border border-neutral-800 rounded-lg p-6 pt-14 overflow-auto max-h-[80vh] font-mono text-sm text-neutral-300 whitespace-pre-wrap">
              {markdown}
            </pre>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
