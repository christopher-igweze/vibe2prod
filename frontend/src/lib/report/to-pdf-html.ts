import type { DiscoveryReport, DiscoveryFinding, Actionability } from "@/lib/api/types"

const ACTIONABILITY_ORDER: Actionability[] = [
  "must_fix",
  "should_fix",
  "consider",
  "informational",
]

const ACTIONABILITY_LABELS: Record<Actionability, string> = {
  must_fix: "Must Fix",
  should_fix: "Should Fix",
  consider: "Consider",
  informational: "Informational",
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#3b82f6",
}

function esc(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return s > 0 ? `${m}m ${s}s` : `${m}m`
}

function renderFindingHtml(f: DiscoveryFinding): string {
  const sevColor = SEVERITY_COLORS[f.severity] || "#6b7280"
  const lines: string[] = []

  lines.push(`<div class="finding">`)
  lines.push(`<h4>${esc(f.title)}</h4>`)
  lines.push(`<div class="meta">`)
  lines.push(`<span class="badge" style="background:${sevColor};color:#fff">${f.severity.toUpperCase()}</span>`)
  lines.push(`<span class="tag">${f.category}</span>`)
  lines.push(`<span class="tag">Confidence: ${f.confidence.toFixed(2)}</span>`)
  if (f.cwe_id) lines.push(`<span class="tag">CWE: ${f.cwe_id}</span>`)
  if (f.owasp_ref) lines.push(`<span class="tag">OWASP: ${f.owasp_ref}</span>`)
  lines.push(`</div>`)

  lines.push(`<p class="desc">${esc(f.description)}</p>`)

  if (f.locations.length > 0) {
    lines.push(`<div class="locations"><strong>Locations:</strong><ul>`)
    for (const loc of f.locations) {
      const range =
        loc.line_start != null && loc.line_end != null
          ? `${loc.line_start}-${loc.line_end}`
          : loc.line_start != null
            ? `${loc.line_start}`
            : ""
      lines.push(`<li><code>${esc(loc.file_path)}${range ? ":" + range : ""}</code></li>`)
      if (loc.snippet) {
        lines.push(`<pre>${esc(loc.snippet)}</pre>`)
      }
    }
    lines.push(`</ul></div>`)
  }

  if (f.suggested_fix) {
    lines.push(`<p class="fix"><strong>Suggested Fix:</strong> ${esc(f.suggested_fix)}</p>`)
  }

  lines.push(`</div>`)
  return lines.join("\n")
}

export function reportToPdfHtml(report: DiscoveryReport, repoName?: string): string {
  const title = repoName ? `FORGE Report: ${repoName}` : "FORGE Report"
  const date = new Date(report.generated_at).toLocaleString("en-US", {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  })

  const sev = report.severity_breakdown
  const summary = report.actionability_summary

  // Group findings by actionability
  const grouped: Record<string, DiscoveryFinding[]> = {}
  for (const f of report.findings) {
    const tier = f.actionability ?? "consider"
    if (!grouped[tier]) grouped[tier] = []
    grouped[tier].push(f)
  }

  let findingsHtml = ""
  for (const tier of ACTIONABILITY_ORDER) {
    const findings = grouped[tier]
    if (!findings || findings.length === 0) continue
    findingsHtml += `<h3>${ACTIONABILITY_LABELS[tier]} (${findings.length})</h3>\n`
    for (const f of findings) {
      findingsHtml += renderFindingHtml(f) + "\n"
    }
  }

  // Remediation plan
  let remediationHtml = ""
  if (report.remediation_plan && report.remediation_plan.items.length > 0) {
    remediationHtml += `<h2>Remediation Plan</h2>\n`
    const sorted = [...report.remediation_plan.items].sort((a, b) => a.priority - b.priority)
    for (const item of sorted) {
      remediationHtml += `<div class="finding">`
      remediationHtml += `<h4>${esc(item.title)}</h4>`
      remediationHtml += `<div class="meta">`
      remediationHtml += `<span class="tag">Priority: ${item.priority}</span>`
      remediationHtml += `<span class="tag">Group: ${item.group}</span>`
      remediationHtml += `</div>`
      remediationHtml += `<p class="desc"><strong>Approach:</strong> ${esc(item.approach)}</p>`
      if (item.files_to_modify.length > 0) {
        remediationHtml += `<p><strong>Files:</strong> ${item.files_to_modify.map(f => `<code>${esc(f)}</code>`).join(", ")}</p>`
      }
      if (item.acceptance_criteria.length > 0) {
        remediationHtml += `<p><strong>Acceptance Criteria:</strong></p><ul>`
        for (const ac of item.acceptance_criteria) {
          remediationHtml += `<li>${esc(ac)}</li>`
        }
        remediationHtml += `</ul>`
      }
      remediationHtml += `</div>\n`
    }
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>${esc(title)}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1a1a1a; max-width: 900px; margin: 0 auto; padding: 40px 32px; font-size: 13px; line-height: 1.5; }
  h1 { font-size: 24px; margin-bottom: 4px; }
  h2 { font-size: 18px; margin-top: 32px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid #e5e5e5; }
  h3 { font-size: 15px; margin-top: 20px; margin-bottom: 8px; color: #374151; }
  h4 { font-size: 14px; margin-bottom: 4px; }
  .subtitle { color: #6b7280; font-size: 13px; margin-bottom: 4px; }
  .run-id { color: #9ca3af; font-size: 12px; font-family: monospace; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }
  .stat-card { border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px 14px; }
  .stat-card .label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
  .stat-card .value { font-size: 18px; font-weight: 600; margin-top: 2px; }
  .severity-bar { display: flex; gap: 12px; margin: 12px 0; }
  .severity-item { display: flex; align-items: center; gap: 4px; font-size: 12px; }
  .severity-dot { width: 10px; height: 10px; border-radius: 50%; }
  .finding { border: 1px solid #e5e5e5; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; page-break-inside: avoid; }
  .finding .meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
  .badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 4px; }
  .tag { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 4px; background: #f3f4f6; color: #374151; }
  .desc { margin: 8px 0; color: #374151; }
  .fix { margin: 6px 0; color: #065f46; }
  .locations { margin: 6px 0; }
  .locations ul { margin-left: 20px; }
  .locations li { margin-bottom: 4px; }
  code { font-family: "SF Mono", Menlo, monospace; font-size: 12px; background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }
  pre { font-family: "SF Mono", Menlo, monospace; font-size: 11px; background: #f9fafb; border: 1px solid #e5e5e5; border-radius: 4px; padding: 8px 12px; margin: 4px 0; overflow-x: auto; white-space: pre-wrap; }
  .footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e5e5e5; font-size: 11px; color: #9ca3af; text-align: center; }
  @media print {
    body { padding: 20px 16px; }
    .no-print { display: none; }
    h2 { page-break-before: auto; }
    .finding { page-break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:20px;padding:12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;text-align:center">
  <strong>Press Ctrl+P (or Cmd+P) to save as PDF</strong>, then close this tab.
</div>

<h1>${esc(title)}</h1>
<p class="subtitle">${date} &middot; Duration: ${formatDuration(report.duration_seconds)}${report.cost_usd > 0 ? ` &middot; Cost: $${report.cost_usd.toFixed(2)}` : ""}</p>
<p class="run-id">Run ID: ${report.run_id}</p>

<div class="summary-grid">
  <div class="stat-card">
    <div class="label">Total Findings</div>
    <div class="value">${report.total_findings}</div>
  </div>
  <div class="stat-card">
    <div class="label">Lines of Code</div>
    <div class="value">${report.loc_total.toLocaleString()}</div>
  </div>
  <div class="stat-card">
    <div class="label">Files</div>
    <div class="value">${report.file_count.toLocaleString()}</div>
  </div>
  ${report.primary_language ? `<div class="stat-card"><div class="label">Language</div><div class="value">${esc(report.primary_language)}</div></div>` : ""}
</div>

<div class="severity-bar">
  <span class="severity-item"><span class="severity-dot" style="background:#ef4444"></span> Critical: ${sev.critical ?? 0}</span>
  <span class="severity-item"><span class="severity-dot" style="background:#f97316"></span> High: ${sev.high ?? 0}</span>
  <span class="severity-item"><span class="severity-dot" style="background:#eab308"></span> Medium: ${sev.medium ?? 0}</span>
  <span class="severity-item"><span class="severity-dot" style="background:#3b82f6"></span> Low: ${sev.low ?? 0}</span>
</div>

${summary ? `<p style="font-size:12px;color:#6b7280;margin:8px 0">Must Fix: ${summary.must_fix_count} &middot; Should Fix: ${summary.should_fix_count} &middot; Consider: ${summary.consider_count} &middot; Informational: ${summary.informational_count}${summary.signal_to_noise_ratio != null ? ` &middot; Signal-to-noise: ${(summary.signal_to_noise_ratio * 100).toFixed(0)}%` : ""}</p>` : ""}

${findingsHtml ? `<h2>Findings</h2>\n${findingsHtml}` : ""}

${remediationHtml}

<div class="footer">
  Generated by FORGE Engine &middot; Run ID: ${report.run_id} &middot; Phase: ${report.phase}
</div>
</body>
</html>`
}

export function openPdfReport(report: DiscoveryReport, repoName?: string) {
  const html = reportToPdfHtml(report, repoName)
  const blob = new Blob([html], { type: "text/html" })
  const url = URL.createObjectURL(blob)
  const win = window.open(url, "_blank")
  // Auto-trigger print dialog after a brief delay for rendering
  if (win) {
    win.addEventListener("load", () => {
      setTimeout(() => win.print(), 300)
    })
  }
  // Clean up blob URL after a delay
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}
