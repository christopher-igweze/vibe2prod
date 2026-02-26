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

      {/* Modules */}
      {map.modules.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Modules</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {map.modules.map((mod) => (
              <div
                key={mod.path}
                className="rounded border border-neutral-800 bg-neutral-950/50 px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-neutral-200">{mod.name}</span>
                  {mod.loc > 0 && (
                    <span className="text-xs text-neutral-500">{mod.loc.toLocaleString()} LOC</span>
                  )}
                </div>
                {mod.purpose && (
                  <p className="text-xs text-neutral-500 mt-0.5 line-clamp-1">{mod.purpose}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Entry Points */}
      {map.entry_points.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Entry Points</h3>
          <div className="flex flex-wrap gap-2">
            {map.entry_points.map((ep, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className="border-neutral-700 text-neutral-300 text-xs"
                >
                  {ep.type}
                </Badge>
                <span className="text-xs text-neutral-400 font-mono">{ep.path}</span>
              </div>
            ))}
          </div>
        </div>
      )}

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
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-neutral-800 text-neutral-500">
                  <th className="text-left py-1.5 pr-4">Source</th>
                  <th className="text-left py-1.5 pr-4">Destination</th>
                  <th className="text-left py-1.5 pr-4">Type</th>
                  <th className="text-left py-1.5">Auth</th>
                </tr>
              </thead>
              <tbody>
                {map.data_flows.map((flow, i) => (
                  <tr key={i} className="border-b border-neutral-800/50">
                    <td className="py-1.5 pr-4 text-neutral-300 font-mono">{flow.source}</td>
                    <td className="py-1.5 pr-4 text-neutral-300 font-mono">{flow.destination}</td>
                    <td className="py-1.5 pr-4 text-neutral-400">{flow.data_type}</td>
                    <td className="py-1.5">
                      <span className={flow.is_authenticated ? "text-emerald-400" : "text-red-400"}>
                        {flow.is_authenticated ? "Yes" : "No"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Auth Boundaries */}
      {map.auth_boundaries.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-neutral-400 mb-2">Auth Boundaries</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-neutral-800 text-neutral-500">
                  <th className="text-left py-1.5 pr-4">Path</th>
                  <th className="text-left py-1.5 pr-4">Protected</th>
                  <th className="text-left py-1.5">Auth Type</th>
                </tr>
              </thead>
              <tbody>
                {map.auth_boundaries.map((ab, i) => (
                  <tr key={i} className="border-b border-neutral-800/50">
                    <td className="py-1.5 pr-4 text-neutral-300 font-mono">{ab.path}</td>
                    <td className="py-1.5 pr-4">
                      <span className={ab.is_protected ? "text-emerald-400" : "text-red-400"}>
                        {ab.is_protected ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="py-1.5 text-neutral-400">{ab.auth_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
