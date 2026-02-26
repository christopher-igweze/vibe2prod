# Vibe2Prod

AI-powered code audit and production-hardening platform. Turns vibe-coded MVPs into production-ready software.

## Architecture

```
vibe2prod/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Pydantic settings (env-driven)
│   ├── api/
│   │   ├── routes/          # 7 core route modules
│   │   └── middleware/      # Auth (Supabase JWT), rate limiting
│   ├── tier1/               # Free deterministic scanner (no LLM cost)
│   ├── sandbox/             # Daytona SDK — ephemeral container management
│   ├── services/            # Supabase, GitHub, OpenRouter, FORGE bridge
│   └── models/              # Pydantic data models
├── supabase/                # Database migrations & config
├── benchmarks/              # FORGE discovery/triage benchmarks
├── doc/                     # FORGE engine integration context
└── docker-compose.yml
```

## Two Execution Tiers

| Tier | What | Cost | How |
|------|------|------|-----|
| **Free (Tier 1)** | Deterministic code scan — security, quality, architecture | $0 | `POST /api/audit` with `tier1_only=true` |
| **Pro (FORGE)** | 12-agent AI remediation — finds AND fixes issues | $2-5/run | FORGE engine via AgentField in Daytona sandbox |

## Quick Start

```bash
# 1. Set up environment
cp backend/.env.example backend/.env
# Edit .env with your keys (Supabase, OpenRouter, Daytona)

# 2. Install dependencies
cd backend && pip install -r requirements.txt

# 3. Run
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/audit` | Start a code audit (Tier 1 or FORGE) |
| `GET` | `/api/status/{scan_id}` | SSE stream of audit progress |
| `POST` | `/api/fix` | Trigger FORGE remediation (BackgroundTask, stores results in Supabase) |
| `POST` | `/api/github/oauth/callback` | GitHub OAuth flow |
| `POST` | `/api/webhook/github` | GitHub push/PR webhooks |
| `GET` | `/health` | Health check |

## FORGE Engine (Separate Repo)

The 12-agent remediation engine lives at [`christopher-igweze/forge-engine`](https://github.com/christopher-igweze/forge-engine). It runs as an AgentField node in Daytona sandboxes and is called via HTTP from this backend's `forge_bridge` service.

For local CLI usage (code stays on your machine):
```bash
pip install vibe2prod
vibe2prod scan ./my-app
```

## Benchmarks

The `benchmarks/` directory contains FORGE discovery + triage benchmarks for measuring finding quality and cost:

- **`discovery_triage_001/`** — 3x3 matrix (9 repos across 3 size groups), 297 total findings, $7.27 total cost
- **`discovery_triage_002/`** — User-provided repo benchmarks with `run_discovery.py` runner script (auto-loads `OPENROUTER_API_KEY` from `backend/.env`, runs FORGE standalone against any GitHub URL or local path)

## Infrastructure

- **Database**: Supabase (PostgreSQL + RLS + JWT auth)
- **Sandboxes**: Daytona (ephemeral Linux containers)
- **LLM routing**: OpenRouter (model-agnostic)
- **CI/CD**: GitHub Actions
