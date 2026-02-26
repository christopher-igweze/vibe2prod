import type { RemediationPlan as RemediationPlanType } from "@/lib/api/types"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { tierClasses } from "./report-utils"

interface RemediationPlanProps {
  plan: RemediationPlanType
}

export function RemediationPlan({ plan }: RemediationPlanProps) {
  const sorted = [...plan.items].sort((a, b) => {
    if (a.priority !== b.priority) return a.priority - b.priority
    return a.tier - b.tier
  })

  const totalLevels = plan.execution_levels.length
  const totalItems = plan.items.length

  return (
    <Card className="bg-neutral-900 border-neutral-800 p-5 space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-neutral-100">Remediation Plan</h2>
        <p className="text-xs text-neutral-500 mt-1">
          {totalItems} items across {totalLevels} execution levels
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-800 text-neutral-500 text-xs">
              <th className="text-left py-2 pr-3 w-16">Priority</th>
              <th className="text-left py-2 pr-3 w-12">Tier</th>
              <th className="text-left py-2 pr-3">Item</th>
              <th className="text-left py-2 w-48">Files</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => {
              const tier = tierClasses(item.tier)
              return (
                <tr key={item.finding_id} className="border-b border-neutral-800/50">
                  <td className="py-2 pr-3">
                    <span className="text-xs text-neutral-400">P{item.priority}</span>
                  </td>
                  <td className="py-2 pr-3">
                    <Badge
                      className={`${tier.bg} ${tier.text} border-transparent text-[10px] px-1.5 py-0`}
                    >
                      {tier.label}
                    </Badge>
                  </td>
                  <td className="py-2 pr-3">
                    <div>
                      <span className="text-neutral-200">{item.title}</span>
                      <span className="text-neutral-600 text-xs ml-2">{item.finding_id}</span>
                    </div>
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {item.files_to_modify.slice(0, 3).map((f, i) => (
                        <span key={i} className="text-xs text-neutral-500 font-mono">
                          {f.split("/").pop()}
                        </span>
                      ))}
                      {item.files_to_modify.length > 3 && (
                        <span className="text-xs text-neutral-600">
                          +{item.files_to_modify.length - 3}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
