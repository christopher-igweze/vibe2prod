"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronRight } from "lucide-react"
import type { DeterministicChecks } from "@/lib/api/types"

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
}

export function FailedChecksTable({ checks }: { checks: DeterministicChecks }) {
  const [expanded, setExpanded] = useState(false)

  if (checks.failed === 0) return null

  return (
    <Card className="forge-glass-card p-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center gap-2">
          {expanded ? <ChevronDown className="size-4 text-[#8692A8]" /> : <ChevronRight className="size-4 text-[#8692A8]" />}
          <h3 className="text-sm font-medium text-[#E8ECF4]">Deterministic Checks</h3>
        </div>
        <div className="flex items-center gap-2 text-xs text-[#8692A8]">
          <span className="text-emerald-400">{checks.passed} passed</span>
          <span className="text-[#4E586E]">/</span>
          <span className="text-red-400">{checks.failed} failed</span>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2">
          {checks.failed_checks.map((check) => (
            <div
              key={check.check_id}
              className="flex items-start gap-3 p-2 rounded-md bg-white/[0.02] text-sm"
            >
              <Badge variant="outline" className={SEVERITY_COLORS[check.severity] || "text-[#8692A8]"}>
                {check.severity}
              </Badge>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <code className="text-xs text-[#4E586E] font-mono">{check.check_id}</code>
                  <span className="text-[#E8ECF4]">{check.name}</span>
                  <span className="text-xs text-red-400 ml-auto shrink-0">{check.deduction}</span>
                </div>
                <p className="text-xs text-[#8692A8] mt-0.5">{check.details}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
