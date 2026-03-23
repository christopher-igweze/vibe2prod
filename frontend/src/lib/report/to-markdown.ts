import type {
  DiscoveryReport,
  DiscoveryFinding,
  Actionability,
  RemediationPlan as RemediationPlanType,
  RemediationItem,
  CodebaseMap,
  EvaluationReport,
  AIVSSScore,
} from "@/lib/api/types"
import { formatDuration } from "@/lib/utils"

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

function escapeMarkdown(text: string): string {
  return text.replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

function renderFinding(f: DiscoveryFinding): string {
  const lines: string[] = []

  lines.push(`#### ${escapeMarkdown(f.title)}`)
  lines.push(
    `- **Severity:** ${f.severity.toUpperCase()} | **Category:** ${f.category.toUpperCase()} | **Confidence:** ${f.confidence.toFixed(2)}`
  )

  const refs: string[] = []
  if (f.cwe_id) refs.push(`**CWE:** ${f.cwe_id}`)
  if (f.owasp_ref) refs.push(`**OWASP:** ${f.owasp_ref}`)
  if (refs.length > 0) lines.push(`- ${refs.join(" | ")}`)

  if (f.intent_signal) lines.push(`- **Intent Signal:** ${f.intent_signal}`)
  if (f.data_flow) lines.push(`- **Data Flow:** ${f.data_flow}`)

  lines.push("")
  lines.push(`> ${escapeMarkdown(f.description)}`)
  lines.push("")

  if (f.locations.length > 0) {
    lines.push("**Locations:**")
    for (const loc of f.locations) {
      const range =
        loc.line_start != null && loc.line_end != null
          ? `${loc.line_start}-${loc.line_end}`
          : loc.line_start != null
            ? `${loc.line_start}`
            : ""
      lines.push(`- \`${loc.file_path}${range ? ":" + range : ""}\``)
      if (loc.snippet) {
        lines.push("  ```")
        lines.push(`  ${loc.snippet}`)
        lines.push("  ```")
      }
    }
    lines.push("")
  }

  if (f.suggested_fix) {
    lines.push(`**Suggested Fix:** ${escapeMarkdown(f.suggested_fix)}`)
    lines.push("")
  }

  lines.push("---")
  lines.push("")

  return lines.join("\n")
}

function renderRemediationPlan(plan: RemediationPlanType): string {
  const lines: string[] = []

  lines.push("## Remediation Plan")
  lines.push("")

  if (plan.execution_levels.length > 0) {
    for (let i = 0; i < plan.execution_levels.length; i++) {
      lines.push(`### Level ${i + 1}`)
      lines.push("")

      const levelIds = new Set(plan.execution_levels[i])
      const levelItems = plan.items.filter((item) =>
        levelIds.has(item.finding_id)
      )

      if (levelItems.length === 0) {
        // Fallback: show the IDs directly
        for (const id of plan.execution_levels[i]) {
          lines.push(`- ${id}`)
        }
      } else {
        for (const item of levelItems) {
          lines.push(renderRemediationItem(item))
        }
      }
      lines.push("")
    }
  } else {
    // No execution levels — just list all items by priority
    const sorted = [...plan.items].sort((a, b) => a.priority - b.priority)
    for (const item of sorted) {
      lines.push(renderRemediationItem(item))
    }
  }

  if (plan.dependencies.length > 0) {
    lines.push("### Dependencies")
    lines.push("")
    for (const dep of plan.dependencies) {
      lines.push(
        `- **${dep.finding_id}** depends on **${dep.depends_on_finding_id}**: ${dep.reason}`
      )
    }
    lines.push("")
  }

  return lines.join("\n")
}

function renderRemediationItem(item: RemediationItem): string {
  const lines: string[] = []

  lines.push(`#### ${escapeMarkdown(item.title)}`)
  lines.push(`- **Priority:** ${item.priority} | **Group:** ${item.group}`)
  lines.push(`- **Approach:** ${escapeMarkdown(item.approach)}`)

  if (item.files_to_modify.length > 0) {
    lines.push(
      `- **Files:** ${item.files_to_modify.map((f) => "`" + f + "`").join(", ")}`
    )
  }

  if (item.acceptance_criteria.length > 0) {
    lines.push("- **Acceptance Criteria:**")
    for (const ac of item.acceptance_criteria) {
      lines.push(`  - ${escapeMarkdown(ac)}`)
    }
  }

  lines.push("")
  return lines.join("\n")
}

function renderCodebaseMap(map: CodebaseMap): string {
  const lines: string[] = []

  lines.push("## Architecture Context")
  lines.push("")

  if (map.architecture_summary) {
    lines.push(escapeMarkdown(map.architecture_summary))
    lines.push("")
  }

  if (map.key_patterns.length > 0) {
    lines.push("**Key Patterns:** " + map.key_patterns.join(", "))
    lines.push("")
  }

  if (map.modules.length > 0) {
    lines.push("### Modules")
    lines.push("")
    for (const mod of map.modules) {
      lines.push(
        `- **${escapeMarkdown(mod.name)}** (\`${mod.path}\`) — ${escapeMarkdown(mod.purpose)} (${mod.loc.toLocaleString()} LOC, ${mod.language})`
      )
    }
    lines.push("")
  }

  if (map.entry_points.length > 0) {
    lines.push("### Entry Points")
    lines.push("")
    for (const ep of map.entry_points) {
      lines.push(
        `- \`${ep.path}\` — ${ep.type}${ep.is_public ? " (public)" : " (private)"}`
      )
    }
    lines.push("")
  }

  if (map.data_flows.length > 0) {
    lines.push("### Data Flows")
    lines.push("")
    for (const df of map.data_flows) {
      lines.push(
        `- ${escapeMarkdown(df.source)} -> ${escapeMarkdown(df.destination)} (${df.data_type})${df.is_authenticated ? " [authenticated]" : ""}`
      )
    }
    lines.push("")
  }

  if (map.auth_boundaries.length > 0) {
    lines.push("### Auth Boundaries")
    lines.push("")
    for (const ab of map.auth_boundaries) {
      lines.push(
        `- \`${ab.path}\` — ${ab.auth_type}${ab.is_protected ? " [protected]" : " [unprotected]"}`
      )
    }
    lines.push("")
  }

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

function renderEvaluationSection(
  evaluation?: EvaluationReport | null,
  aivss?: AIVSSScore | null,
): string {
  if (!evaluation) return ""

  const lines: string[] = []
  const scores = evaluation.scores
  const gate = evaluation.quality_gate

  lines.push("## Production Readiness")
  lines.push("")

  if (scores) {
    lines.push(
      `**Composite Score:** ${scores.composite}/100 (${scores.band} — ${scores.label})`
    )
  }

  if (gate) {
    const status = gate.passed ? "PASSED" : "FAILED"
    lines.push(`**Quality Gate:** ${status} (${gate.profile} profile)`)
    if (!gate.passed && gate.failures?.length > 0) {
      for (const reason of gate.failures) {
        lines.push(`- ${reason}`)
      }
    }
  }

  lines.push("")

  // Dimensions table
  if (scores?.dimensions) {
    lines.push("### Dimensions")
    lines.push("")
    lines.push("| Dimension | Score | Checks |")
    lines.push("|-----------|-------|--------|")

    for (const key of DIMENSION_ORDER) {
      const dim = scores.dimensions[key]
      if (!dim) continue
      const label = DIMENSION_LABELS[key] ?? key
      const total = dim.checks_passed + dim.checks_failed
      lines.push(
        `| ${label} | ${dim.score} | ${dim.checks_passed}/${total} passed |`
      )
    }
    lines.push("")
  }

  // Compliance
  const comp = evaluation.compliance
  if (comp) {
    lines.push("### Compliance")
    lines.push("")
    if (comp.asvs && comp.asvs.total_requirements > 0) {
      const pct = Math.round((comp.asvs.passed / comp.asvs.total_requirements) * 100)
      lines.push(
        `- OWASP ASVS: Level ${comp.asvs.estimated_level} (${pct}% of L1, ${comp.asvs.passed}/${comp.asvs.total_requirements} checks)`
      )
    }
    if (comp.nist && comp.nist.total > 0) {
      lines.push(
        `- NIST SSDF: ${comp.nist.covered}/${comp.nist.total} practices covered`
      )
    }
    lines.push("")
  }

  // AIVSS
  if (aivss) {
    lines.push("### AI Risk (AIVSS)")
    lines.push("")
    lines.push(`- Score: ${aivss.score}/10 (${aivss.severity})`)
    lines.push("")
  }

  return lines.join("\n")
}

export function reportToMarkdown(
  report: DiscoveryReport,
  repoName?: string,
  evaluation?: EvaluationReport | null,
  aivss?: AIVSSScore | null,
): string {
  const lines: string[] = []

  // Header
  const title = repoName ? `Scan Report: ${repoName}` : "Scan Report"
  lines.push(`# ${title}`)
  lines.push("")
  const costStr = report.cost_usd > 0 ? ` | **Cost:** $${((report.cost_usd + 0.14) * 4).toFixed(2)}` : ""
  lines.push(
    `**Generated:** ${new Date(report.generated_at).toLocaleString()} | **Duration:** ${formatDuration(report.duration_seconds)}${costStr}`
  )
  lines.push("")

  // Summary
  lines.push("## Summary")
  lines.push(
    `- **Total LOC:** ${report.loc_total.toLocaleString()} | **Files:** ${report.file_count.toLocaleString()} | **Language:** ${report.primary_language}`
  )

  const stnr = report.actionability_summary?.signal_to_noise_ratio
  lines.push(
    `- **Findings:** ${report.total_findings} total${stnr != null ? ` | **Signal-to-noise:** ${(stnr * 100).toFixed(0)}%` : ""}`
  )

  if (report.actionability_summary) {
    const s = report.actionability_summary
    lines.push(
      `- **Must Fix:** ${s.must_fix_count} | **Should Fix:** ${s.should_fix_count} | **Consider:** ${s.consider_count} | **Informational:** ${s.informational_count}`
    )
  }

  // Severity breakdown
  const sev = report.severity_breakdown
  lines.push(
    `- **Severity:** Critical: ${sev.critical ?? 0} | High: ${sev.high ?? 0} | Medium: ${sev.medium ?? 0} | Low: ${sev.low ?? 0}`
  )
  lines.push("")

  // Evaluation section
  const evalSection = renderEvaluationSection(evaluation, aivss)
  if (evalSection) {
    lines.push(evalSection)
  }

  // Findings grouped by actionability
  if (report.findings.length > 0) {
    lines.push("## Findings")
    lines.push("")

    const grouped: Record<string, DiscoveryFinding[]> = {}
    for (const f of report.findings) {
      const tier = f.actionability ?? "consider"
      if (!grouped[tier]) grouped[tier] = []
      grouped[tier].push(f)
    }

    for (const tier of ACTIONABILITY_ORDER) {
      const findings = grouped[tier]
      if (!findings || findings.length === 0) continue

      lines.push(
        `### ${ACTIONABILITY_LABELS[tier]} (${findings.length})`
      )
      lines.push("")

      for (const f of findings) {
        lines.push(renderFinding(f))
      }
    }
  }

  // Remediation Plan
  if (report.remediation_plan && report.remediation_plan.items.length > 0) {
    lines.push(renderRemediationPlan(report.remediation_plan))
  }

  // Architecture Context
  if (report.codebase_map) {
    lines.push(renderCodebaseMap(report.codebase_map))
  }

  // Footer
  lines.push("---")
  lines.push(
    `*Run ID: ${report.run_id} | Phase: ${report.phase}*`
  )
  lines.push("")

  return lines.join("\n")
}
