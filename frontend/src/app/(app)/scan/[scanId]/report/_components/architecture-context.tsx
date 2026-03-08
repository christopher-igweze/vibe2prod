"use client"

import type { CodebaseMap, DiscoveryFinding } from "@/lib/api/types"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface ArchitectureContextProps {
  map: CodebaseMap
  findings: DiscoveryFinding[]
}

export function ArchitectureContext({ map, findings }: ArchitectureContextProps) {
  // Group findings by top-level directory for hotspot chart
  const hotspots = new Map<string, number>()
  for (const f of findings) {
    for (const loc of f.locations) {
      const dir = loc.file_path.split("/").slice(0, 2).join("/")
      hotspots.set(dir, (hotspots.get(dir) ?? 0) + 1)
    }
  }
  const sortedHotspots = [...hotspots.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8)
  const maxCount = sortedHotspots[0]?.[1] ?? 1

  return (
    <Card className="p-5 space-y-6">
      <h2 className="text-lg font-semibold text-[#E8ECF4] font-[family-name:var(--font-heading)]">Architecture Context</h2>

      {/* Architecture Summary */}
      {map.architecture_summary && (
        <p className="text-sm text-[#E8ECF4] leading-relaxed">
          {map.architecture_summary}
        </p>
      )}

      {/* Modules + Entry Points grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Modules */}
        {map.modules.length > 0 && (
          <div className="rounded-lg border border-white/[0.06] bg-[#0B0F19]/50 p-4">
            <h3 className="text-sm font-medium text-[#8692A8] mb-3">Modules</h3>
            <div className="space-y-2">
              {map.modules.map((mod) => (
                <div
                  key={mod.path}
                  className="flex items-start justify-between gap-2"
                >
                  <div className="min-w-0">
                    <span className="text-sm font-medium text-[#E8ECF4] block">
                      {mod.name}
                    </span>
                    {mod.purpose && (
                      <p className="text-xs text-[#4E586E] mt-0.5 line-clamp-2">
                        {mod.purpose}
                      </p>
                    )}
                  </div>
                  {mod.loc > 0 && (
                    <span className="text-xs text-[#4E586E] shrink-0 tabular-nums">
                      {mod.loc.toLocaleString()} LOC
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Entry Points */}
        {map.entry_points.length > 0 && (
          <div className="rounded-lg border border-white/[0.06] bg-[#0B0F19]/50 p-4">
            <h3 className="text-sm font-medium text-[#8692A8] mb-3">Entry Points</h3>
            <div className="space-y-2">
              {map.entry_points.map((ep, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-xs text-[#E8ECF4] font-[family-name:var(--font-code)] truncate flex-1">
                    {ep.path}
                  </span>
                  <Badge
                    variant="outline"
                    className="border-white/[0.08] text-[#8692A8] text-[10px] px-1.5 py-0 shrink-0"
                  >
                    {ep.type}
                  </Badge>
                  <Badge
                    className={`text-[10px] px-1.5 py-0 border shrink-0 ${
                      ep.is_public
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : "bg-forge-surface text-[#8692A8] border-white/[0.06]"
                    }`}
                  >
                    {ep.is_public ? "public" : "private"}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Key Patterns */}
      {map.key_patterns.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[#8692A8] mb-2">Key Patterns</h3>
          <div className="flex flex-wrap gap-1.5">
            {map.key_patterns.map((pattern, i) => (
              <Badge
                key={i}
                variant="secondary"
                className="bg-forge-nav text-[#E8ECF4] text-xs"
              >
                {pattern}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Data Flows */}
      {map.data_flows.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[#8692A8] mb-2">Data Flows</h3>
          <div className="space-y-2">
            {map.data_flows.map((flow, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-sm"
              >
                <span className="text-[#E8ECF4] font-[family-name:var(--font-code)] text-xs">{flow.source}</span>
                <span className="text-[#4E586E]">-&gt;</span>
                <span className="text-[#E8ECF4] font-[family-name:var(--font-code)] text-xs">{flow.destination}</span>
                <Badge
                  variant="outline"
                  className="border-white/[0.08] text-[#4E586E] text-[10px] px-1.5 py-0 ml-1"
                >
                  {flow.data_type}
                </Badge>
                <Badge
                  className={`text-[10px] px-1.5 py-0 border shrink-0 ${
                    flow.is_authenticated
                      ? "bg-forge-amber/10 text-forge-amber border-forge-amber/20"
                      : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}
                >
                  {flow.is_authenticated ? "authenticated" : "unauthenticated"}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Auth Boundaries */}
      {map.auth_boundaries.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[#8692A8] mb-2">Auth Boundaries</h3>
          <div className="space-y-2">
            {map.auth_boundaries.map((ab, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-[#E8ECF4] font-[family-name:var(--font-code)] text-xs">{ab.path}</span>
                <Badge
                  className={`text-[10px] px-1.5 py-0 border shrink-0 ${
                    ab.is_protected
                      ? "bg-forge-amber/10 text-forge-amber border-forge-amber/20"
                      : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}
                >
                  {ab.is_protected ? "protected" : "unprotected"}
                </Badge>
                <span className="text-xs text-[#4E586E]">{ab.auth_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Finding Hotspots */}
      {sortedHotspots.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[#8692A8] mb-2">Finding Hotspots</h3>
          <div className="space-y-1.5">
            {sortedHotspots.map(([dir, count]) => (
              <div key={dir} className="flex items-center gap-3">
                <span className="text-xs text-[#8692A8] font-[family-name:var(--font-code)] w-48 shrink-0 truncate">
                  {dir}
                </span>
                <div className="flex-1 h-4 bg-forge-nav rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-emerald-500/40 rounded-sm"
                    style={{ width: `${(count / maxCount) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-[#4E586E] w-6 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
