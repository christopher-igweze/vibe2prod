# Vibe2Prod Frontend Implementation Plan

## Context

Vibe2Prod is a backend-only FastAPI app today. No frontend exists. The backend has a complete API for auditing codebases (Tier 1 free scanning with 15 static checks + LLM-assisted reports), GitHub OAuth, onboarding, SSE progress streaming, and multi-format report artifacts (markdown, PDF). The goal is to build a simple, clean frontend that serves as:

1. **A waitlist landing page** — collect emails, gate access
2. **A scan interface** — paste GitHub URL or connect GitHub OAuth → run a free audit
3. **A report viewer** — view reports on-site + download as MD/PDF

Users must join the waitlist to unlock 5 free scans.

**Branch:** All work on `feature/frontend-waitlist` (off `main`). Micro-commits per phase. No merge to main without explicit confirmation.

**FORGE context:** FORGE is a separate HTTP service called via `forge_bridge.py` → AgentField API. Currently disabled (`FORGE_ENABLED=false`). The frontend doesn't talk to FORGE directly — it uses `POST /api/fix` which the backend proxies to FORGE. Both `trigger_forge_scan` and `trigger_forge_remediate` now accept a `project_context` parameter for context-aware remediation. Not part of this frontend build (Phase 5+).

---

## Recent Backend Changes (Affecting Frontend)

### Security Hardening
- **SSE ownership check** — `GET /api/status/{scan_id}` now returns 403 if user doesn't own the scan
- **Fix ownership check** — `POST /api/fix` now returns 403 if user doesn't own the project
- **Rate limits added** — `POST /api/onboarding/org` and `GET /api/status/{scan_id}` now rate-limited (429 responses)
- **Atomic quota** — `increment_reports_if_under_cap()` uses optimistic locking (no concurrent slip-through)
- **OAuth state secret required** — `GITHUB_OAUTH_STATE_SECRET` must be set or OAuth returns 503

### Actionability Classifier (New)
Findings are now classified into **four actionability tiers** based on severity, confidence, and project context:

| Tier | Meaning | Color |
|------|---------|-------|
| `must_fix` | Exploitable now, ship blocker | Red |
| `should_fix` | Real issue, prioritize this sprint | Orange |
| `consider` | Valid observation, may not be urgent | Yellow |
| `informational` | Noted for awareness only | Blue |

Classification is **context-aware**: same finding may be `must_fix` in enterprise but `consider` in MVP. Known compromises (from ProjectIntake) are auto-downgraded to `informational`.

### New Finding Fields
`Tier1Finding` (in `tier1/contracts.py`) now includes:
```python
actionability: str = ""   # must_fix | should_fix | consider | informational
data_flow: str = ""        # "user input → validation → SQL query → database"
pattern_id: str = ""       # "VP-001"
pattern_slug: str = ""     # "client_writable_authority"
```

### Pattern Library (New)
Scanner now runs **two passes**: 15 deterministic checks + pattern library evaluation. Three curated patterns:
- **VP-001:** Client-writable authority columns (critical) — BaaS users modifying role/tier columns
- **VP-002:** Client-only premium gating (high) — localStorage-only feature restrictions
- **VP-003:** Unprotected admin endpoints (high) — /admin routes without auth

Findings from patterns have `engine="pattern_library"` and link back via `pattern_id`/`pattern_slug`.

### Report Structure Changes
Reports now group findings by actionability tier (not just severity). Summary JSON includes:
```json
{
  "counts": {
    "by_actionability": { "must_fix": 1, "should_fix": 2, "consider": 2, "informational": 0 }
  }
}
```

Markdown reports use headings: "Must Fix — fix before shipping", "Should Fix — prioritize this sprint", etc.

### Project Context Threading
`ProjectIntake` → `intake_to_forge_context()` → flows through actionability classification AND to FORGE agents. Every intake field now matters for finding prioritization (project_origin → project_stage, scale_expectation → severity calibration, must_not_break_flows → beloved_features).

---

## Decisions

- **Domain:** vibe2prod.com — used throughout branding, CORS, OG metadata
- **Auth:** Clerk (`@clerk/nextjs`) with Supabase third-party integration
- **Waitlist:** Clerk's native `<Waitlist />` component (no custom table needed)
- **Input method:** GitHub URL only (no file upload — deferred to Phase 5)
- **SSE auth:** fetch + ReadableStream (passes Bearer token in headers)
- **Quota:** 5 lifetime scans for waitlist users

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | **Next.js 15 (App Router)** | SSR for SEO on landing page, client components for app |
| Styling | **Tailwind CSS + shadcn/ui** | Fast, accessible, production-ready components |
| Auth | **Clerk** (`@clerk/nextjs` ≥6.2.0) | Native waitlist, pre-built UI, GitHub OAuth, Supabase integration |
| Data fetching | **@tanstack/react-query** | Cache, dedupe, SSE-friendly |
| Markdown | **react-markdown + remark-gfm + rehype-highlight** | Renders existing Tier1 markdown reports |
| Forms | **react-hook-form + zod** | Type-safe validation mirroring Pydantic models |
| Hosting | **Vercel** | Zero-config Next.js, preview deploys |

**Location:** `frontend/` directory in the existing vibe2prod repo.

---

## Auth Architecture

### Clerk + Supabase Third-Party Integration (New Method)

The old approach (Clerk JWT templates with shared `SUPABASE_JWT_SECRET`) is **deprecated as of April 2025**. The new approach uses Supabase's native third-party auth support for Clerk.

**Setup:**
1. In Clerk dashboard: go to "Connect with Supabase" page to configure Clerk instance
2. In Supabase dashboard: add Clerk as a Third-Party Auth integration
3. For local dev, add to `supabase/config.toml`:
   ```toml
   [auth.third_party.clerk]
   enabled = true
   domain = "your-app.clerk.accounts.dev"
   ```
4. In Clerk dashboard: customize session token to include `role: "authenticated"` claim

**Frontend → Supabase (direct DB access via RLS):**
```typescript
const supabaseClient = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  {
    accessToken: async () => session?.getToken() ?? null,
  }
)
```

**Frontend → FastAPI Backend (cross-origin API calls):**
The backend middleware (`auth.py`) currently validates JWTs with HS256 + `supabase_jwt_secret`. With Clerk's third-party integration, Clerk session tokens are **RS256-signed** JWTs verified via Clerk's JWKS endpoint. The backend auth middleware **must be updated** to:
- Fetch Clerk's public key from JWKS: `https://api.clerk.com/v1/jwks` or `{clerk-frontend-api}/.well-known/jwks.json`
- Verify RS256 signatures instead of HS256
- Validate `exp`, `nbf`, and optionally `azp` claims
- Extract `sub` claim as `user_id` (same as before)

**Modified `auth.py` approach:**
```python
# Fetch JWKS from Clerk (cached)
# Verify with RS256 algorithm
# Extract sub → request.state.user_id
```

This is the **only backend auth change needed** — all downstream code still uses `request.state.user_id`.

### Profile Sync

Clerk webhook (`user.created`, `user.updated`) → `POST /api/webhook/clerk`:
- Upsert `profiles` row with Clerk user ID, email, name
- Validates `svix` signature header using `clerk_webhook_secret`
- On `user.created`: also set `waitlist_status = 'approved'` (since Clerk waitlist already gates access)

---

## Waitlist (Clerk Native)

Clerk has a built-in waitlist feature (requires `@clerk/nextjs` ≥6.2.0):

**How it works:**
1. Enable "Waitlist" in Clerk Dashboard → Waitlist page
2. Users see `<Waitlist />` component instead of `<SignUp />`
3. Users submit email/name to join the waitlist
4. Admin approves/denies via Clerk Dashboard (Waitlist page → ... menu → Invite/Deny)
5. Approved users receive an email with access to `<SignIn />`
6. `<SignUp />` is restricted to users with valid invitation links only

**Frontend setup:**
```tsx
// Landing page — waitlist form
<Waitlist />

// ClerkProvider config
<ClerkProvider waitlistUrl="/waitlist">
```

**No custom waitlist table needed.** Clerk manages the entire queue. The `profiles.lifetime_scans_used` / `lifetime_scan_cap` columns handle the 5-scan quota separately.

**Auto-approve option:** For early traction, you can manually batch-approve all waitlist entries regularly in the Clerk dashboard. Or use Clerk's Backend API to auto-approve programmatically via a cron job.

---

## GitHub Auth for Private Repos

### Clerk GitHub OAuth Scopes

When configuring GitHub as a social connection in Clerk dashboard, request these scopes for private repo access:

- `repo` — Full control of private repositories (read/write)
- `read:user` — Read user profile data (Clerk needs this by default)

**Configure in Clerk Dashboard:** SSO Connections → GitHub → Custom scopes → add `repo`

Or use `additionalOAuthScopes` on the frontend for post-signup scope escalation:
```tsx
<UserProfile
  additionalOAuthScopes={{
    github: ['repo'],
  }}
/>
```

### Retrieving the GitHub Token

Clerk stores the GitHub OAuth token as part of the social connection. To get it (server-side only):

```typescript
const client = await clerkClient()
const oauthTokens = await client.users.getUserOauthAccessToken(userId, 'github')
const githubToken = oauthTokens.data[0]?.token || ''
```

**Important:** Clerk does NOT auto-refresh OAuth tokens. Must explicitly request when needed.

### Two Paths for GitHub Connection

**Path A: Clerk GitHub Social Login** (primary)
- User signs up/logs in via GitHub through Clerk
- Clerk stores the GitHub OAuth token as part of the social connection
- When a scan needs private repo access, a Next.js API route fetches the token via `getUserOauthAccessToken()` and passes it to the FastAPI backend
- OR: the Clerk `user.created` webhook extracts and stores it in `profiles.github_access_token`

**Path B: Connect GitHub Later** (secondary)
- User signs up with email, no GitHub
- Later clicks "Connect GitHub" on `/settings` or during scan creation
- Uses existing backend OAuth flow: `POST /api/github-oauth { action: "get_auth_url" }` → redirect → exchange → token stored in `profiles.github_access_token`

**Existing backend files (unchanged):**
- `api/routes/github_oauth.py` — OAuth flow (get_auth_url, exchange_code, disconnect)
- `services/supabase_client.py` — `save_github_connection()`, `get_github_access_token()`
- `tier1/indexer.py` — Uses stored token for GitHub API cloning
- `config.py` — `github_client_id`, `github_client_secret`, `github_oauth_scope`

---

## Backend Changes Required

### 1. Supabase Migration: profile columns for lifetime cap

```sql
-- No waitlist table needed (Clerk handles it)
-- Add lifetime scan tracking to profiles
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS lifetime_scans_used integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS lifetime_scan_cap integer NOT NULL DEFAULT 5;
```

### 2. Auth Middleware Update

**File:** `backend/api/middleware/auth.py`

Replace HS256 + `supabase_jwt_secret` verification with RS256 + Clerk JWKS verification:
- Fetch JWKS from Clerk (cache with TTL)
- Verify RS256 signature
- Validate `exp`, `nbf` claims
- Extract `sub` → `request.state.user_id` (unchanged contract)
- Add `"/api/webhook/clerk"` to `PUBLIC_PREFIXES`

New dependency: `PyJWKClient` from `PyJWT[crypto]` (already uses `PyJWT`, just needs `cryptography` extra)

### 3. New API Endpoints

| File | Endpoint | Auth | Purpose |
|------|----------|------|---------|
| `api/routes/user.py` | `GET /api/user/profile` | Required | Profile + onboarding status + scan quota |
| `api/routes/user.py` | `GET /api/user/scans` | Required | List scan history for dashboard |
| `api/routes/webhook_clerk.py` | `POST /api/webhook/clerk` | Svix signature | Profile upsert on user.created/updated |

### 4. Modified Backend Files

- **`main.py`** (L65-71): Update CORS `allow_origin_regex` to include `vibe2prod.com` + `*.vercel.app`. Mount new `user` and `webhook_clerk` routers.
- **`api/middleware/auth.py`**: RS256 + JWKS verification (see section 2 above).
- **`config.py`**: Add `clerk_publishable_key`, `clerk_secret_key`, `clerk_webhook_secret`, `clerk_jwks_url` settings.
- **`services/supabase_client.py`**: Add `get_user_profile()`, `list_user_scans()`, `upsert_profile_from_clerk()`, `check_lifetime_scan_cap()`, `increment_lifetime_scans()`.

### 5. Supabase Config Update

Add to `supabase/config.toml`:
```toml
[auth.third_party.clerk]
enabled = true
domain = "your-app.clerk.accounts.dev"
```

---

## Frontend Structure

```
frontend/
  src/
    app/
      layout.tsx                          # Root layout, ClerkProvider, QueryClientProvider
      page.tsx                            # Landing page with Clerk <Waitlist /> component
      waitlist/page.tsx                   # Dedicated waitlist page (if separate from landing)
      (auth)/
        sign-in/[[...sign-in]]/page.tsx   # Clerk <SignIn />
        sign-up/[[...sign-up]]/page.tsx   # Clerk <SignUp /> (invite-only after waitlist)
      (app)/
        layout.tsx                        # App shell (nav, auth guard)
        dashboard/page.tsx                # Projects, recent scans, quota
        onboarding/page.tsx               # Org onboarding wizard
        scan/
          new/page.tsx                    # Paste URL → intake form → submit
          [scanId]/page.tsx               # Live SSE progress timeline
          [scanId]/report/page.tsx        # Score cards + markdown viewer + download
        settings/page.tsx                 # GitHub connection, preferences
    components/
      ui/                                 # shadcn/ui primitives
      landing/                            # hero, features, how-it-works, footer
      scan/                               # repo-input, intake-form, scan-progress, score-card
      report/                             # report-viewer, report-download, findings-list
    lib/
      api/client.ts                       # Typed fetch wrapper (uses Clerk getToken for Bearer)
      api/types.ts                        # TS types mirroring Pydantic models (scan.py, contracts.py)
      api/sse.ts                          # fetch-based SSE with error handling (403, 429, reconnect)
      hooks/use-scan-stream.ts            # SSE hook for scan progress
    middleware.ts                          # clerkMiddleware — protect /dashboard, /scan/*, /settings
```

---

## Key Pages & Flows

### Landing Page (`/`) — Server Component, Static
- Hero: headline + subheadline
- Clerk `<Waitlist />` component (client island) — collects email, managed by Clerk
- Features: 3 cards (Scan, Report, Harden)
- How It Works: 3-step visual
- Footer

### Auth Flow
- Clerk `<Waitlist />` → user joins queue → admin approves in Clerk Dashboard → user gets invite email
- Approved user signs in via Clerk `<SignIn />` (email/password, magic link, or GitHub OAuth)
- `clerkMiddleware` in `middleware.ts` protects `/dashboard`, `/scan/*`, `/settings`
- On API calls to FastAPI: `const token = await getToken()` → `Authorization: Bearer ${token}`
- Profile auto-created via Clerk `user.created` webhook → `POST /api/webhook/clerk`

### Scan Flow (`/scan/new` → `/scan/[scanId]` → `/scan/[scanId]/report`)
1. Check quota via `GET /api/limits` — block if `lifetime_scans_used >= lifetime_scan_cap`
2. Paste GitHub URL (validated client-side: `github.com/owner/repo`)
3. Optionally call `POST /api/primer` for repo pre-analysis
4. Fill intake form matching `ProjectIntake` model: project_origin, product_summary, target_users, sensitive_data, must_not_break_flows, deployment_target, scale_expectation
   - **Important:** Every intake field now feeds into actionability classification (project_origin → project_stage, scale_expectation → severity calibration). Make the form feel important, not skippable.
5. Submit → `POST /api/audit` → returns `scan_id` → redirect to `/scan/[scanId]`
6. SSE progress via `fetch` + `ReadableStream` (passes Bearer token in headers)
7. On `scan_complete` → show scores + actionability summary + "View Report" button

### Error Handling (Required)
The backend now enforces ownership and rate limits. Frontend must handle:
- **403 on SSE** — user doesn't own scan → redirect to dashboard with toast
- **403 on /api/fix** — user doesn't own project → show error message
- **429 on SSE/onboarding** — rate limited → exponential backoff with user message
- **503 on OAuth** — `GITHUB_OAUTH_STATE_SECRET` missing → show "GitHub not configured" admin message
- **SSE reconnect** — 10-minute inactivity timeout closes stream → reconnect with jitter

### Report Viewer (`/scan/[scanId]/report`)

**Score Dashboard (top)**
- Health/security/reliability/scalability gauges (0-100)
- Actionability summary badges: "2 Must Fix · 3 Should Fix · 5 Consider · 1 Info" (from `counts.by_actionability`)

**Download Bar**
- MD button + PDF button (`GET /api/report-artifacts/{scanId}?artifact_type=...`)

**Findings (primary view — grouped by actionability)**
- **Must Fix** section (red) — ship blockers, expanded by default
- **Should Fix** section (orange) — collapsed by default
- **Consider** section (yellow) — collapsed
- **Informational** section (blue) — collapsed
- Each finding card shows:
  - Severity badge + actionability label
  - Title + description
  - `data_flow` trace (e.g., "user input → form → SQL query") when present
  - File path + line number
  - Pattern attribution badge when `pattern_id` is set (e.g., "VP-001")
  - Suggested fix (expandable)
- Filterable by severity, category, and actionability tier

**Markdown Report (secondary tab)**
- Full markdown rendered via `react-markdown` with Tailwind `prose` typography
- Reports already self-organize by actionability tier headings

**Analysis Methodology (footer section)**
- Pattern library table: patterns checked, hits per pattern, CWE IDs
- Project stage context badge explaining prioritization calibration

---

## Implementation Phases

### Phase 1: Foundation + Waitlist
- Init Next.js in `frontend/` with Tailwind + shadcn/ui
- Landing page with Clerk `<Waitlist />` component
- Clerk setup: `@clerk/nextjs`, enable waitlist in Clerk dashboard, sign-in/sign-up pages
- Configure Clerk + Supabase third-party integration
- Update backend `auth.py`: RS256 + JWKS verification (replaces HS256)
- Backend: `POST /api/webhook/clerk` for profile auto-creation
- Supabase migration: add `lifetime_scans_used`/`lifetime_scan_cap` to profiles
- Update CORS in `main.py`
- Deploy to Vercel

### Phase 2: Onboarding + Dashboard
- Backend: `GET /api/user/profile`, `GET /api/user/scans`
- Onboarding wizard mapping to `OrgOnboardingPayload`
- Dashboard with quota badge + empty state
- App shell (nav, Clerk `<UserButton />`)
- Settings page with GitHub OAuth connection

### Phase 3: Scan Flow + Error Handling
- `/scan/new` — repo input + intake form (emphasize context importance) + primer call
- `/scan/[scanId]` — SSE progress timeline with reconnect logic
- Wire `POST /api/audit` + lifetime cap enforcement
- Handle all SSE event types
- Error handling: 403 (ownership), 429 (rate limit), SSE timeout/reconnect

### Phase 4: Report Viewer + Polish
- Score cards with gauges + actionability summary badges
- Findings view: grouped by actionability tier (must_fix/should_fix/consider/informational)
- Finding cards: severity, actionability label, data_flow trace, pattern_id badge, suggested fix
- Markdown report tab (secondary view)
- MD + PDF download
- Analysis methodology section (pattern library hits table)
- Loading skeletons, error boundaries, mobile responsive pass
- SEO metadata (OG, Twitter cards)

### Phase 5 (Post-launch)
- Repo upload (needs new backend endpoint)
- GitHub repo browser (browse connected repos)
- Scan history comparisons
- Email notifications on scan complete

---

## Frontend Data Models (TypeScript)

Key types to mirror from backend (source: `tier1/contracts.py`, `models/scan.py`):

```typescript
type Actionability = 'must_fix' | 'should_fix' | 'consider' | 'informational'
type Severity = 'critical' | 'high' | 'medium' | 'low'
type Category = 'security' | 'reliability' | 'scalability'

interface Tier1Finding {
  check_id: string
  title: string
  description: string
  category: Category
  severity: Severity
  status: 'fail' | 'warn' | 'pass' | 'skip'
  confidence: number           // 0.0-1.0
  actionability: Actionability // NEW — primary grouping axis
  data_flow: string            // NEW — "user input → validation → SQL"
  pattern_id: string           // NEW — "VP-001" (empty if not pattern-based)
  pattern_slug: string         // NEW — "client_writable_authority"
  engine: string               // "regex" | "ast" | "pattern_library" | etc.
  file_path: string
  line_number: number | null
  evidence: string
  why_it_matters: string
  suggested_fix: string
}

interface ReportSummary {
  scores: {
    health_score: number
    security_score: number
    reliability_score: number
    scalability_score: number
  }
  counts: {
    findings_total: number
    by_severity: Record<Severity, number>
    by_category: Record<Category, number>
    by_actionability: Record<Actionability, number>  // NEW
  }
}
```

---

## Clerk Dashboard Setup Checklist

Before coding, configure in Clerk Dashboard:
1. [ ] Enable Waitlist (Waitlist page → toggle on)
2. [ ] Add GitHub as social connection (SSO Connections → GitHub)
3. [ ] Set GitHub custom scopes: `repo` (for private repo access)
4. [ ] Customize session token: add `role: "authenticated"` claim
5. [ ] Configure "Connect with Supabase" integration
6. [ ] Set up Webhook endpoint: `https://api.vibe2prod.com/api/webhook/clerk`
7. [ ] Subscribe to webhook events: `user.created`, `user.updated`
8. [ ] Copy webhook signing secret → `CLERK_WEBHOOK_SECRET` env var

---

## Environment Variables

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_WAITLIST_URL=/
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=eyJ...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (add to `backend/.env`)
```
CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json
CLERK_WEBHOOK_SECRET=whsec_...
```

---

## Verification Plan

1. **Waitlist:** Visit `/` → Clerk `<Waitlist />` renders → submit email → appears in Clerk Dashboard → approve → user gets invite email
2. **Auth:** Clerk sign-in → `getToken()` → Bearer token accepted by updated FastAPI middleware → `request.state.user_id` = Clerk user ID
3. **Profile sync:** Sign up → Clerk webhook fires → `profiles` row created in Supabase
4. **GitHub:** Sign in with GitHub → Clerk stores OAuth token → `getUserOauthAccessToken()` returns valid token → can clone private repos
5. **Scan:** Paste a public GitHub URL → fill intake → submit → SSE events render in timeline → `scan_complete` shows scores + actionability summary
6. **Report — Actionability grouping:** Findings grouped by must_fix/should_fix/consider/informational → correct color coding → expandable cards with data_flow traces
7. **Report — Pattern attribution:** Findings with `pattern_id` show VP-xxx badge → methodology section shows pattern hits table
8. **Report — Downloads:** Download MD → opens correctly → download PDF → opens correctly
9. **Report — Context awareness:** Run same repo with MVP vs Enterprise intake → verify different actionability classifications
10. **Error handling:** Attempt SSE on another user's scan → 403 handled gracefully → rate limit triggered → 429 handled with backoff
11. **Quota:** Run 5 scans → 6th attempt blocked with "limit reached" message
12. **Mobile:** All pages responsive at 375px viewport
