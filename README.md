# Vibe2Prod

AI-powered code audit and production-hardening platform. Turns vibe-coded MVPs into production-ready software.

## What It Does

Vibe2Prod audits code repositories for security, reliability, scalability, and architectural issues using the [FORGE engine](https://github.com/christopher-igweze/forge-engine) — a 3-agent AI pipeline backed by deterministic SAST analysis. It scores repos across multiple dimensions, generates remediation plans, and provides a Production Readiness Score.

## Tech Stack

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Clerk (auth), TanStack Query, shadcn/ui |
| **Backend** | FastAPI, Python 3.12, Pydantic v2, httpx (async) |
| **Database** | Supabase (PostgreSQL + RLS + JWT) |
| **Auth** | Clerk (frontend) → Supabase JWT (backend) |
| **LLM Routing** | OpenRouter (model-agnostic) |
| **FORGE Engine** | Separate repo — called via HTTP bridge |
| **Payments** | Stripe (wallet-based PAYG + BYOK) |

## Architecture

```
frontend/                    # Next.js 16 (App Router, Turbopack)
├── src/app/
│   ├── (auth)/              # Sign-in/sign-up (Clerk)
│   ├── (app)/               # Protected app routes
│   │   ├── dashboard/       # Scan history, metrics, projects
│   │   ├── scan/new         # Multi-step audit wizard
│   │   ├── scan/[id]        # Live scan progress + report
│   │   ├── settings/        # User preferences, API keys
│   │   └── pricing/         # Billing & credits
│   ├── cli/                 # CLI documentation
│   └── page.tsx             # Landing page
├── src/components/
│   ├── landing/             # 17 marketing sections
│   ├── dashboard/           # Stats, scans, projects
│   ├── scan/                # Wizard (repo → intake → review)
│   └── ui/                  # shadcn/ui primitives
└── src/hooks/               # Dashboard state, repo selection, user role

backend/
├── main.py                  # FastAPI app + middleware stack
├── config.py                # Pydantic Settings (strict, extra="forbid")
├── api/
│   ├── routes/              # 12 route modules
│   └── middleware/          # Auth (Supabase JWT), rate limiting
├── services/
│   ├── repositories/        # 14 focused data access modules
│   ├── forge_bridge.py      # HTTP bridge to FORGE engine
│   ├── forge_executor.py    # Async execution + polling
│   ├── github_oauth_flow.py # GitHub OAuth (RFC 6749)
│   ├── github_token_manager.py  # Token encryption (AES-256)
│   └── openrouter_key_manager.py # BYOK support
├── sandbox/                 # Daytona SDK — ephemeral containers
└── models/                  # Pydantic data models

supabase/                    # 27+ migrations
docker-compose.yml           # 3 services: frontend, api, forge
```

## Features

**Audit Pipeline**
- Multi-step scan wizard: repo selection → project intake → review & submit
- FORGE discovery: Opengrep SAST + 3 AI agents (Codebase Analyst, Security Auditor, Fix Strategist)
- Deterministic evaluation: 47 checks across 7 dimensions (security, reliability, maintainability, test quality, performance, docs, ops)
- Production Readiness Score with band ratings (A–F)
- AIVSS scoring for agentic AI projects

**Dashboard**
- Scan history with status, timing, and cost tracking
- Project management (group scans by repo)
- Live SSE updates for in-progress scans
- Usage stats (LLM cost, infra cost, findings per scan)

**Pricing**
- Free tier (limited scans)
- PAYG (wallet-based, Stripe)
- BYOK (bring-your-own OpenRouter key, no wallet charge)
- Developer role (unlimited)

**Integrations**
- GitHub OAuth with encrypted token storage
- GitHub webhooks (push/PR events)
- CLI: `pip install vibe2prod && vibe2prod scan ./my-app` (code stays local)
- MCP server for Claude Code integration

## Quick Start

```bash
# Docker (recommended)
docker-compose up

# Or manually:

# Backend
cp backend/.env.example backend/.env   # Add your keys
cd backend && pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm install
npm run dev
```

## API Endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `POST` | `/api/audit` | Start FORGE discovery scan | JWT |
| `GET` | `/api/status/{scan_id}` | SSE stream of scan progress | JWT |
| `POST` | `/api/fix` | Trigger FORGE remediation | JWT |
| `POST` | `/api/primer` | Analyze repo (cached per SHA) | JWT |
| `GET` | `/api/user/me` | User profile | JWT |
| `PATCH` | `/api/user/me` | Update preferences | JWT |
| `POST` | `/api/github/oauth/callback` | GitHub OAuth redirect | Public |
| `POST` | `/api/webhook/github` | GitHub push/PR webhooks | HMAC |
| `POST` | `/api/webhook/clerk` | Clerk auth webhooks | HMAC |
| `GET` | `/health` | Health check | Public |

## FORGE Engine

The audit engine lives at [`christopher-igweze/forge-engine`](https://github.com/christopher-igweze/forge-engine). v3 uses 3 LLM agents + Opengrep SAST + 47 deterministic evaluation checks. Scans cost ~$0.21.

```bash
# Local CLI (code stays on your machine)
pip install vibe2prod
vibe2prod scan ./my-app
```

## Environment Variables

**Backend** — `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `OPENROUTER_API_KEY`, `DAYTONA_API_KEY`, `DAYTONA_API_URL`, plus optional GitHub/Clerk/Stripe/FORGE keys.

**Frontend** — `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_API_URL`.

See `.env.example` files for the full list.

## Infrastructure

- **Frontend**: Vercel (Next.js optimized)
- **Backend**: Docker (FastAPI + uvicorn)
- **Database**: Supabase (PostgreSQL + RLS)
- **Sandboxes**: Daytona (ephemeral Linux containers)
- **LLM Routing**: OpenRouter (model-agnostic)
