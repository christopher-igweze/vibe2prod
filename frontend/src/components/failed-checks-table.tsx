"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronRight } from "lucide-react"
import type { DeterministicChecks, FailedCheck } from "@/lib/api/types"

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  info: "bg-slate-500/10 text-slate-400 border-slate-500/20",
}

const DOMAIN_MAP: Record<string, string> = {
  SEC: "Security",
  REL: "Reliability",
  MNT: "Maintainability",
  TST: "Test Quality",
  PRF: "Performance",
  DOC: "Documentation",
  OPS: "Operations",
}

const DOMAIN_ORDER = ["SEC", "REL", "MNT", "TST", "PRF", "DOC", "OPS"]

function getDomain(checkId: string): string {
  const prefix = checkId.split("-")[0]
  return prefix in DOMAIN_MAP ? prefix : "OTHER"
}

function groupByDomain(checks: FailedCheck[]): Record<string, FailedCheck[]> {
  const groups: Record<string, FailedCheck[]> = {}
  for (const check of checks) {
    const domain = getDomain(check.check_id)
    if (!groups[domain]) groups[domain] = []
    groups[domain].push(check)
  }
  return groups
}

function DomainGroup({ domain, checks }: { domain: string; checks: FailedCheck[] }) {
  const [open, setOpen] = useState(false)
  const label = DOMAIN_MAP[domain] || domain
  const totalDeduction = checks.reduce((sum, c) => sum + c.deduction, 0)

  return (
    <div className="border border-white/[0.06] rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-3 py-2 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          {open ? <ChevronDown className="size-3.5 text-[#4E586E]" /> : <ChevronRight className="size-3.5 text-[#4E586E]" />}
          <span className="text-sm font-medium text-[#E8ECF4]">{label}</span>
          <span className="text-xs text-[#4E586E]">{checks.length} failed</span>
        </div>
        <span className="text-xs font-mono text-red-400">{totalDeduction}</span>
      </button>

      {open && (
        <div className="border-t border-white/[0.06] divide-y divide-white/[0.04]">
          {checks.map((check) => (
            <div
              key={check.check_id}
              className="flex items-start gap-3 px-3 py-2.5 text-sm"
            >
              <Badge variant="outline" className={`shrink-0 ${SEVERITY_COLORS[check.severity] || "text-[#8692A8]"}`}>
                {check.severity}
              </Badge>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <code className="text-xs text-[#4E586E] font-mono">{check.check_id}</code>
                  <span className="text-[#E8ECF4]">{check.name}</span>
                  <span className="text-xs text-red-400 ml-auto shrink-0">{check.deduction}</span>
                </div>
                {check.details && (
                  <p className="text-xs text-[#8692A8] mt-0.5">{check.details}</p>
                )}
                {check.locations && check.locations.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {check.locations.map((loc, i) => (
                      <code key={i} className="text-xs text-[#4E586E] bg-white/[0.03] px-1.5 py-0.5 rounded font-mono">
                        {loc.file}{loc.line ? `:${loc.line}` : ""}
                      </code>
                    ))}
                  </div>
                )}
                {check.fix_guidance && (
                  <p className="text-xs text-emerald-400/70 mt-1">
                    Fix: {check.fix_guidance}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function FailedChecksTable({ checks }: { checks: DeterministicChecks }) {
  const [expanded, setExpanded] = useState(false)

  if (checks.failed === 0) return null

  const grouped = groupByDomain(checks.failed_checks)
  const sortedDomains = DOMAIN_ORDER.filter((d) => grouped[d]?.length > 0)

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
        <div className="flex items-center gap-3 text-xs">
          <span className="text-emerald-400">{checks.passed} passed</span>
          <span className="text-red-400">{checks.failed} failed</span>
          <span className="text-[#4E586E]">across {sortedDomains.length} dimensions</span>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2">
          {sortedDomains.map((domain) => (
            <DomainGroup key={domain} domain={domain} checks={grouped[domain]} />
          ))}
        </div>
      )}
    </Card>
  )
}
