import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a duration in seconds to a human-readable string (e.g. "45s", "2m 15s").
 * Accepts `number | null` — returns "--" for null values.
 */
export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "--"
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

/** Severity-to-hex-color mapping for PDF/HTML report generation. */
export const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
}

/** Score-to-hex-color — canonical implementation shared across app and reports. */
export function scoreColor(score: number): string {
  if (score >= 70) return "#34d399"
  if (score >= 40) return "#fbbf24"
  return "#ef4444"
}

/** HTML-escape a string for safe embedding in HTML. */
export function esc(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}
