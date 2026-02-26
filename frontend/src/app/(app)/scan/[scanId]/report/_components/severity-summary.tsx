import type { Severity } from "@/lib/api/types"
import { severityClasses } from "./report-utils"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"]

interface SeveritySummaryProps {
  breakdown: Record<Severity, number>
}

export function SeveritySummary({ breakdown }: SeveritySummaryProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {SEVERITY_ORDER.map((sev) => {
        const cfg = severityClasses(sev)
        const count = breakdown[sev] ?? 0
        return (
          <div
            key={sev}
            className={`rounded-lg border ${cfg.border} ${cfg.bg} p-4 text-center`}
          >
            <p className={`text-3xl font-bold ${cfg.text}`}>{count}</p>
            <p className={`text-xs uppercase tracking-wider mt-1 ${cfg.text} opacity-80`}>
              {cfg.label}
            </p>
          </div>
        )
      })}
    </div>
  )
}
