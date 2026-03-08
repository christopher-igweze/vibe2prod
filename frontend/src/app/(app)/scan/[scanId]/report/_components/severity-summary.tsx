"use client"

import type { ActionabilitySummary } from "@/lib/api/types"
import { ACTIONABILITY_CONFIG } from "./report-utils"

interface SeveritySummaryProps {
  actionabilitySummary?: ActionabilitySummary | null
}

export function SeveritySummary({ actionabilitySummary }: SeveritySummaryProps) {
  if (!actionabilitySummary) return null

  return (
    <div className="grid grid-cols-4 gap-2">
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
            className={`rounded-lg forge-glass border ${cfg.border} px-3 py-2.5 text-center`}
          >
            <p className={`text-xl font-bold font-[family-name:var(--font-heading)] ${cfg.text}`}>{count}</p>
            <p className={`text-[10px] uppercase tracking-wider mt-0.5 ${cfg.text} opacity-80`}>
              {cfg.label}
            </p>
          </div>
        )
      })}
    </div>
  )
}
