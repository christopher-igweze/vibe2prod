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
| `POST` | `/api/fix` | Trigger auto-fix (FORGE) |
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

## Infrastructure

- **Database**: Supabase (PostgreSQL + RLS + JWT auth)
- **Sandboxes**: Daytona (ephemeral Linux containers)
- **LLM routing**: OpenRouter (model-agnostic)
- **CI/CD**: GitHub Actions
