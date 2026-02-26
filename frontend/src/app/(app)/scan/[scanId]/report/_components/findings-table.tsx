"use client"

import { useState } from "react"
import type { DiscoveryFinding, Severity } from "@/lib/api/types"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { severityClasses, CATEGORY_LABELS } from "./report-utils"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"]

interface FindingsTableProps {
  findings: DiscoveryFinding[]
}

export function FindingsTable({ findings }: FindingsTableProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const sorted = [...findings].sort((a, b) => {
    const ai = SEVERITY_ORDER.indexOf(a.severity)
    const bi = SEVERITY_ORDER.indexOf(b.severity)
    if (ai !== bi) return ai - bi
    return a.tier - b.tier
  })

  function toggleRow(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <Card className="bg-neutral-900 border-neutral-800 p-5">
      <h2 className="text-lg font-semibold text-neutral-100 mb-4">
        All Findings ({findings.length})
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-800 text-neutral-500 text-xs">
              <th className="text-left py-2 pr-3 w-20">Severity</th>
              <th className="text-left py-2 pr-3">Title</th>
              <th className="text-left py-2 pr-3 w-28">Category</th>
              <th className="text-left py-2 pr-3 w-48">Locations</th>
              <th className="text-left py-2 w-24">Agent</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((finding) => {
              const sev = severityClasses(finding.severity)
              const isExpanded = expandedIds.has(finding.id)

              return (
                <FindingRows
                  key={finding.id}
                  finding={finding}
                  sev={sev}
                  isExpanded={isExpanded}
                  onToggle={() => toggleRow(finding.id)}
                />
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

interface FindingRowsProps {
  finding: DiscoveryFinding
  sev: { label: string; bg: string; text: string; border: string }
  isExpanded: boolean
  onToggle: () => void
}

function FindingRows({ finding, sev, isExpanded, onToggle }: FindingRowsProps) {
  return (
    <>
      <tr
        className="border-b border-neutral-800/50 cursor-pointer hover:bg-neutral-800/30 transition-colors"
        onClick={onToggle}
      >
        <td className="py-2.5 pr-3">
          <Badge
            className={`${sev.bg} ${sev.text} ${sev.border} border text-[10px] px-1.5 py-0`}
          >
            {sev.label}
          </Badge>
        </td>
        <td className="py-2.5 pr-3 text-neutral-200">{finding.title}</td>
        <td className="py-2.5 pr-3 text-neutral-400 text-xs">
          {CATEGORY_LABELS[finding.category] ?? finding.category}
        </td>
        <td className="py-2.5 pr-3">
          <div className="flex flex-col gap-0.5">
            {finding.locations.slice(0, 2).map((loc, i) => (
              <span key={i} className="text-xs text-neutral-500 font-mono truncate max-w-[12rem] block">
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
        <td className="py-2.5 text-xs text-neutral-500">{finding.agent}</td>
      </tr>

      {isExpanded && (
        <tr className="border-b border-neutral-800/50">
          <td colSpan={5} className="px-4 py-4 bg-neutral-950/40">
            <div className="space-y-4">
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
                        className="rounded border border-neutral-800 bg-neutral-950/50 p-3"
                      >
                        <p className="text-xs text-neutral-400 font-mono mb-1">
                          {loc.file_path}
                          {loc.line_start != null && `:${loc.line_start}`}
                          {loc.line_end != null && loc.line_end !== loc.line_start && `-${loc.line_end}`}
                        </p>
                        {loc.snippet && (
                          <pre className="text-xs text-neutral-500 whitespace-pre-wrap overflow-x-auto">
                            {loc.snippet}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
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
