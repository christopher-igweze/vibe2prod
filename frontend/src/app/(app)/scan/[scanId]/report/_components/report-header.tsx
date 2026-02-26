import type { DiscoveryReport } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"
import { formatDuration, formatCost } from "./report-utils"

interface ReportHeaderProps {
  report: DiscoveryReport
  repoName?: string
}

export function ReportHeader({ report, repoName }: ReportHeaderProps) {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-neutral-100">
          FORGE Discovery Report
        </h1>
        {repoName && (
          <p className="text-neutral-400 text-sm mt-1">{repoName}</p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <Badge variant="outline" className="border-neutral-700 text-neutral-400">
          {report.total_findings} findings
        </Badge>
        <Badge variant="outline" className="border-neutral-700 text-neutral-400">
          {formatDuration(report.duration_seconds)}
        </Badge>
        {report.cost_usd > 0 && (
          <Badge variant="outline" className="border-neutral-700 text-neutral-400">
            {formatCost(report.cost_usd)}
          </Badge>
        )}
        {report.primary_language && (
          <Badge variant="outline" className="border-neutral-700 text-neutral-400">
            {report.primary_language}
          </Badge>
        )}
        <span className="text-neutral-600">|</span>
        <span className="text-neutral-500 font-mono">
          {report.run_id}
        </span>
        <span className="text-neutral-600">|</span>
        <span className="text-neutral-500">
          {new Date(report.generated_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  )
}
