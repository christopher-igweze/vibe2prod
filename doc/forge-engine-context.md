# FORGE Engine Integration Context

**Source repo:** `christopher-igweze/forge-engine`
**Package:** `vibe2prod` (v0.3.0, Python 3.12+)
**Last synced:** 2026-02-26

This document describes the FORGE engine architecture and how vibe2prod integrates with it.

---

## What FORGE Does

FORGE is a 12-agent AI remediation engine that audits codebases and auto-fixes issues. It takes a repo, discovers problems (security, quality, architecture), triages them by complexity, fixes them with AI coders, validates the fixes, and produces a Production Readiness Score.

**Two modes of operation:**
- **Standalone CLI** (`vibe2prod scan|fix|report`) — code stays local, only LLM API calls leave the machine
- **Platform mode** (`forge-engine`) — runs as an AgentField node in Daytona sandboxes, called via HTTP

---

## How Vibe2Prod Calls FORGE

The bridge lives at `backend/services/forge_bridge.py`. It talks to FORGE via AgentField's HTTP API:

```
POST {agentfield_url}/api/v1/execute/async/{node_id}.{reasoner}
```

**Three reasoners exposed:**

| Reasoner | What it does | Agents used |
|----------|-------------|-------------|
| `scan` / `discover` | Discovery + triage only (free tier) | 1-6 |
| `remediate` | Full pipeline: discover + fix + validate | 1-12 |
| `fix_single` | Fix one specific finding | 7-10 |

**Async signatures (from `forge/app.py`):**

```python
async def discover(repo_url="", repo_path="", config=None) -> dict
async def remediate(repo_url="", repo_path="", config=None, tier1_findings=None) -> dict
async def fix_single(repo_path="", finding=None, codebase_map=None, config=None) -> dict
```

**Config dict:**
```python
{
    "mode": "full",                    # full | discovery | remediation | validation
    "dry_run": False,                  # scan only, no fixes
    "models": {"default": "model-id"}, # per-role model overrides
    "enable_parallel_audit": True,
    "max_inner_retries": 3,
    "max_outer_replans": 1,
}
```

**Result dict (ForgeResult):**
```python
{
    "forge_run_id": "uuid",
    "success": True,
    "mode": "full",
    "summary": "Fixed 28 of 35 findings...",
    "total_findings": 35,
    "findings_fixed": 28,
    "findings_deferred": 7,
    "agent_invocations": 97,
    "cost_usd": 3.42,
    "duration_seconds": 1680,
    "readiness_report": {              # ProductionReadinessReport
        "overall_score": 78,
        "category_scores": [...],
        "recommendations": [...],
        "debt_items": [...],
        "investor_summary": "..."
    }
}
```

---

## The 12 Agents

### Discovery Phase (Agents 1-4)

| # | Agent | Model | What it produces |
|---|-------|-------|-----------------|
| 1 | Codebase Analyst | minimax-m2.5 | `CodebaseMap` — modules, deps, data flows, auth boundaries, tech stack |
| 2 | Security Auditor | haiku-4.5 | Findings from 3 parallel passes: auth_flow, data_handling, infrastructure |
| 3 | Quality Auditor | minimax-m2.5 | Findings from 3 parallel passes: error_handling, code_patterns, performance |
| 4 | Architecture Reviewer | haiku-4.5 | Structural coherence score (0-100) + findings |

Agent 1 runs first (serial). Agents 2-4 run in parallel after Agent 1 completes.

### Triage Phase (Agents 5-6)

| # | Agent | Model | What it produces |
|---|-------|-------|-----------------|
| 6 | Triage Classifier | haiku-4.5 | Tier assignment (0-3) for each finding |
| 5 | Fix Strategist | haiku-4.5 | `RemediationPlan` — execution order, dependencies, parallel groups |

Agent 6 runs first (assigns tiers), then Agent 5 plans execution.

### Remediation Phase (Agents 7-10 + Escalation)

| # | Agent | Model | Provider | What it does |
|---|-------|-------|----------|-------------|
| 7 | Coder Tier 2 | **sonnet-4.6** | opencode | Scoped fix (1-3 files) |
| 8 | Coder Tier 3 | **sonnet-4.6** | opencode | Architectural fix (5-15 files) |
| 9 | Test Generator | haiku-4.5 | opencode | Writes tests for fixes |
| 10 | Code Reviewer | haiku-4.5 | openrouter | Reviews fix quality |
| - | Escalation Agent | haiku-4.5 | openrouter | Decides RECLASSIFY/SPLIT/DEFER/ESCALATE |

Sonnet 4.6 for coders is non-negotiable per spec.

### Validation Phase (Agents 11-12)

| # | Agent | Model | What it produces |
|---|-------|-------|-----------------|
| 11 | Integration Validator | haiku-4.5 | Test results, regression check |
| 12 | Debt Tracker | minimax-m2.5 | Production Readiness Report (score + recommendations) |

---

## Three-Loop Control System

```
OUTER LOOP (max 1 replan)
  Re-runs Fix Strategist on remaining findings
    |
    v
MIDDLE LOOP (per finding, on inner exhaustion)
  Escalation Agent decides:
    RECLASSIFY → bump tier 2→3, retry inner
    SPLIT      → decompose into sub-findings
    DEFER      → mark as tech debt
    ESCALATE   → trigger outer replan
    |
    v
INNER LOOP (max 3 iterations per finding)
  Coder → [Test Generator + Code Reviewer] (parallel)
    APPROVE          → done
    REQUEST_CHANGES  → retry with feedback
    BLOCK            → escalate to middle loop
```

Each fix runs in an isolated git worktree (`.forge-worktrees/fix-{id}/`). Merged on approval.

---

## Tier System

| Tier | What | How it's handled |
|------|------|-----------------|
| 0 | Invalid / false-positive | Auto-skipped |
| 1 | Known pattern (deterministic) | Rules-based template fix, no LLM |
| 2 | Scoped fix (1-3 files) | Sonnet 4.6 via inner loop |
| 3 | Architectural fix (5-15 files) | Sonnet 4.6 via inner loop, more turns |

---

## Finding Schema (AuditFinding)

```python
{
    "id": "F-XXXXXXXX",
    "title": "SQL injection in user query",
    "description": "...",
    "category": "SECURITY",          # SECURITY | QUALITY | ARCHITECTURE | RELIABILITY | PERFORMANCE
    "severity": "HIGH",              # CRITICAL | HIGH | MEDIUM | LOW | INFO
    "locations": [{
        "file_path": "src/db.py",
        "line_start": 42,
        "line_end": 45,
        "snippet": "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')"
    }],
    "suggested_fix": "Use parameterized queries...",
    "confidence": 0.92,
    "tier": 2,
    "dedup_key": "sql-injection-src/db.py"
}
```

---

## LLM Provider Abstraction

FORGE uses a provider-agnostic layer (`forge/vendor/agent_ai/`) with four backends:

| Provider | Used by | How it works |
|----------|---------|-------------|
| `openrouter_direct` | Planning agents (analyst, auditors, strategist, reviewer, debt tracker) | Pure stdlib HTTP to OpenRouter API |
| `opencode` | Action agents (coders, test gen, integration validator) | CLI subprocess with file tools (Read/Write/Edit/Bash/Glob/Grep) |
| `claude` | Alternative to opencode | Claude Agent SDK in-process |
| `codex` | Alternative to opencode | Codex CLI subprocess |

Model routing: `FORGE_DEFAULT_MODELS < config.models.default < config.models.<role>`

---

## Artifacts Directory

After a FORGE run, the repo contains:

```
.artifacts/
  scan/
    codebase_map.json           # Agent 1 output
    security_findings.json      # Agent 2
    quality_findings.json       # Agent 3
    architecture_findings.json  # Agent 4
  fix_plan.json                 # Agent 5
  triage_result.json            # Agent 6
  report/
    discovery_report.json       # Discovery + triage report
    discovery_report.html       # HTML version
    forge-{run_id}.json         # Readiness report (post-remediation)
    forge-{run_id}.html         # HTML version
  telemetry/
    invocations.jsonl           # Per-agent metrics
    cost_summary.json           # Cost breakdown
    training_data.jsonl         # Finding→Fix pairs
.forge-checkpoints/             # Resume after crash
.forge-worktrees/               # Isolated branches per fix
```

---

## Discovery Reports

After the discovery + triage phase, FORGE generates a structured report in two formats: JSON (`discovery_report.json`) and HTML (`discovery_report.html`), stored under `.artifacts/report/`.

**Report contents:**
- **Findings table** — all findings sorted by severity, with tier assignments from triage
- **Architecture context** — modules, entry points, data flows, auth boundaries (from Agent 1's `CodebaseMap`)
- **Remediation plan** — execution order and dependency graph from the Fix Strategist
- **Finding hotspots** — findings grouped by module to identify high-risk areas
- **Repo stats** — LOC total, file count, primary language, runtime
- **Cost** — total LLM cost for the discovery + triage run

Per-finding "ripple tags" cross-reference each finding with the data flows it touches, making it easy to trace impact across the codebase.

**Hive Discovery mode:** As an alternative to classic sequential discovery, FORGE supports swarm-based discovery via `config.discovery_mode = "swarm"`. This runs a hive of parallel workers that chunk the codebase and discover findings concurrently, then synthesizes results. Useful for large repos where classic discovery would be slow.

---

## LLM Output Normalization

Raw LLM outputs are normalized before Pydantic validation to prevent silent dropping of findings:

| Field | Normalization | Example |
|-------|--------------|---------|
| `category` | Aliases mapped to canonical values | `code_patterns` -> `quality`, `error_handling` -> `reliability`, `auth_flow`/`data_handling`/`infrastructure`/`auth` -> `security`, `perf` -> `performance` |
| `priority` | Values < 1 clamped to 1 | `0` -> `1`, `-1` -> `1` |
| `dependency` | List coerced to first element or empty string | `["F-001", "F-002"]` -> `"F-001"`, `[]` -> `""` |

These normalizations run before Pydantic model construction, catching common LLM output variations that would otherwise cause validation failures and silently drop findings.

---

## Environment Variables

**Required for FORGE:**
- `OPENROUTER_API_KEY` — for all LLM calls

**Platform mode (AgentField):**
- `FORGE_NODE_ID` (default: `forge-engine`)
- `FORGE_PORT` (default: `8004`)
- `FORGE_HOST` (default: `0.0.0.0`)
- `AGENTFIELD_SERVER` (default: `http://localhost:8080`)
- `AGENTFIELD_API_KEY` — if control plane requires auth

**Vibe2Prod backend config (config.py):**
- `FORGE_ENABLED` (default: `false`)
- `FORGE_AGENTFIELD_URL` (default: `http://localhost:8080`)
- `FORGE_DEFAULT_MODEL` (default: `minimax/minimax-m2.5`)

---

## Cost Targets

| Metric | Target |
|--------|--------|
| Discovery scan | ~$0.30-0.50 |
| Full remediation (35 findings) | $2-5 |
| Time (full pipeline) | 25-30 minutes |
| Agent invocations (full) | ~97 |

Cost is tracked per-agent with per-model pricing from OpenRouter.

---

## Key Design Decisions

1. **Sonnet 4.6 for coders** — non-negotiable per spec; other agents use cheaper models
2. **Parallel where possible** — Agents 2-4 parallel, test+review parallel, fixes within a level parallel
3. **Worktree isolation** — each fix in its own git branch, merge on approval
4. **Checkpoint resume** — crash recovery at phase boundaries
5. **Tier 1 fast path** — deterministic templates skip LLM entirely
6. **Training flywheel** — every fix logged as finding→outcome pair for future fine-tuning
