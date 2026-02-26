import type { DiscoveryFinding } from "@/lib/api/types"
import { Badge } from "@/components/ui/badge"
import {
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { severityClasses, tierClasses, CATEGORY_LABELS } from "./report-utils"

interface FindingRowProps {
  finding: DiscoveryFinding
}

export function FindingRow({ finding }: FindingRowProps) {
  const sev = severityClasses(finding.severity)
  const tier = tierClasses(finding.tier)

  return (
    <AccordionItem
      value={finding.id}
      className="border-neutral-800"
    >
      <AccordionTrigger className="hover:no-underline px-3 py-2.5 text-left">
        <div className="flex items-center gap-3 w-full min-w-0 pr-2">
          <Badge
            className={`${sev.bg} ${sev.text} ${sev.border} border text-[10px] px-1.5 py-0 shrink-0`}
          >
            {sev.label}
          </Badge>
          <Badge
            className={`${tier.bg} ${tier.text} border-transparent text-[10px] px-1.5 py-0 shrink-0`}
          >
            {tier.label}
          </Badge>
          <span className="text-xs text-neutral-500 shrink-0">
            {CATEGORY_LABELS[finding.category] ?? finding.category}
          </span>
          <span className="text-sm text-neutral-200 truncate">{finding.title}</span>
          <span className="text-xs text-neutral-600 font-mono shrink-0 ml-auto">
            {finding.id}
          </span>
        </div>
      </AccordionTrigger>

      <AccordionContent className="px-3 pb-4 space-y-4">
        {/* Description */}
        <p className="text-sm text-neutral-300 leading-relaxed">
          {finding.description}
        </p>

        {/* Locations */}
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

        {/* Suggested Fix */}
        {finding.suggested_fix && (
          <div>
            <h4 className="text-xs font-medium text-neutral-500 mb-1.5">Suggested Fix</h4>
            <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
              {finding.suggested_fix}
            </p>
          </div>
        )}

        {/* Meta */}
        <div className="flex flex-wrap gap-3 text-xs text-neutral-500">
          {finding.confidence > 0 && (
            <span>Confidence: {Math.round(finding.confidence * 100)}%</span>
          )}
          {finding.cwe_id && <span>{finding.cwe_id}</span>}
          {finding.owasp_ref && <span>{finding.owasp_ref}</span>}
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}
