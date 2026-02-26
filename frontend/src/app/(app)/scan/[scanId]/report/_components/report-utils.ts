import type { Severity } from "@/lib/api/types"

export const SEVERITY_CONFIG: Record<
  Severity,
  { label: string; bg: string; text: string; border: string }
> = {
  critical: {
    label: "Critical",
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/20",
  },
  high: {
    label: "High",
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/20",
  },
  medium: {
    label: "Medium",
    bg: "bg-yellow-500/10",
    text: "text-yellow-400",
    border: "border-yellow-500/20",
  },
  low: {
    label: "Low",
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/20",
  },
}

export const TIER_CONFIG: Record<
  number,
  { label: string; bg: string; text: string }
> = {
  1: { label: "T1", bg: "bg-blue-500/10", text: "text-blue-400" },
  2: { label: "T2", bg: "bg-amber-500/10", text: "text-amber-400" },
  3: { label: "T3", bg: "bg-purple-500/10", text: "text-purple-400" },
}

export const CATEGORY_LABELS: Record<string, string> = {
  security: "Security",
  architecture: "Architecture",
  quality: "Quality",
  reliability: "Reliability",
  performance: "Performance",
}

export function severityClasses(severity: Severity) {
  return SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.medium
}

export function tierClasses(tier: number) {
  return TIER_CONFIG[tier] ?? TIER_CONFIG[2]
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(2)}`
}
