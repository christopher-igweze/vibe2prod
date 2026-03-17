import type { ScanFixStatus } from "@/lib/api/types"
import { formatDuration, SEVERITY_COLORS, scoreColor, esc } from "@/lib/utils"

export function remediationReportToPdfHtml(status: ScanFixStatus): string {
  const title = "FORGE Remediation Report"
  const date = new Date().toLocaleString("en-US", {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  })

  const readiness = status.readiness_report
  const overallScore = status.readiness_score ?? readiness?.overall_score ?? 0
  const findingsFixed = status.findings_fixed ?? 0
  const findingsDeferred = status.findings_deferred ?? 0
  const totalFindings = findingsFixed + findingsDeferred
  const isFailed = status.status === "failed"

  // Category breakdown
  let categoryHtml = ""
  if (readiness?.category_scores && readiness.category_scores.length > 0) {
    categoryHtml += `<h2>Category Breakdown</h2>\n<table class="cat-table"><thead><tr><th>Category</th><th>Score</th><th>Weight</th><th>Details</th></tr></thead><tbody>\n`
    for (const cat of readiness.category_scores) {
      const color = scoreColor(cat.score)
      categoryHtml += `<tr><td>${esc(cat.name)}</td><td style="color:${color};font-weight:600">${cat.score}/100</td><td>${cat.weight.toFixed(2)}</td><td>${esc(cat.details || "")}</td></tr>\n`
    }
    categoryHtml += `</tbody></table>\n`
  }

  // Debt items
  let debtHtml = ""
  if (readiness?.debt_items && readiness.debt_items.length > 0) {
    debtHtml += `<h2>Deferred Items (${readiness.debt_items.length})</h2>\n`
    for (const item of readiness.debt_items) {
      const sevColor = SEVERITY_COLORS[item.severity] || "#6b7280"
      debtHtml += `<div class="finding">`
      debtHtml += `<div class="meta"><span class="badge" style="background:${sevColor};color:#fff">${item.severity.toUpperCase()}</span><span class="tag">${esc(item.category)}</span></div>`
      debtHtml += `<h4>${esc(item.title)}</h4>`
      debtHtml += `<p class="desc">${esc(item.description)}</p>`
      if (item.reason_deferred) {
        debtHtml += `<p class="deferred">Reason: ${esc(item.reason_deferred)}</p>`
      }
      debtHtml += `</div>\n`
    }
  }

  // Recommendations
  let recsHtml = ""
  if (readiness?.recommendations && readiness.recommendations.length > 0) {
    recsHtml += `<h2>Recommendations</h2>\n<ul>\n`
    for (const rec of readiness.recommendations) {
      recsHtml += `<li>${esc(rec)}</li>\n`
    }
    recsHtml += `</ul>\n`
  }

  // Investor summary
  let summaryHtml = ""
  if (isFailed) {
    summaryHtml = `<div class="error-box"><strong>Remediation Failed</strong><p>${esc(status.error || status.summary || "Remediation failed.")}</p></div>`
  } else if (readiness?.investor_summary) {
    summaryHtml = `<div class="summary-box"><p>${esc(readiness.investor_summary)}</p></div>`
  } else if (status.summary) {
    summaryHtml = `<div class="summary-box"><p>${esc(status.summary)}</p></div>`
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
  h4 { font-size: 14px; margin-bottom: 4px; }
  .subtitle { color: #6b7280; font-size: 13px; margin-bottom: 16px; }
  .status-badge { display: inline-block; font-size: 12px; font-weight: 600; padding: 2px 10px; border-radius: 4px; margin-left: 8px; }
  .status-success { background: #d1fae5; color: #065f46; }
  .status-failed { background: #fee2e2; color: #991b1b; }
  .score-hero { text-align: center; margin: 24px 0; }
  .score-hero .score { font-size: 64px; font-weight: 700; }
  .score-hero .label { font-size: 14px; color: #6b7280; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }
  .stat-card { border: 1px solid #e5e5e5; border-radius: 6px; padding: 10px 14px; }
  .stat-card .label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
  .stat-card .value { font-size: 18px; font-weight: 600; margin-top: 2px; }
  .cat-table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  .cat-table th, .cat-table td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #e5e5e5; font-size: 13px; }
  .cat-table th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; }
  .finding { border: 1px solid #e5e5e5; border-radius: 6px; padding: 12px 16px; margin-bottom: 10px; page-break-inside: avoid; }
  .finding .meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
  .badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 4px; }
  .tag { display: inline-block; font-size: 11px; padding: 1px 8px; border-radius: 4px; background: #f3f4f6; color: #374151; }
  .desc { margin: 8px 0; color: #374151; }
  .deferred { margin: 4px 0; color: #6b7280; font-style: italic; font-size: 12px; }
  .summary-box { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 16px; margin: 16px 0; }
  .error-box { background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 16px; margin: 16px 0; color: #991b1b; }
  ul { margin-left: 20px; margin-top: 8px; }
  li { margin-bottom: 6px; }
  .footer { margin-top: 32px; padding-top: 12px; border-top: 1px solid #e5e5e5; font-size: 11px; color: #9ca3af; text-align: center; }
  @media print {
    body { padding: 20px 16px; }
    .no-print { display: none; }
    .finding { page-break-inside: avoid; }
  }
</style>
</head>
<body>
<div class="no-print" style="margin-bottom:20px;padding:12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:6px;text-align:center">
  <strong>Press Ctrl+P (or Cmd+P) to save as PDF</strong>, then close this tab.
</div>

<h1>${esc(title)}<span class="status-badge ${isFailed ? "status-failed" : "status-success"}">${isFailed ? "FAILED" : "SUCCESS"}</span></h1>
<p class="subtitle">${date} &middot; Duration: ${formatDuration(status.duration_seconds)}${status.cost_usd != null ? ` &middot; Cost: $${status.cost_usd.toFixed(2)}` : ""}</p>

<div class="score-hero">
  <div class="score" style="color:${scoreColor(overallScore)}">${overallScore}</div>
  <div class="label">Production Readiness Score (out of 100)</div>
</div>

${summaryHtml}

<div class="summary-grid">
  <div class="stat-card">
    <div class="label">Total Findings</div>
    <div class="value">${totalFindings}</div>
  </div>
  <div class="stat-card">
    <div class="label">Fixed</div>
    <div class="value" style="color:#10b981">${findingsFixed}</div>
  </div>
  <div class="stat-card">
    <div class="label">Deferred</div>
    <div class="value" style="color:#eab308">${findingsDeferred}</div>
  </div>
  ${status.agent_invocations != null ? `<div class="stat-card"><div class="label">Agent Invocations</div><div class="value">${status.agent_invocations}</div></div>` : ""}
</div>

${categoryHtml}

${debtHtml}

${recsHtml}

<div class="footer">
  Generated by FORGE Engine &middot; Fix Attempt: ${status.fix_attempt_id}
</div>
</body>
</html>`
}

export function openRemediationPdfReport(status: ScanFixStatus) {
  const html = remediationReportToPdfHtml(status)
  const blob = new Blob([html], { type: "text/html" })
  const url = URL.createObjectURL(blob)
  const win = window.open(url, "_blank")
  if (win) {
    win.addEventListener("load", () => {
      setTimeout(() => win.print(), 300)
    })
  }
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}
