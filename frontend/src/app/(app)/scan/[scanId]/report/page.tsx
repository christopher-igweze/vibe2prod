"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { ArrowLeft, Loader2, AlertCircle } from "lucide-react"

import { apiFetch } from "@/lib/api/client"
import type { DiscoveryFinding, DiscoveryReport, Severity } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

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

/* ---------- page ---------- */

export default function ReportPage() {
  const { scanId } = useParams<{ scanId: string }>()
  const { getToken } = useAuth()
  const router = useRouter()

  const [scan, setScan] = useState<ScanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined
        const data = await apiFetch<ScanDetail>(
          `/api/user/scans/${scanId}`,
          { token },
        )
        setScan(data)
      } catch {
        setError("Failed to load scan report.")
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [scanId, getToken])

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

  const report = scan.report_data?.discovery_report

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
      />

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
    </div>
  )
}
