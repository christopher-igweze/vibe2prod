# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Vibe2Prod is a FastAPI backend that audits AI-generated codebases and hardens them for production. Two tiers:
- **Tier 1 (Free):** Deterministic scanner — no LLM cost, indexes repo via GitHub API, runs 15 static checks, generates an LLM-assisted report
- **FORGE (Paid):** 12-agent AI remediation engine in a separate repo (`christopher-igweze/forge-engine`), called via HTTP through `services/forge_bridge.py`

## Commands

```bash
# Run the backend
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run all tests
cd backend && PYTHONPATH=. pytest -q

# Run a single test file
cd backend && PYTHONPATH=. pytest tests/test_audit_routes.py -q

# Run a single test class or method
cd backend && PYTHONPATH=. pytest tests/test_audit_routes.py::AuditRouteTests::test_name -q

# Docker
docker-compose up
```

Tests use `unittest.TestCase` with `FastAPI.TestClient`. The `.env` file is loaded automatically by Pydantic — tests set env var defaults at module level to avoid requiring real credentials.

## Architecture

```
backend/
  main.py              → FastAPI app, middleware registration, router mounting
  config.py            → Pydantic Settings (loads from .env, strict — extra vars rejected)
  api/
    routes/            → 7 route modules, all mounted under /api
    middleware/
      auth.py          → Supabase JWT verification (skips PUBLIC_PATHS and /api/webhook/)
      rate_limit.py    → slowapi rate limiter
  tier1/
    orchestrator.py    → Tier1Orchestrator: index → scan → report pipeline
    indexer.py         → DeterministicIndexer: clones via GitHub API, builds file/LOC index
    scanner.py         → DeterministicScanner: 15 static checks, no LLM
    reporter.py        → Tier1Reporter: LLM-assisted report generation via OpenRouter
    contracts.py       → Tier1QuotaStatus and shared types
    quota.py           → Monthly usage caps (3 projects, 10 reports, 50k LOC)
  services/
    supabase_client.py → All DB operations (scans, projects, indexes, quotas, artifacts)
    forge_bridge.py    → HTTP bridge to FORGE engine via AgentField async API
    github.py          → GitHub API: repo info, head SHA, repo parsing
    openrouter.py      → OpenRouter LLM client
    context_store.py   → Context management
  sandbox/             → Daytona SDK integration for ephemeral containers
  models/              → Pydantic data models (scan, findings, builds, onboarding, etc.)
```

## Key Patterns

**Request flow:** Client → CORS → SlowAPI rate limit → SupabaseAuthMiddleware (JWT) → Route handler

**Tier 1 pipeline:** `POST /api/audit` (tier1_only=true) → `Tier1Orchestrator.run()` → DeterministicIndexer (GitHub API clone, index with TTL) → DeterministicScanner (15 checks) → Tier1Reporter (OpenRouter LLM call) → Supabase artifact storage → SSE streaming via `/api/status/{scan_id}`

**FORGE integration:** `POST /api/audit` (tier1_only=false) or `POST /api/fix` → `forge_bridge.trigger_forge_remediate()` → HTTP POST to AgentField → poll for completion → parse ForgeRunResult. FORGE is currently disabled (`FORGE_ENABLED=false`).

**Config is strict:** `config.py` uses Pydantic BaseSettings with implicit `extra="forbid"`. Any env var in `.env` not declared in Settings will crash the app. When adding new env vars, add them to both `config.py` and `.env.example`.

**Auth model:** Supabase JWT with `user_id` extracted from `sub` claim. All routes require auth except `/`, `/health`, `/docs`, `/api/webhook/*`.

## FORGE Engine Context

The FORGE engine is documented in `doc/forge-engine-context.md`. Key points:
- 12 agents across 4 phases: Discovery (codebase analyst, security/quality auditors, architecture reviewer) → Triage (classifier, fix strategist) → Remediation (coders, test gen, code reviewer, escalation) → Validation (integration validator, debt tracker)
- Three-loop control: inner (coder retry, max 3), middle (escalation: reclassify/split/defer), outer (replan, max 1)
- Sonnet 4.6 for coders, Haiku 4.5 for planning agents, Minimax M2.5 for cheap analysis
- Returns `ForgeResult` with findings count, fixes applied, Production Readiness Score (0-100)

## Database

Supabase (PostgreSQL + RLS). Migrations in `supabase/migrations/`. All DB access goes through `services/supabase_client.py` using the service role key (bypasses RLS for backend operations).
