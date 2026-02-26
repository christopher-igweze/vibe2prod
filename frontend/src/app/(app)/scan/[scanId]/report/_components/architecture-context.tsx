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
    <Card className="bg-neutral-900 border-neutral-800 p-5 space-y-6">
      <h2 className="text-lg font-semibold text-neutral-100">Architecture Context</h2>

      {/* Architecture Summary */}
      {map.architecture_summary && (
        <p className="text-sm text-neutral-300 leading-relaxed">
          {map.architecture_summary}
        </p>
      )}

      {/* Modules + Entry Points grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Modules */}
        {map.modules.length > 0 && (
          <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-4">
            <h3 className="text-sm font-medium text-neutral-400 mb-3">Modules</h3>
            <div className="space-y-2">
              {map.modules.map((mod) => (
                <div
                  key={mod.path}
                  className="flex items-start justify-between gap-2"
                >
                  <div className="min-w-0">
                    <span className="text-sm font-medium text-neutral-200 block">
                      {mod.name}
                    </span>
                    {mod.purpose && (
                      <p className="text-xs text-neutral-500 mt-0.5 line-clamp-2">
                        {mod.purpose}
                      </p>
                    )}
                  </div>
                  {mod.loc > 0 && (
                    <span className="text-xs text-neutral-500 shrink-0 tabular-nums">
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
          <div className="rounded-lg border border-neutral-800 bg-neutral-950/50 p-4">
            <h3 className="text-sm font-medium text-neutral-400 mb-3">Entry Points</h3>
            <div className="space-y-2">
              {map.entry_points.map((ep, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-xs text-neutral-300 font-mono truncate flex-1">
                    {ep.path}
                  </span>
                  <Badge
                    variant="outline"
                    className="border-neutral-700 text-neutral-400 text-[10px] px-1.5 py-0 shrink-0"
                  >
                    {ep.type}
                  </Badge>
                  <Badge
                    className={`text-[10px] px-1.5 py-0 border shrink-0 ${
                      ep.is_public
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-neutral-500/10 text-neutral-400 border-neutral-600"
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
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Key Patterns</h3>
          <div className="flex flex-wrap gap-1.5">
            {map.key_patterns.map((pattern, i) => (
              <Badge
                key={i}
                variant="secondary"
                className="bg-neutral-800 text-neutral-300 text-xs"
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
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Data Flows</h3>
          <div className="space-y-2">
            {map.data_flows.map((flow, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-sm"
              >
                <span className="text-neutral-300 font-mono text-xs">{flow.source}</span>
                <span className="text-neutral-600">-&gt;</span>
                <span className="text-neutral-300 font-mono text-xs">{flow.destination}</span>
                <Badge
                  variant="outline"
                  className="border-neutral-700 text-neutral-500 text-[10px] px-1.5 py-0 ml-1"
                >
                  {flow.data_type}
                </Badge>
                <Badge
                  className={`text-[10px] px-1.5 py-0 border shrink-0 ${
                    flow.is_authenticated
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
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
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Auth Boundaries</h3>
          <div className="space-y-2">
            {map.auth_boundaries.map((ab, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="text-neutral-300 font-mono text-xs">{ab.path}</span>
                <Badge
                  className={`text-[10px] px-1.5 py-0 border shrink-0 ${
                    ab.is_protected
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}
                >
                  {ab.is_protected ? "protected" : "unprotected"}
                </Badge>
                <span className="text-xs text-neutral-500">{ab.auth_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Finding Hotspots */}
      {sortedHotspots.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Finding Hotspots</h3>
          <div className="space-y-1.5">
            {sortedHotspots.map(([dir, count]) => (
              <div key={dir} className="flex items-center gap-3">
                <span className="text-xs text-neutral-400 font-mono w-48 shrink-0 truncate">
                  {dir}
                </span>
                <div className="flex-1 h-4 bg-neutral-800 rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-orange-500/40 rounded-sm"
                    style={{ width: `${(count / maxCount) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-neutral-500 w-6 text-right">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
