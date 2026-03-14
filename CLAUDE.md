# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Vibe2Prod is a FastAPI backend + Next.js frontend that audits AI-generated codebases and hardens them for production.
- **FORGE Engine:** 12-agent AI discovery and remediation engine in a separate repo (`christopher-igweze/forge-engine`), called via HTTP through `services/forge_bridge.py`

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
  services/
    supabase_client.py → All DB operations (scans, projects, indexes, quotas, artifacts)
    forge_bridge.py    → HTTP bridge to FORGE engine via AgentField async API
    github.py          → GitHub API: repo info, head SHA, repo parsing
    openrouter.py      → OpenRouter LLM client
    context_store.py   → Context management
  sandbox/             → Daytona SDK integration for ephemeral containers
  models/              → Pydantic data models (scan, findings, builds, onboarding, etc.)
benchmarks/
  discovery_triage_001/  → 3x3 matrix benchmark (9 repos × 3 size groups)
  discovery_triage_002/  → User-provided repo benchmarks + runner script (run_discovery.py)
```

## Key Patterns

**Request flow:** Client → CORS → SlowAPI rate limit → SupabaseAuthMiddleware (JWT) → Route handler

**FORGE discovery:** `POST /api/audit` → `forge_bridge.trigger_forge_scan()` → HTTP POST to AgentField → poll for completion → parse ForgeRunResult → store discovery report in Supabase → SSE streaming via `/api/status/{scan_id}`

**FORGE remediation:** `POST /api/fix` → `forge_bridge.trigger_forge_remediate()` → HTTP POST to AgentField → poll for completion → parse ForgeRunResult. Validates the scan, triggers FORGE remediation in a `BackgroundTask`, stores results in Supabase, and updates scan status.

**Config is strict:** `config.py` uses Pydantic BaseSettings with implicit `extra="forbid"`. Any env var in `.env` not declared in Settings will crash the app. When adding new env vars, add them to both `config.py` and `.env.example`. FORGE-specific config fields include `forge_node_id` and `agentfield_api_key` (in addition to existing `forge_enabled`, `forge_agentfield_url`, `forge_default_model`).

**Auth model:** Supabase JWT with `user_id` extracted from `sub` claim. All routes require auth except `/`, `/health`, `/docs`, `/api/webhook/*`.

## FORGE Engine Context

The FORGE engine is documented in `docs/forge-engine-context.md`. Key points:
- 12 agents across 4 phases: Discovery (codebase analyst, security/quality auditors, architecture reviewer) → Triage (classifier, fix strategist) → Remediation (coders, test gen, code reviewer, escalation) → Validation (integration validator, debt tracker)
- Three-loop control: inner (coder retry, max 3), middle (escalation: reclassify/split/defer), outer (replan, max 1)
- Sonnet 4.6 for coders, Haiku 4.5 for planning agents, Minimax M2.5 for cheap analysis
- Returns `ForgeResult` with findings count, fixes applied, Production Readiness Score (0-100)

## Database

Supabase (PostgreSQL + RLS). Migrations in `supabase/migrations/`. All DB access goes through `services/supabase_client.py` using the service role key (bypasses RLS for backend operations).

## Sibling Repos

- **forge-engine** (`../forge-engine`): 12-agent AI remediation engine. Has its own specs in `docs/superpowers/specs/`.
- **security-probe** (`../security-probe`): Live vulnerability scanning microservice. Has its own specs in `docs/superpowers/specs/`.
