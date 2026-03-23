import type { DiscoveryReport, DiscoveryFinding, Actionability, EvaluationReport, AIVSSScore } from "@/lib/api/types"
import { formatDuration, SEVERITY_COLORS, esc } from "@/lib/utils"

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

const DIMENSION_ORDER = [
  "security",
  "reliability",
  "maintainability",
  "test_quality",
  "performance",
  "documentation",
  "operations",
] as const

const DIMENSION_LABELS: Record<string, string> = {
  security: "Security",
  reliability: "Reliability",
  maintainability: "Maintainability",
  test_quality: "Test Quality",
  performance: "Performance",
  documentation: "Documentation",
  operations: "Operations",
}

function renderEvaluationHtml(
  evaluation?: EvaluationReport | null,
  aivss?: AIVSSScore | null,
): string {
  if (!evaluation) return ""

  const lines: string[] = []
  const scores = evaluation.scores
  const gate = evaluation.quality_gate

  lines.push(`<h2>Production Readiness</h2>`)

  // Score + gate cards
  lines.push(`<div class="summary-grid">`)
  if (scores) {
    lines.push(`<div class="stat-card">`)
    lines.push(`<div class="label">Composite Score</div>`)
    lines.push(`<div class="value">${scores.composite}/100</div>`)
    lines.push(`<div style="font-size:11px;color:#6b7280;margin-top:2px">${esc(scores.band)} — ${esc(scores.label)}</div>`)
    lines.push(`</div>`)
  }
  if (gate) {
    const gateColor = gate.passed ? "#059669" : "#dc2626"
    const gateText = gate.passed ? "PASSED" : "FAILED"
    lines.push(`<div class="stat-card">`)
    lines.push(`<div class="label">Quality Gate</div>`)
    lines.push(`<div class="value" style="color:${gateColor}">${gateText}</div>`)
    lines.push(`<div style="font-size:11px;color:#6b7280;margin-top:2px">${esc(gate.profile)} profile</div>`)
    lines.push(`</div>`)
  }
  if (aivss) {
    lines.push(`<div class="stat-card">`)
    lines.push(`<div class="label">AI Risk (AIVSS)</div>`)
    lines.push(`<div class="value">${aivss.score}/10</div>`)
    lines.push(`<div style="font-size:11px;color:#6b7280;margin-top:2px">${esc(aivss.severity)}</div>`)
    lines.push(`</div>`)
  }
  lines.push(`</div>`)

  // Quality gate failure reasons
  if (gate && !gate.passed && gate.failures?.length > 0) {
    lines.push(`<div style="margin:8px 0;padding:8px 12px;background:#fef2f2;border:1px solid #fecaca;border-radius:6px;font-size:12px;color:#991b1b">`)
    lines.push(`<strong>Gate Failures:</strong><ul style="margin:4px 0 0 16px">`)
    for (const reason of gate.failures) {
      lines.push(`<li>${esc(reason)}</li>`)
    }
    lines.push(`</ul></div>`)
  }

  // Dimensions
  if (scores?.dimensions) {
    lines.push(`<h3>Dimensions</h3>`)
    lines.push(`<table style="width:100%;border-collapse:collapse;font-size:12px;margin:8px 0">`)
    lines.push(`<thead><tr style="border-bottom:1px solid #e5e5e5;text-align:left">`)
    lines.push(`<th style="padding:4px 8px">Dimension</th>`)
    lines.push(`<th style="padding:4px 8px">Score</th>`)
    lines.push(`<th style="padding:4px 8px">Progress</th>`)
    lines.push(`<th style="padding:4px 8px">Checks</th>`)
    lines.push(`</tr></thead><tbody>`)

    for (const key of DIMENSION_ORDER) {
      const dim = scores.dimensions[key]
      if (!dim) continue
      const label = DIMENSION_LABELS[key] ?? key
      const total = dim.checks_passed + dim.checks_failed
      const pct = total > 0 ? Math.round((dim.checks_passed / total) * 100) : 0
      const barColor = dim.score >= 70 ? "#059669" : dim.score >= 40 ? "#d97706" : "#dc2626"

      lines.push(`<tr style="border-bottom:1px solid #f3f4f6">`)
      lines.push(`<td style="padding:4px 8px;font-weight:500">${esc(label)}</td>`)
      lines.push(`<td style="padding:4px 8px">${dim.score}</td>`)
      lines.push(`<td style="padding:4px 8px"><div style="width:100%;height:8px;background:#f3f4f6;border-radius:4px;overflow:hidden"><div style="width:${pct}%;height:100%;background:${barColor};border-radius:4px"></div></div></td>`)
      lines.push(`<td style="padding:4px 8px">${dim.checks_passed}/${total}</td>`)
      lines.push(`</tr>`)
    }
    lines.push(`</tbody></table>`)
  }

  // Compliance
  const comp = evaluation.compliance
  if (comp) {
    lines.push(`<h3>Compliance</h3>`)
    lines.push(`<ul style="font-size:12px;margin:4px 0 8px 16px">`)
    if (comp.asvs) {
      lines.push(`<li>OWASP ASVS: Level ${comp.asvs.estimated_level} (${comp.asvs.level_1_percent}% of L1, ${esc(comp.asvs.level_1_coverage)})</li>`)
    }
    if (comp.nist) {
      lines.push(`<li>NIST SSDF: ${comp.nist.practices_passing}/${comp.nist.practices_evaluated} practices passing</li>`)
    }
    lines.push(`</ul>`)
  }

  return lines.join("\n")
}

export function reportToPdfHtml(
  report: DiscoveryReport,
  repoName?: string,
  evaluation?: EvaluationReport | null,
  aivss?: AIVSSScore | null,
): string {
  const title = repoName ? `Scan Report: ${repoName}` : "Scan Report"
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
<p class="subtitle">${date} &middot; Duration: ${formatDuration(report.duration_seconds)}${report.cost_usd > 0 ? ` &middot; Cost: $${((report.cost_usd + 0.14) * 4).toFixed(2)}` : ""}</p>
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

${renderEvaluationHtml(evaluation, aivss)}

${findingsHtml ? `<h2>Findings</h2>\n${findingsHtml}` : ""}

${remediationHtml}

<div class="footer">
  Run ID: ${report.run_id} &middot; Phase: ${report.phase}
</div>
</body>
</html>`
}

export function openPdfReport(
  report: DiscoveryReport,
  repoName?: string,
  evaluation?: EvaluationReport | null,
  aivss?: AIVSSScore | null,
) {
  const html = reportToPdfHtml(report, repoName, evaluation, aivss)
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
