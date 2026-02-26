"use client"

import type { DiscoveryReport } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"
import { formatDuration, formatCost } from "./report-utils"

interface ReportHeaderProps {
  report: DiscoveryReport
  repoName?: string
}

export function ReportHeader({ report, repoName }: ReportHeaderProps) {
  const truncatedRunId = report.run_id.slice(0, 12)
  const formattedDate = new Date(report.generated_at).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })

  return (
    <div className="text-center space-y-4">
      <div>
        <h1 className="text-3xl font-bold text-neutral-100">
          FORGE Discovery Report
        </h1>
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
          {report.total_findings} findings
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
    </div>
  )
}
