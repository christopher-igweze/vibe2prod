"""Supabase client for persisting scan reports, findings, and action items."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from supabase import create_client, Client

from config import settings
from models.findings import (
    AuditReport,
    Finding,
    ActionItem,
    EducationCard,
)
from models.scan import ScanStatus


def _client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


# ------------------------------------------------------------------ #
# Projects
# ------------------------------------------------------------------ #


async def get_or_create_project(
    user_id: str,
    repo_url: str,
    repo_name: str | None = None,
    vibe_prompt: str | None = None,
    project_charter: dict | None = None,
    latest_scan_tier: str = "deep",
) -> UUID:
    """Return the project ID for *repo_url*, creating the row if needed."""
    client = _client()
    existing = (
        client.table("projects")
        .select("id")
        .eq("user_id", str(user_id))
        .eq("repo_url", repo_url)
        .limit(1)
        .execute()
    )
    if existing.data:
        return UUID(existing.data[0]["id"])

    row = (
        client.table("projects")
        .insert(
            {
                "user_id": str(user_id),
                "repo_url": repo_url,
                "repo_name": repo_name,
                "vibe_prompt": vibe_prompt,
                "project_charter": project_charter,
                "latest_scan_tier": latest_scan_tier,
                "scan_count": 0,
            }
        )
        .execute()
    )
    return UUID(row.data[0]["id"])


async def get_project_by_repo_url(user_id: str, repo_url: str) -> dict | None:
    """Fetch the user's project row for a repo URL, if it exists."""
    client = _client()
    row = (
        client.table("projects")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("repo_url", repo_url)
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


# ------------------------------------------------------------------ #
# Scan reports
# ------------------------------------------------------------------ #


async def create_scan_report(
    scan_id: UUID,
    project_id: UUID,
    user_id: str,
    scan_tier: str = "deep",
    project_intake: dict | None = None,
    primer_summary: str | None = None,
    audit_confidence: int | None = None,
) -> UUID:
    """Insert a new scan_reports row using the caller-supplied *scan_id*.

    The caller's ``scan_id`` becomes the row ``id`` so every downstream
    reference (update_scan_status, save_report, etc.) targets the same row.
    """
    client = _client()
    row = (
        client.table("scan_reports")
        .insert(
            {
                "id": str(scan_id),
                "project_id": str(project_id),
                "user_id": str(user_id),
                "scan_tier": scan_tier,
                "status": ScanStatus.pending.value,
                "project_intake": project_intake,
                "primer_summary": primer_summary,
                "audit_confidence": audit_confidence,
            }
        )
        .execute()
    )
    return UUID(row.data[0]["id"])


async def update_scan_status(
    scan_id: UUID,
    status: ScanStatus,
    *,
    failure_reason: str | None = None,
) -> None:
    update: dict = {"status": status.value}
    if failure_reason is not None:
        update["failure_reason"] = failure_reason
    client = _client()
    client.table("scan_reports").update(update).eq(
        "id", str(scan_id)
    ).execute()


async def fail_orphaned_scans() -> int:
    """Mark any scans stuck in 'pending' or 'scanning' as 'failed'.

    Called on app startup — if the server just booted, no background tasks
    can be running for these scans, so they're orphaned from a previous
    container lifecycle.

    Returns the number of scans marked as failed.
    """
    client = _client()
    result = (
        client.table("scan_reports")
        .update({"status": ScanStatus.failed.value})
        .in_("status", [ScanStatus.pending.value, ScanStatus.scanning.value])
        .execute()
    )
    return len(result.data) if result.data else 0


def _compute_scores_from_discovery(discovery_report: dict) -> dict[str, int]:
    """Derive health/security/reliability/scalability scores from findings.

    Starts each dimension at 100 and deducts based on finding severity.
    Maps FORGE categories → frontend score dimensions:
      security → security_score
      quality + architecture → health_score
      reliability → reliability_score
      performance → scalability_score
    """
    severity_weights = {"critical": 15, "high": 8, "medium": 4, "low": 1, "info": 0}
    category_map: dict[str, str] = {
        "security": "security_score",
        "quality": "health_score",
        "architecture": "health_score",
        "reliability": "reliability_score",
        "performance": "scalability_score",
    }

    deductions: dict[str, int] = {
        "health_score": 0,
        "security_score": 0,
        "reliability_score": 0,
        "scalability_score": 0,
    }

    for finding in discovery_report.get("findings", []):
        severity = finding.get("severity", "medium")
        category = finding.get("category", "quality")
        weight = severity_weights.get(severity, 4)
        score_key = category_map.get(category, "health_score")
        deductions[score_key] += weight

    return {k: max(0, 100 - v) for k, v in deductions.items()}


async def update_scan_with_discovery(
    scan_id: UUID,
    discovery_report: dict,
) -> None:
    """Store FORGE discovery report data and computed scores."""
    scores = _compute_scores_from_discovery(discovery_report)
    client = _client()
    client.table("scan_reports").update(
        {
            "status": ScanStatus.completed.value,
            "report_data": {"discovery_report": discovery_report},
            "completed_at": datetime.now(timezone.utc).isoformat(),
            **scores,
        }
    ).eq("id", str(scan_id)).execute()


async def save_report(
    scan_id: UUID,
    report: AuditReport,
    scan_tier: str = "deep",
    report_data_extra: dict | None = None,
) -> None:
    """Persist the final assembled report."""
    client = _client()
    report_data = report.model_dump(mode="json")
    if isinstance(report_data_extra, dict) and report_data_extra:
        report_data.update(report_data_extra)

    client.table("scan_reports").update(
        {
            "status": ScanStatus.completed.value,
            "health_score": report.health_score,
            "security_score": report.security_score,
            "reliability_score": report.reliability_score,
            "scalability_score": report.scalability_score,
            "audit_confidence": report.audit_confidence,
            "primer_summary": report.primer_summary,
            "evolution_report": report.evolution.model_dump(mode="json"),
            "report_data": report_data,
        }
    ).eq("id", str(scan_id)).execute()

    scan_row = (
        client.table("scan_reports")
        .select("project_id")
        .eq("id", str(scan_id))
        .limit(1)
        .execute()
    )
    if scan_row.data:
        project_id = scan_row.data[0]["project_id"]
        project_row = (
            client.table("projects")
            .select("scan_count")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        current_scan_count = 0
        if project_row.data:
            current_scan_count = int(project_row.data[0].get("scan_count") or 0)
        client.table("projects").update(
            {
                "latest_health_score": report.health_score,
                "latest_scan_tier": scan_tier,
                "scan_count": current_scan_count + 1,
            }
        ).eq("id", project_id).execute()


# ------------------------------------------------------------------ #
# Primer cache
# ------------------------------------------------------------------ #


async def get_project_primer(project_id: UUID, repo_sha: str) -> dict | None:
    client = _client()
    row = (
        client.table("project_primers")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("repo_sha", repo_sha)
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


async def save_project_primer(
    *,
    project_id: UUID,
    user_id: str,
    repo_sha: str,
    primer_json: dict,
    summary: str,
    confidence: int,
    failure_reason: str | None = None,
) -> None:
    client = _client()
    client.table("project_primers").upsert(
        {
            "project_id": str(project_id),
            "user_id": str(user_id),
            "repo_sha": repo_sha,
            "primer_json": primer_json,
            "summary": summary,
            "confidence": confidence,
            "failure_reason": failure_reason,
        },
        on_conflict="project_id,repo_sha",
    ).execute()


async def get_github_access_token(user_id: str) -> str | None:
    client = _client()
    row = (
        client.table("profiles")
        .select("github_access_token")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0].get("github_access_token")


async def save_github_connection(
    *,
    user_id: str,
    access_token: str,
    github_username: str | None = None,
    avatar_url: str | None = None,
) -> None:
    """Persist GitHub OAuth credentials and profile metadata for a user."""
    client = _client()
    client.table("profiles").update(
        {
            "github_access_token": access_token,
            "github_username": github_username,
            "avatar_url": avatar_url,
        }
    ).eq("user_id", str(user_id)).execute()


async def clear_github_connection(*, user_id: str) -> None:
    """Remove stored GitHub OAuth credentials for a user."""
    client = _client()
    client.table("profiles").update(
        {
            "github_access_token": None,
            "github_username": None,
        }
    ).eq("user_id", str(user_id)).execute()


async def upsert_profile_from_clerk(
    user_id: str,
    email: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
    github_username: str | None = None,
) -> None:
    """Upsert a user profile from Clerk webhook data."""
    client = _client()
    data: dict = {
        "user_id": user_id,
        "email": email,
        "display_name": display_name,
        "avatar_url": avatar_url,
    }
    if github_username:
        data["github_username"] = github_username

    existing = (
        client.table("profiles")
        .select("user_id")
        .eq("user_id", user_id)
        .execute()
    )

    if existing.data:
        # Update existing profile (don't overwrite fields with None)
        update_data = {k: v for k, v in data.items() if v is not None and k != "user_id"}
        if update_data:
            client.table("profiles").update(update_data).eq("user_id", user_id).execute()
    else:
        # Insert new profile
        client.table("profiles").insert(data).execute()


async def save_org_onboarding(*, user_id: str, payload: dict) -> None:
    client = _client()
    client.table("profiles").update(
        {
            "technical_level": payload.get("technical_level"),
            "explanation_style": payload.get("explanation_style"),
            "shipping_posture": payload.get("shipping_posture"),
            "tool_tags": payload.get("tool_tags") or [],
            "acquisition_source": payload.get("acquisition_source"),
            "acquisition_other": payload.get("acquisition_other"),
            "coding_agent_provider": payload.get("coding_agent_provider"),
            "coding_agent_model": payload.get("coding_agent_model"),
            "onboarding_complete": True,
        }
    ).eq("user_id", str(user_id)).execute()


async def is_onboarding_complete(user_id: str) -> bool:
    client = _client()
    row = (
        client.table("profiles")
        .select("onboarding_complete")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return False
    return bool(row.data[0].get("onboarding_complete"))


async def get_user_onboarding_preferences(user_id: str) -> dict | None:
    """Return stored onboarding preferences for report personalization."""
    client = _client()
    row = (
        client.table("profiles")
        .select(
            "technical_level,explanation_style,shipping_posture,tool_tags,acquisition_source,acquisition_other,coding_agent_provider,coding_agent_model,onboarding_complete"
        )
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


# ------------------------------------------------------------------ #
# Findings (raw scanner output → action_items table)
# ------------------------------------------------------------------ #


async def save_findings(
    scan_id: UUID, project_id: UUID, user_id: str, findings: list[Finding]
) -> None:
    """Bulk-insert action_items rows from Scanner findings."""
    if not findings:
        return
    client = _client()
    rows = [
        {
            "scan_report_id": str(scan_id),
            "project_id": str(project_id),
            "user_id": str(user_id),
            "title": f.title,
            "description": f.description,
            "category": f.category.value,
            "severity": f.severity.value,
            "source": f.source.value,
            "file_path": f.file_path,
            "line_number": f.line_number,
        }
        for f in findings
    ]
    client.table("action_items").insert(rows).execute()


# ------------------------------------------------------------------ #
# Action items (Planner output)
# ------------------------------------------------------------------ #


async def save_action_items(
    scan_id: UUID, project_id: UUID, user_id: str, items: list[ActionItem]
) -> None:
    """Persist prioritised action items from the Planner.

    Each row uses the ActionItem's model ``id`` so that save_education
    can target a specific row later.
    """
    if not items:
        return
    client = _client()
    rows = [
        {
            "id": str(item.id),
            "scan_report_id": str(scan_id),
            "project_id": str(project_id),
            "user_id": str(user_id),
            "title": item.title,
            "description": item.description,
            "category": item.category.value,
            "severity": item.severity.value,
            "file_path": item.file_path,
            "line_number": item.line_number,
        }
        for item in items
    ]
    client.table("action_items").insert(rows).execute()


# ------------------------------------------------------------------ #
# Education cards (Educator output → update existing action_items)
# ------------------------------------------------------------------ #


async def save_education(
    scan_id: UUID,
    project_id: UUID,
    user_id: str,
    cards: list[EducationCard],
) -> None:
    """Attach education text to specific action_items rows."""
    if not cards:
        return
    client = _client()
    for card in cards:
        client.table("action_items").update(
            {
                "why_it_matters": card.why_it_matters,
                "cto_perspective": card.cto_perspective,
            }
        ).eq("id", str(card.action_item_id)).execute()


# ------------------------------------------------------------------ #
# Action item lookups (for /api/fix route)
# ------------------------------------------------------------------ #


async def get_action_item(action_item_id: UUID, user_id: str) -> dict | None:
    """Fetch a single action item by ID, scoped to the requesting user."""
    client = _client()
    row = (
        client.table("action_items")
        .select("*")
        .eq("id", str(action_item_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


async def update_action_item_fix_status(
    action_item_id: UUID, fix_status: str
) -> None:
    """Update the fix_status on an action item (open/in_progress/fixed/wont_fix)."""
    client = _client()
    client.table("action_items").update(
        {"fix_status": fix_status}
    ).eq("id", str(action_item_id)).execute()


# ------------------------------------------------------------------ #
# Fix attempts (FORGE integration)
# ------------------------------------------------------------------ #


async def create_fix_attempt(
    *,
    action_item_id: UUID,
    project_id: UUID,
    user_id: str,
) -> UUID:
    """Insert a new fix_attempts row and return its ID."""
    client = _client()
    row = (
        client.table("fix_attempts")
        .insert(
            {
                "action_item_id": str(action_item_id),
                "project_id": str(project_id),
                "user_id": str(user_id),
                "status": "pending",
            }
        )
        .execute()
    )
    return UUID(row.data[0]["id"])


async def update_fix_attempt(
    fix_attempt_id: UUID,
    *,
    status: str,
    pr_url: str | None = None,
    agent_logs: dict | None = None,
) -> None:
    """Update a fix_attempt row with FORGE results."""
    client = _client()
    update_data: dict = {"status": status}
    if pr_url is not None:
        update_data["pr_url"] = pr_url
    if agent_logs is not None:
        update_data["agent_logs"] = agent_logs
    if status == "running":
        update_data["started_at"] = datetime.now(timezone.utc).isoformat()
    if status in ("success", "failed"):
        update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

    client.table("fix_attempts").update(update_data).eq(
        "id", str(fix_attempt_id)
    ).execute()


async def create_scan_fix_attempt(
    *,
    scan_id: UUID,
    project_id: UUID,
    user_id: str,
) -> UUID:
    """Insert a fix_attempts row for a scan-level remediation and return its ID.

    NOTE: Requires ``scan_report_id`` column in fix_attempts table.
    A migration is needed before this function will work.
    """
    client = _client()
    row = (
        client.table("fix_attempts")
        .insert(
            {
                "scan_report_id": str(scan_id),
                "project_id": str(project_id),
                "user_id": str(user_id),
                "status": "pending",
            }
        )
        .execute()
    )
    return UUID(row.data[0]["id"])


async def get_active_scan_fix_attempt(scan_id: UUID) -> dict | None:
    """Return the active (pending/running) fix_attempt for a scan, if any.

    Returns None if the scan_report_id column hasn't been migrated yet.
    """
    try:
        client = _client()
        row = (
            client.table("fix_attempts")
            .select("*")
            .eq("scan_report_id", str(scan_id))
            .in_("status", ["pending", "running"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not row.data:
            return None
        return row.data[0]
    except Exception:
        return None


async def get_latest_scan_fix_attempt(scan_id: UUID) -> dict | None:
    """Return the most recent fix_attempt for a scan.

    Returns None if the scan_report_id column hasn't been migrated yet.
    """
    try:
        client = _client()
        row = (
            client.table("fix_attempts")
            .select("*")
            .eq("scan_report_id", str(scan_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not row.data:
            return None
        return row.data[0]
    except Exception:
        return None


async def list_user_scans(user_id: str, limit: int = 20) -> list[dict]:
    """Return recent scans for a user, newest first."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select("id,status,scan_tier,health_score,security_score,reliability_score,scalability_score,created_at,project_id")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return row.data or []


async def get_scan_report(scan_id: UUID, user_id: str) -> dict | None:
    """Fetch a scan report row by ID, scoped to the requesting user."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select("*")
        .eq("id", str(scan_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


async def delete_scan_report(scan_id: UUID, user_id: str) -> bool:
    """Delete a scan report scoped to the requesting user.

    CASCADE foreign keys handle child rows (action_items, fix_attempts, etc.).
    Returns True if a row was deleted, False if not found.
    """
    client = _client()
    result = (
        client.table("scan_reports")
        .delete()
        .eq("id", str(scan_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    return bool(result.data)


async def get_project(project_id: UUID) -> dict | None:
    """Fetch a project row by ID."""
    client = _client()
    row = (
        client.table("projects")
        .select("*")
        .eq("id", str(project_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]
