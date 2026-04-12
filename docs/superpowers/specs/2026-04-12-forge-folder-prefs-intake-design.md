# Design: .forge/ Folder, Editable Preferences, Skip Repeat Intake

**Date:** 2026-04-12
**Status:** Approved (brainstorming complete)

---

## Overview

Three features that reduce friction for repeat users and make the onboarding data collected during signup actually useful:

1. **`.forge/` folder convention** — per-repo config folder containing project context and suppression entries
2. **Editable scan preferences in Settings** — let users change the 4 behavioral fields after onboarding
3. **Skip intake form on rescan** — don't show the project context questionnaire if context already exists

## 1. `.forge/` Folder Convention

### Structure

```
repo/
├── .forge/
│   ├── context.json      ← project context for FORGE agents
│   └── .forgeignore      ← suppression entries (preferred location)
├── .forgeignore           ← also supported (legacy fallback)
```

### `context.json` Schema

```json
{
  "product_summary": "A SaaS billing app with Stripe checkout",
  "target_users": "Solo founders shipping from Lovable/Bolt",
  "sensitive_data": ["payments", "pii"],
  "critical_flows": ["checkout", "webhook signature verification"],
  "deployment_target": "Vercel + Supabase",
  "scale_expectation": "< 1k users initially",
  "vibe_prompt": "Build a Stripe checkout with subscriptions"
}
```

Same field names as the web intake form — no mapping layer needed. Both CLI and web produce/consume the same shape.

### `.forgeignore` Resolution

1. Check `.forge/.forgeignore` first (preferred)
2. Fall back to root `.forgeignore`
3. If both exist, use `.forge/.forgeignore` and log warning: "Found .forgeignore at both .forge/.forgeignore and repo root. Using .forge/.forgeignore."

### `context.json` Resolution (CLI only)

1. If `--context <path>` flag is passed, use that file (explicit override)
2. Otherwise check `.forge/context.json` in the scanned repo
3. If neither exists, run without project context (backward compatible)

Web UI ignores `.forge/context.json` entirely — it reads from the DB (`scan_reports.project_intake`).

### Who Creates `.forge/`

| Trigger | Behavior |
|---|---|
| `vibe2prod scan ./repo` (CLI, first run) | Creates `.forge/` with template `context.json` (empty fields + instructional comments). Prints: "Created .forge/context.json — edit it to improve scan accuracy." |
| `/forge` skill (Claude Code) | Auto-infers context by reading repo (README, package.json, .env patterns, config files). Writes `.forge/context.json` with inferred values. Shows user the result and asks to confirm before saving. |
| Web UI scan | Stores intake in `scan_reports.project_intake` (DB only). No repo write. |
| `vibe2prod setup` | Does NOT create `.forge/` (setup is per-machine, `.forge/` is per-repo). |

### CLI Template (`context.json` on first scan)

```json
{
  "_comment": "FORGE project context. Edit these fields to improve scan accuracy. See https://docs.vibe2prod.net/context",
  "product_summary": "",
  "target_users": "",
  "sensitive_data": [],
  "critical_flows": [],
  "deployment_target": "",
  "scale_expectation": "",
  "vibe_prompt": ""
}
```

### CLI Context → DB Persistence

When the CLI runs a scan with context (from `.forge/context.json` or `--context`), the parsed context dict is stored in `scan_reports.project_intake` alongside the scan results. This means:

- User runs CLI scan with `.forge/context.json` → context saved to DB
- User later opens web UI for the same repo → intake form is pre-filled from the CLI context
- Full loop: CLI → DB → web UI pre-fill

Implementation: in `forge_executor.py`, after scan completion, pass `project_context` to the scan report update call so it's persisted in the `project_intake` JSONB column.

### `.forge/` and `.gitignore`

`.forge/` should be **committed** to the repo (not gitignored). It's project configuration, like `.github/` or `.vscode/`. Team members benefit from shared context and suppression entries.

## 2. Editable Scan Preferences in Settings

### Location

New "Scan Preferences" section on the Settings page (`/settings`), positioned between GitHub Connection and API Key sections.

### Fields

| Field | Input Type | Options |
|---|---|---|
| Technical Level | Radio group | Engineer / Vibe Coder / Founder |
| Explanation Style | Select | Just Steps / Explain Why / Deep Dive |
| Shipping Posture | Select | Move Fast / Balanced / Careful |
| Coding Tool | Select + optional text input | Claude Code / Cursor / Lovable / Codex / Replit / Other (with text field) |

`acquisition_source` is NOT editable — it's analytics-only, set once during onboarding.

### Behavior

- Pre-filled from current profile values (fetched via existing `/api/user/me`)
- Explicit save button at bottom of section (not auto-save)
- Saves via new `PATCH /api/user/me` endpoint
- Success toast: "Preferences saved. Your next scan will use these settings."
- No page reload needed

### Visual Treatment

Same card style as existing settings sections (GitHub Connection, API Key, OpenRouter Key).
- Title: "Scan Preferences"
- Subtitle: "These influence how FORGE explains findings and filters noise."

### Backend: `PATCH /api/user/me`

New endpoint that accepts a partial dict of profile fields.

**Whitelisted fields:** `technical_level`, `explanation_style`, `shipping_posture`, `coding_tool`, `coding_tool_other`

Any field not in the whitelist is silently ignored (not an error — allows forward compatibility).

**Validation:** Same constraints as onboarding (enum values for technical_level/explanation_style/shipping_posture, string for coding_tool).

**Response:** Returns the full updated profile (same shape as `GET /api/user/me`).

## 3. Skip Intake Form on Rescan

### Current Flow (all scans)

```
Step 1: Repo URL + branch  →  Step 2: Intake form  →  Step 3: Review & Submit
```

### New Flow — First Scan of a Repo

```
Step 1: Repo URL + branch  →  Step 2: Intake form  →  Step 3: Review & Submit
```

Unchanged. Full intake form shown.

### New Flow — Rescan of Known Repo

```
Step 1: Repo URL + branch  →  Step 2: Review & Submit
                                  └── "Edit project context" (collapsed link)
```

Step 2 (intake form) is skipped entirely. The Review step includes a collapsed "Edit project context" link that expands the pre-filled intake form if clicked.

### "Known Repo" Detection

After the user enters a repo URL in Step 1:

1. Check if a project exists in the DB for that URL (use data already loaded from `/api/user/projects` on the dashboard, or fetch via `/api/user/projects?repo_url=...`)
2. Check if the most recent scan for that project has a non-empty `project_intake`
3. If both true → skip to Review step with collapsed edit link
4. If either false → show full intake form (Step 2)

### Collapsed "Edit project context" Section

- Default state: collapsed, shows text link only: "Edit project context ›"
- Click expands the full intake form pre-filled from the last scan's `project_intake`
- If user edits fields, the updated values are sent with the scan request
- If user doesn't expand, the previous intake is sent automatically (no user action needed)

### No New API Endpoints

The intake data is already stored in `scan_reports.project_intake` and the frontend already fetches project/scan data. The logic is purely frontend:

1. Check project existence → conditionally skip Step 2
2. Pass previous intake to the scan request → backend already handles this

## Implementation Order

```
Feature 2 (.forge/ folder)  →  Feature 1 (settings prefs)  →  Feature 3 (skip intake)
```

Rationale:
- `.forge/` folder is foundational — CLI changes, forge-engine changes, forgeignore resolution
- Settings prefs is backend + frontend, independent of `.forge/`
- Skip intake depends on context being stored in DB (which `.forge/` CLI persistence enables)

### Repos Touched

| Feature | vibe2prod (backend) | vibe2prod (frontend) | forge-engine |
|---|---|---|---|
| `.forge/` folder | `forge_executor.py` (persist context to DB) | — | `cli.py` (auto-create folder, read context.json), `phases.py` (forgeignore resolution) |
| Editable prefs | `user.py` (new PATCH endpoint) | `settings/page.tsx` (new section) | — |
| Skip intake | — | `scan/new/page.tsx` (conditional step skip, collapsed edit) | — |

## Out of Scope

- Moving existing root `.forgeignore` files to `.forge/.forgeignore` automatically (user does this manually if they want)
- Web UI writing to repos (no repo write access from web)
- Syncing DB intake back to `.forge/context.json` (one-directional: file → DB only)
- Changing the onboarding flow itself (just making prefs editable after)
