import type { DiscoveryFinding, Severity } from "@/lib/api/types"
import { Card } from "@/components/ui/card"
import { Accordion } from "@/components/ui/accordion"
import { FindingRow } from "./finding-row"

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low"]

interface FindingsTableProps {
  findings: DiscoveryFinding[]
}

export function FindingsTable({ findings }: FindingsTableProps) {
  const sorted = [...findings].sort((a, b) => {
    const ai = SEVERITY_ORDER.indexOf(a.severity)
    const bi = SEVERITY_ORDER.indexOf(b.severity)
    if (ai !== bi) return ai - bi
    return a.tier - b.tier
  })

  return (
    <Card className="bg-neutral-900 border-neutral-800 p-5">
      <h2 className="text-lg font-semibold text-neutral-100 mb-4">
        All Findings ({findings.length})
      </h2>

      <Accordion type="multiple" className="space-y-0">
        {sorted.map((finding) => (
          <FindingRow key={finding.id} finding={finding} />
        ))}
      </Accordion>
    </Card>
  )
}
