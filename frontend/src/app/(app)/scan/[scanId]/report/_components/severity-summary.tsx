"use client"

import type { ActionabilitySummary, Severity } from "@/lib/api/types"
import { severityClasses, ACTIONABILITY_CONFIG } from "./report-utils"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"]

interface SeveritySummaryProps {
  breakdown: Record<Severity, number>
  actionabilitySummary?: ActionabilitySummary | null
}

export function SeveritySummary({ breakdown, actionabilitySummary }: SeveritySummaryProps) {
  return (
    <div className="space-y-3">
      {/* Actionability row — the numbers that matter */}
      {actionabilitySummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {([
            { key: "must_fix_count" as const, actionability: "must_fix" as const },
            { key: "should_fix_count" as const, actionability: "should_fix" as const },
            { key: "consider_count" as const, actionability: "consider" as const },
            { key: "informational_count" as const, actionability: "informational" as const },
          ]).map(({ key, actionability }) => {
            const cfg = ACTIONABILITY_CONFIG[actionability]
            const count = actionabilitySummary[key] ?? 0
            return (
              <div
                key={actionability}
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
      )}

      {/* Severity row — secondary context */}
      <div className="grid grid-cols-4 gap-2">
        {SEVERITY_ORDER.map((sev) => {
          const cfg = severityClasses(sev)
          const count = breakdown[sev] ?? 0
          return (
            <div
              key={sev}
              className={`rounded border ${cfg.border} ${cfg.bg} px-3 py-2 text-center`}
            >
              <p className={`text-lg font-semibold ${cfg.text}`}>{count}</p>
              <p className={`text-[10px] uppercase tracking-wider ${cfg.text} opacity-70`}>
                {cfg.label}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
