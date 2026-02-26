"use client"

import type { RemediationPlan as RemediationPlanType } from "@/lib/api/types"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { tierClasses } from "./report-utils"

interface RemediationPlanProps {
  plan: RemediationPlanType
}

const PRIORITY_COLORS: Record<number, { bg: string; text: string }> = {
  1: { bg: "bg-red-500/10", text: "text-red-400" },
  2: { bg: "bg-orange-500/10", text: "text-orange-400" },
  3: { bg: "bg-yellow-500/10", text: "text-yellow-400" },
  4: { bg: "bg-blue-500/10", text: "text-blue-400" },
  5: { bg: "bg-neutral-500/10", text: "text-neutral-400" },
}

function priorityClasses(priority: number) {
  return PRIORITY_COLORS[priority] ?? PRIORITY_COLORS[5]
}

export function RemediationPlan({ plan }: RemediationPlanProps) {
  // Build a lookup from finding_id -> item for quick access
  const itemMap = new Map(plan.items.map((item) => [item.finding_id, item]))

  // Build a dependency lookup: finding_id -> dependency reasons
  const depLookup = new Map<string, string[]>()
  for (const dep of plan.dependencies) {
    const existing = depLookup.get(dep.finding_id) ?? []
    const depItem = itemMap.get(dep.depends_on_finding_id)
    const label = depItem ? depItem.title : dep.depends_on_finding_id
    existing.push(`${label} (${dep.reason})`)
    depLookup.set(dep.finding_id, existing)
  }

  return (
    <Card className="bg-neutral-900 border-neutral-800 p-5 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-neutral-100">Remediation Plan</h2>
        <p className="text-xs text-neutral-500 mt-1">
          {plan.items.length} items across {plan.execution_levels.length} execution levels
        </p>
      </div>

      {plan.execution_levels.map((levelIds, levelIndex) => {
        const levelItems = levelIds
          .map((id) => itemMap.get(id))
          .filter((item): item is NonNullable<typeof item> => item != null)
          .sort((a, b) => a.priority - b.priority)

        if (levelItems.length === 0) return null

        return (
          <div key={levelIndex}>
            <h3 className="text-sm font-medium text-neutral-400 mb-3">
              Level {levelIndex + 1}
              <span className="text-neutral-600 ml-2 font-normal">
                ({levelItems.length} item{levelItems.length !== 1 ? "s" : ""})
              </span>
            </h3>

            <div className="space-y-3">
              {levelItems.map((item) => {
                const tier = tierClasses(item.tier)
                const prio = priorityClasses(item.priority)
                const deps = depLookup.get(item.finding_id)

                return (
                  <div
                    key={item.finding_id}
                    className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-4 space-y-3"
                  >
                    {/* Header row */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2 flex-wrap min-w-0">
                        <Badge
                          className={`${prio.bg} ${prio.text} border-transparent text-[10px] px-1.5 py-0 shrink-0`}
                        >
                          P{item.priority}
                        </Badge>
                        <Badge
                          className={`${tier.bg} ${tier.text} border-transparent text-[10px] px-1.5 py-0 shrink-0`}
                        >
                          {tier.label}
                        </Badge>
                        {item.group && (
                          <Badge
                            variant="outline"
                            className="border-neutral-700 text-neutral-400 text-[10px] px-1.5 py-0 shrink-0"
                          >
                            {item.group}
                          </Badge>
                        )}
                        <span className="text-sm text-neutral-200">{item.title}</span>
                      </div>
                      <span className="text-xs text-neutral-600 shrink-0 tabular-nums">
                        {item.estimated_files} file{item.estimated_files !== 1 ? "s" : ""}
                      </span>
                    </div>

                    {/* Approach */}
                    {item.approach && (
                      <p className="text-sm text-neutral-400 leading-relaxed">
                        {item.approach}
                      </p>
                    )}

                    {/* Files to modify */}
                    {item.files_to_modify.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-neutral-500 mb-1">Files</h4>
                        <div className="flex flex-wrap gap-1.5">
                          {item.files_to_modify.map((f, i) => (
                            <span
                              key={i}
                              className="text-xs text-neutral-500 font-mono bg-neutral-800/50 rounded px-1.5 py-0.5"
                            >
                              {f}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Acceptance Criteria */}
                    {item.acceptance_criteria.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-neutral-500 mb-1">Acceptance Criteria</h4>
                        <ul className="list-disc list-inside space-y-0.5">
                          {item.acceptance_criteria.map((ac, i) => (
                            <li key={i} className="text-xs text-neutral-400">
                              {ac}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Dependencies */}
                    {deps && deps.length > 0 && (
                      <div className="flex items-start gap-2 text-xs">
                        <span className="text-neutral-600 shrink-0">Depends on:</span>
                        <span className="text-neutral-500">{deps.join(", ")}</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </Card>
  )
}
