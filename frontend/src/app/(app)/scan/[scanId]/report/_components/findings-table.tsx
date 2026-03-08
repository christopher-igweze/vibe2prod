"use client"

import { useMemo, useState } from "react"
import { ChevronDown, ChevronRight, Eye, EyeOff } from "lucide-react"
import type { Actionability, Category, DiscoveryFinding, Severity } from "@/lib/api/types"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { severityClasses, actionabilityClasses, CATEGORY_LABELS, SEVERITY_CONFIG } from "./report-utils"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"]
const ACTIONABILITY_ORDER: Actionability[] = ["must_fix", "should_fix", "consider"]
const ALL_CATEGORIES: Category[] = ["security", "architecture", "quality", "reliability", "performance"]

function sortFindings(findings: DiscoveryFinding[]) {
  return [...findings].sort((a, b) => {
    const ai = SEVERITY_ORDER.indexOf(a.severity)
    const bi = SEVERITY_ORDER.indexOf(b.severity)
    if (ai !== bi) return ai - bi
    return (a.tier ?? 2) - (b.tier ?? 2)
  })
}

interface FindingsTableProps {
  actionableFindings: DiscoveryFinding[]
  intentionalFindings: DiscoveryFinding[]
}

export function FindingsTable({ actionableFindings, intentionalFindings }: FindingsTableProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(["consider"]) // consider collapsed by default
  )
  const [showIntentional, setShowIntentional] = useState(false)

  // Filter state — all active by default
  const [severityFilter, setSeverityFilter] = useState<Set<Severity>>(
    () => new Set(SEVERITY_ORDER)
  )
  const [categoryFilter, setCategoryFilter] = useState<Set<Category>>(
    () => new Set(ALL_CATEGORIES)
  )

  function toggleSeverity(s: Severity) {
    setSeverityFilter((prev) => {
      const next = new Set(prev)
      next.has(s) ? next.delete(s) : next.add(s)
      return next
    })
  }

  function toggleCategory(c: Category) {
    setCategoryFilter((prev) => {
      const next = new Set(prev)
      next.has(c) ? next.delete(c) : next.add(c)
      return next
    })
  }

  // Apply filters
  const filteredActionable = useMemo(
    () =>
      actionableFindings.filter(
        (f) => severityFilter.has(f.severity) && categoryFilter.has(f.category)
      ),
    [actionableFindings, severityFilter, categoryFilter]
  )

  // Group filtered actionable findings by actionability
  const groups: Record<string, DiscoveryFinding[]> = {}
  for (const a of ACTIONABILITY_ORDER) {
    groups[a] = []
  }
  for (const f of filteredActionable) {
    const key = f.actionability ?? "consider"
    if (!groups[key]) groups[key] = []
    groups[key].push(f)
  }

  function toggleRow(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleGroup(group: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev)
      next.has(group) ? next.delete(group) : next.add(group)
      return next
    })
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 px-1">
        {/* Severity filters */}
        {SEVERITY_ORDER.map((s) => {
          const cfg = SEVERITY_CONFIG[s]
          const active = severityFilter.has(s)
          return (
            <button
              key={s}
              onClick={() => toggleSeverity(s)}
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                active
                  ? `${cfg.bg} ${cfg.text} ${cfg.border}`
                  : "bg-forge-nav text-forge-text-muted border-forge-surface-hover"
              }`}
            >
              {cfg.label}
            </button>
          )
        })}

        <span className="w-px h-4 bg-forge-surface-hover" />

        {/* Category filters */}
        {ALL_CATEGORIES.map((c) => {
          const active = categoryFilter.has(c)
          return (
            <button
              key={c}
              onClick={() => toggleCategory(c)}
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                active
                  ? "bg-forge-surface-hover text-neutral-200 border-forge-border-hover"
                  : "bg-forge-nav text-forge-text-muted border-forge-surface-hover"
              }`}
            >
              {CATEGORY_LABELS[c] ?? c}
            </button>
          )
        })}
      </div>

      {/* Actionable findings grouped by actionability */}
      {ACTIONABILITY_ORDER.map((level) => {
        const findings = groups[level] ?? []
        if (findings.length === 0) return null

        const cfg = actionabilityClasses(level)
        const isCollapsed = collapsedGroups.has(level)
        const sorted = sortFindings(findings)

        return (
          <Card key={level} className="forge-glass rounded-lg overflow-hidden">
            {/* Group header */}
            <button
              className={`w-full flex items-center gap-3 px-5 py-3 border-b ${cfg.border} hover:bg-forge-surface-hover/30 transition-colors`}
              onClick={() => toggleGroup(level)}
            >
              {isCollapsed ? (
                <ChevronRight className={`size-4 ${cfg.text}`} />
              ) : (
                <ChevronDown className={`size-4 ${cfg.text}`} />
              )}
              <Badge className={`${cfg.bg} ${cfg.text} ${cfg.border} border text-xs px-2 py-0`}>
                {cfg.label}
              </Badge>
              <span className="text-sm text-neutral-400">
                {findings.length} {findings.length === 1 ? "finding" : "findings"}
              </span>
            </button>

            {/* Findings table */}
            {!isCollapsed && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/6 text-forge-text-muted text-xs">
                      <th className="text-left py-2 pl-5 pr-3 w-20">Severity</th>
                      <th className="text-left py-2 pr-3">Title</th>
                      <th className="text-left py-2 pr-3 w-28">Category</th>
                      <th className="text-left py-2 pr-3 w-48">Locations</th>
                      <th className="text-left py-2 pr-5 w-24">Agent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map((finding) => (
                      <FindingRow
                        key={finding.id}
                        finding={finding}
                        isExpanded={expandedIds.has(finding.id)}
                        onToggle={() => toggleRow(finding.id)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )
      })}

      {/* Intentional / Informational — collapsed by default */}
      {intentionalFindings.length > 0 && (
        <Card className="forge-glass rounded-lg opacity-80">
          <button
            className="w-full flex items-center gap-3 px-5 py-3 hover:bg-forge-surface-hover/20 transition-colors"
            onClick={() => setShowIntentional((v) => !v)}
          >
            {showIntentional ? (
              <EyeOff className="size-4 text-neutral-600" />
            ) : (
              <Eye className="size-4 text-neutral-600" />
            )}
            <span className="text-sm text-neutral-500">
              {intentionalFindings.length} intentional {intentionalFindings.length === 1 ? "pattern" : "patterns"} hidden
            </span>
            <span className="text-xs text-neutral-600 ml-auto">
              {showIntentional ? "Click to hide" : "Click to show"}
            </span>
          </button>

          {showIntentional && (
            <div className="overflow-x-auto border-t border-white/6">
              <table className="w-full text-sm opacity-60">
                <thead>
                  <tr className="border-b border-white/4 text-forge-text-muted text-xs">
                    <th className="text-left py-2 pl-5 pr-3 w-20">Severity</th>
                    <th className="text-left py-2 pr-3">Title</th>
                    <th className="text-left py-2 pr-3 w-28">Category</th>
                    <th className="text-left py-2 pr-3 w-48">Locations</th>
                    <th className="text-left py-2 pr-5 w-24">Agent</th>
                  </tr>
                </thead>
                <tbody>
                  {sortFindings(intentionalFindings).map((finding) => (
                    <FindingRow
                      key={finding.id}
                      finding={finding}
                      isExpanded={expandedIds.has(finding.id)}
                      onToggle={() => toggleRow(finding.id)}
                      muted
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Empty state for actionable */}
      {actionableFindings.length === 0 && intentionalFindings.length > 0 && (
        <Card className="forge-glass rounded-lg p-8 text-center">
          <p className="text-neutral-400 text-sm">
            No actionable findings — all {intentionalFindings.length} detected patterns appear intentional.
          </p>
        </Card>
      )}
    </div>
  )
}

/* ── Individual finding row ─────────────────────────────────────── */

interface FindingRowProps {
  finding: DiscoveryFinding
  isExpanded: boolean
  onToggle: () => void
  muted?: boolean
}

function FindingRow({ finding, isExpanded, onToggle, muted }: FindingRowProps) {
  const sev = severityClasses(finding.severity)
  const textColor = muted ? "text-neutral-500" : "text-neutral-200"

  return (
    <>
      <tr
        className="border-b border-white/6 cursor-pointer hover:bg-forge-surface-hover/30 transition-colors"
        onClick={onToggle}
      >
        <td className="py-2.5 pl-5 pr-3">
          <Badge
            className={`${sev.bg} ${sev.text} ${sev.border} border text-[10px] px-1.5 py-0 ${muted ? "opacity-50" : ""}`}
          >
            {sev.label}
          </Badge>
        </td>
        <td className={`py-2.5 pr-3 ${textColor}`}>{finding.title}</td>
        <td className="py-2.5 pr-3 text-neutral-400 text-xs">
          {CATEGORY_LABELS[finding.category] ?? finding.category}
        </td>
        <td className="py-2.5 pr-3">
          <div className="flex flex-col gap-0.5">
            {finding.locations.slice(0, 2).map((loc, i) => (
              <span key={i} className="text-xs text-neutral-500 font-[family-name:var(--font-code)] truncate max-w-[12rem] block">
                {loc.file_path}
                {loc.line_start != null && `:${loc.line_start}`}
              </span>
            ))}
            {finding.locations.length > 2 && (
              <span className="text-xs text-neutral-600">
                +{finding.locations.length - 2} more
              </span>
            )}
          </div>
        </td>
        <td className="py-2.5 pr-5 text-xs text-neutral-500">{finding.agent}</td>
      </tr>

      {isExpanded && (
        <tr className="border-b border-white/6">
          <td colSpan={5} className="px-5 py-4 bg-forge-surface/60">
            <div className="space-y-4">
              {/* Pattern ID + Intent signal badges */}
              <div className="flex items-center gap-2 flex-wrap">
                {finding.pattern_id && (
                  <Badge variant="outline" className="font-[family-name:var(--font-code)] text-xs border-forge-surface-hover text-neutral-400">
                    {finding.pattern_id}
                  </Badge>
                )}
                {finding.intent_signal && (
                  <Badge
                    variant="outline"
                    className={
                      finding.intent_signal === "intentional"
                        ? "border-forge-text-muted text-neutral-500 text-xs"
                        : "border-forge-surface-hover text-neutral-400 text-xs"
                    }
                  >
                    Intent: {finding.intent_signal}
                  </Badge>
                )}
                {finding.actionability && (
                  <Badge
                    variant="outline"
                    className="border-forge-surface-hover text-neutral-400 text-xs"
                  >
                    {finding.actionability.replace("_", " ")}
                  </Badge>
                )}
              </div>

              {/* Description */}
              <div>
                <h4 className="text-xs font-medium text-neutral-500 mb-1">Description</h4>
                <p className="text-sm text-neutral-300 leading-relaxed">
                  {finding.description}
                </p>
              </div>

              {/* Suggested Fix */}
              {finding.suggested_fix && (
                <div>
                  <h4 className="text-xs font-medium text-neutral-500 mb-1">Suggested Fix</h4>
                  <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
                    {finding.suggested_fix}
                  </p>
                </div>
              )}

              {/* Locations with snippets */}
              {finding.locations.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-neutral-500 mb-1.5">Locations</h4>
                  <div className="space-y-2">
                    {finding.locations.map((loc, i) => (
                      <div
                        key={i}
                        className="rounded border border-white/6 bg-forge-surface/50 p-3"
                      >
                        <p className="text-xs text-neutral-400 font-[family-name:var(--font-code)] mb-1">
                          {loc.file_path}
                          {loc.line_start != null && `:${loc.line_start}`}
                          {loc.line_end != null && loc.line_end !== loc.line_start && `-${loc.line_end}`}
                        </p>
                        {loc.snippet && (
                          <pre className="text-xs text-neutral-500 font-[family-name:var(--font-code)] whitespace-pre-wrap overflow-x-auto">
                            {loc.snippet}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Data flow */}
              {finding.data_flow && (
                <div>
                  <h4 className="text-xs font-medium text-neutral-500 mb-1">Data Flow</h4>
                  <p className="text-xs text-neutral-400 font-[family-name:var(--font-code)]">{finding.data_flow}</p>
                </div>
              )}

              {/* Meta info */}
              <div className="flex flex-wrap gap-3 text-xs text-neutral-500">
                {finding.confidence > 0 && (
                  <span>Confidence: {Math.round(finding.confidence * 100)}%</span>
                )}
                {finding.cwe_id && <span>{finding.cwe_id}</span>}
                {finding.owasp_ref && <span>{finding.owasp_ref}</span>}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
