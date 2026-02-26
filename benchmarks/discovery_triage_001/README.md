# FORGE Benchmark: Discovery + Triage Matrix E2E — discovery_triage_001

**Date:** 2026-02-26
**Forge Version:** 0.1.0
**Pipeline Mode:** Discovery (Discovery + Triage phases only, no Remediation)
**Matrix:** 3x3 (size x complexity) = 9 open-source repositories

## Purpose

First full matrix benchmark of the FORGE engine's Discovery and Triage pipeline across a diverse 3x3 grid of real-world open-source repositories. This validates:

1. **Cost scaling** — How does LLM cost correlate with repo size and complexity?
2. **Finding quality** — Does the engine surface meaningful findings across different codebase profiles?
3. **Duration** — Wall-clock performance across the size spectrum
4. **Agent economics** — Which agents dominate cost, and can we optimize?

## 3x3 Matrix Results

|                | **Simple** | **Decent** | **Complex** |
|----------------|-----------|-----------|------------|
| **Small**      | fabric    | open-saas | fastapi-fullstack |
| **Medium**     | httpie    | screenshot-to-code | chatbot-ui |
| **Large**      | juice-shop | ghostfolio | jan |

### Full Results Table

| Repo | Size | Complexity | LOC | Findings | Critical | High | Medium | Low | Cost (USD) | Duration (s) | Tokens |
|------|------|------------|-----|----------|----------|------|--------|-----|------------|--------------|--------|
| fabric | small | simple | ~5.4k | 21 | 4 | 5 | 10 | 2 | $0.8488 | 199.6 | 525,597 |
| httpie | medium | simple | ~19k | 21 | 0 | 5 | 8 | 8 | $0.5956 | 152.6 | 381,882 |
| juice-shop | large | simple | ~90k | 21 | 0 | 7 | 10 | 4 | $1.0217 | 323.6 | 629,688 |
| open-saas | small | decent | ~10.9k | 39 | 4 | 6 | 18 | 11 | $0.6783 | 315.3 | 418,189 |
| screenshot-to-code | medium | decent | ~19.2k | 45 | 4 | 14 | 18 | 9 | $0.7387 | 198.3 | 451,566 |
| ghostfolio | large | decent | ~71k | 52 | 4 | 24 | 20 | 4 | $1.0127 | 256.8 | 635,220 |
| fastapi-fullstack | small | complex | ~12.6k | 35 | 0 | 12 | 14 | 9 | $0.6480 | 332.7 | 404,680 |
| chatbot-ui | medium | complex | ~26.9k | 36 | 2 | 10 | 17 | 7 | $0.7710 | 266.0 | 478,415 |
| jan | large | complex | ~89k | 27 | 0 | 10 | 13 | 4 | $0.9520 | 189.4 | 515,039 |

### Totals

| Metric | Value |
|--------|-------|
| **Total Findings** | 297 |
| **Total Cost** | $7.2668 |
| **Total Duration** | 2,234.3s (~37.2 min) |
| **Total Tokens** | 4,440,276 |
| **Avg Cost / Repo** | $0.8074 |
| **Avg Findings / Repo** | 33.0 |
| **Avg Duration / Repo** | 248.3s (~4.1 min) |

### Severity Distribution (All Repos)

| Severity | Count | % |
|----------|-------|---|
| Critical | 18 | 6.1% |
| High | 93 | 31.3% |
| Medium | 128 | 43.1% |
| Low | 58 | 19.5% |

## Per-Agent Cost Breakdown

All 9 repos combined. Every discovery run invokes 10 agents.

| Agent | Total Cost | % of Total | Role |
|-------|-----------|------------|------|
| security_auditor/infrastructure | $1.4469 | 19.9% | Infrastructure security scanning |
| security_auditor/data_handling | $1.4031 | 19.3% | Data handling security scanning |
| security_auditor/auth_flow | $1.3168 | 18.1% | Auth flow security scanning |
| fix_strategist | $1.1437 | 15.7% | Triage: remediation planning |
| architecture_reviewer | $0.7626 | 10.5% | Architecture analysis |
| triage_classifier | $0.3191 | 4.4% | Triage: finding classification |
| quality_auditor/code_patterns | $0.2945 | 4.1% | Code pattern quality checks |
| quality_auditor/performance | $0.2788 | 3.8% | Performance quality checks |
| quality_auditor/error_handling | $0.2534 | 3.5% | Error handling quality checks |
| codebase_analyst | $0.0482 | 0.7% | Initial codebase indexing |

### Model Cost Split

| Model | Total Cost | % of Total |
|-------|-----------|------------|
| anthropic/claude-haiku-4.5 | $6.3920 | 88.0% |
| minimax/minimax-m2.5 | $0.8748 | 12.0% |

## Key Observations

### Cost Scaling

- **Cheapest run:** httpie at $0.60 (medium/simple, 19k LOC)
- **Most expensive run:** juice-shop at $1.02 (large/simple, 90k LOC)
- Cost range is narrow: $0.60 - $1.02 across a 17x LOC range (5.4k to 90k)
- Cost correlates more with LOC than with complexity, but the scaling is sub-linear — doubling LOC does not double cost
- The codebase_analyst (indexer) is the cheapest agent at $0.05 total — it uses Minimax M2.5 for bulk analysis

### Security Auditors Dominate Cost

- The three security_auditor sub-agents together account for **57.3%** of total cost ($4.17)
- This is by design: security scanning receives the most context and performs the deepest analysis
- The fix_strategist (15.7%) is the single most expensive individual agent after the security trio

### Finding Distribution

- **Vibecoded repos surface more findings:** open-saas (39), screenshot-to-code (45), ghostfolio (52) have the highest counts
- **Clean CLI tools have fewer findings:** httpie (21), fabric (21)
- Complexity matters more than size for finding count — complex repos at any size produce more findings
- The critical severity rate is low (6.1%), suggesting the engine is appropriately calibrated

### Duration Variability

- Duration varies from 152.6s (httpie) to 333.8s (fastapi-fullstack)
- Duration does NOT strictly correlate with LOC — fastapi-fullstack (12.6k LOC) took longer than jan (89k LOC)
- This suggests network/API latency and LLM response time variability dominate wall-clock time

## Architecture Context Note

All 9 repos have a `codebase_map.json` in their `scan/` directory, generated by the codebase_analyst agent. However, only **fabric** and **jan** have the `codebase_map` embedded directly in the `discovery_report.json`. This is because:

- **fabric** was re-run after the codebase_map feature was added to the report generator
- **jan** was also run with the updated report generator
- The remaining 7 repos were generated before the codebase_map was added to the report output

The codebase_map data is available for all repos in `scan/codebase_map.json` regardless.

## Viewing Reports

Open the HTML discovery reports in a browser:

```bash
open benchmarks/discovery_triage_001/repos/fabric/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/httpie/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/juice-shop/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/open-saas/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/screenshot-to-code/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/ghostfolio/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/fastapi-fullstack/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/chatbot-ui/report/discovery_report.html
open benchmarks/discovery_triage_001/repos/jan/report/discovery_report.html
```

## File Structure

```
discovery_triage_001/
  README.md                          ← this file
  matrix_summary.json                ← compiled results with all metrics
  repos/
    {repo}/
      report/
        discovery_report.json        ← full findings + remediation plan
        discovery_report.html        ← styled HTML report
      telemetry/
        cost_summary.json            ← per-agent and per-model cost breakdown
        invocations.jsonl            ← raw LLM invocation log
      scan/
        codebase_map.json            ← architecture map from codebase_analyst
        architecture_findings.json   ← architecture reviewer findings
        security_findings.json       ← security auditor findings
        quality_findings.json        ← quality auditor findings
        triage_result.json           ← triage classifier output
        remediation_plan.json        ← fix strategist remediation plan
```
