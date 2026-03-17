"""Supabase client for persisting scan reports, findings, and action items."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography.exceptions import InvalidTag
from supabase import create_client, Client

from config import settings

logger = logging.getLogger(__name__)
from models.findings import (
    AuditReport,
    Finding,
    ActionItem,
    EducationCard,
)
from models.scan import ScanStatus
from services.token_encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)


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


async def list_user_projects(user_id: str, limit: int = 50) -> list[dict]:
    """Return all projects for a user, with latest scan info."""
    client = _client()
    row = (
        client.table("projects")
        .select("id,repo_url,repo_name,scan_count,latest_health_score,latest_scan_tier,created_at,updated_at")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return row.data or []


async def get_project_scan_history(
    project_id: UUID, user_id: str, limit: int = 50
) -> list[dict]:
    """Return scan reports for a project, newest first, with scores."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select("id,status,scan_tier,health_score,security_score,reliability_score,scalability_score,created_at,completed_at")
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return row.data or []


async def get_project_with_scans(
    project_id: UUID, user_id: str, limit: int = 50
) -> tuple[dict | None, list[dict]]:
    """Fetch project and its scan history concurrently.

    Returns a tuple of (project, scans) to reduce sequential DB calls.
    The project is None if not found or belongs to another user.
    """
    project_task = get_project(project_id)
    scans_task = get_project_scan_history(project_id, user_id, limit)

    project, scans = await asyncio.gather(project_task, scans_task)

    # Verify ownership
    if project and project.get("user_id") != user_id:
        return None, []

    return project, scans


async def get_latest_project_intake(
    project_id: UUID, user_id: str
) -> dict | None:
    """Return project_intake from the most recent scan for intake pre-fill."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select("project_intake")
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .not_.is_("project_intake", "null")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0].get("project_intake")


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
    client = _client()
    update: dict = {"status": status.value}
    if failure_reason is not None:
        update["failure_reason"] = failure_reason
    try:
        client.table("scan_reports").update(update).eq(
            "id", str(scan_id)
        ).execute()
    except Exception:
        if failure_reason is not None:
            # Column may not exist yet — retry without failure_reason
            client.table("scan_reports").update(
                {"status": status.value}
            ).eq("id", str(scan_id)).execute()
        else:
            raise


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


async def check_database_health() -> bool:
    """Verify database connectivity by executing a simple query.

    Returns True if database is reachable and responsive, False otherwise.
    This is used for health checks and startup verification.
    """
    try:
        client = _client()
        # Execute a simple query to verify connectivity
        result = client.table("projects").select("id").limit(1).execute()
        return True
    except Exception:
        return False


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


def get_user_role(user_id: str) -> str:
    """Return the user's role. Defaults to 'user' (waitlist) if profile missing."""
    client = _client()
    row = (
        client.table("profiles")
        .select("role")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return "user"
    return row.data[0].get("role", "user")


def get_user_profile(user_id: str) -> dict | None:
    """Return the user's profile including role and onboarding status."""
    client = _client()
    row = (
        client.table("profiles")
        .select("user_id,email,display_name,avatar_url,role,onboarding_complete,tour_completed,lifetime_scans_used,lifetime_scan_cap,scan_credits,balance_usd")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


async def upgrade_user_role(user_id: str, new_role: str) -> bool:
    """Upgrade a user's role. Returns True if profile was updated."""
    client = _client()
    existing = (
        client.table("profiles")
        .select("role")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not existing.data:
        return False
    client.table("profiles").update({"role": new_role}).eq("user_id", str(user_id)).execute()
    return True


async def get_github_access_token(user_id: str) -> str | None:
    """Retrieve and decrypt the stored GitHub OAuth access token for *user_id*.

    Returns the plaintext token, or *None* if the user has not connected
    GitHub.  If the stored value cannot be decrypted (e.g. tampered ciphertext
    or a key mismatch) a warning is logged and *None* is returned so the caller
    treats the credential as absent rather than exposing raw ciphertext.
    """
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
    raw = row.data[0].get("github_access_token")
    if not raw:
        return None
    try:
        return decrypt_token(raw, settings.github_token_encryption_key)
    except (InvalidTag, ValueError) as exc:
        logger.warning(
            "Failed to decrypt GitHub access token for user %s: %s. "
            "The stored credential may be corrupted or was encrypted with a "
            "different key.  Treating as disconnected.",
            user_id,
            exc,
        )
        return None


async def get_github_profile(user_id: str) -> tuple[str | None, str | None]:
    """Retrieve GitHub username and avatar URL from the user's profile."""
    client = _client()
    row = (
        client.table("profiles")
        .select("github_username, avatar_url")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None, None
    return row.data[0].get("github_username"), row.data[0].get("avatar_url")


async def save_github_connection(
    *,
    user_id: str,
    access_token: str,
    github_username: str | None = None,
    avatar_url: str | None = None,
) -> None:
    """Persist GitHub OAuth credentials and profile metadata for a user.

    The *access_token* is encrypted with AES-256-GCM using the key from
    ``settings.github_token_encryption_key`` before being written to the
    database.  The plaintext token never touches the storage layer.
    """
    encrypted = encrypt_token(access_token, settings.github_token_encryption_key)
    client = _client()
    client.table("profiles").update(
        {
            "github_access_token": encrypted,
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


# ------------------------------------------------------------------ #
# OAuth state nonce consumption (replay-attack prevention, CWE-613)
# ------------------------------------------------------------------ #


async def is_oauth_state_consumed(jti: str) -> bool:
    """Return True if the OAuth state nonce *jti* has already been consumed.

    Each ``jti`` is stored in the ``oauth_state_nonces`` table the first time
    :func:`consume_oauth_state` is called.  Subsequent calls for the same
    ``jti`` therefore return ``True``, preventing replay attacks within the
    JWT's TTL window.

    Required table (run once as a migration)::

        CREATE TABLE IF NOT EXISTS oauth_state_nonces (
            jti        TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at  TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_oauth_state_nonces_expires_at
            ON oauth_state_nonces (expires_at);

    Raises:
        HTTPException: If the database is unavailable or query fails,
            with 503 status code to indicate a temporary service issue.
    """
    client = _client()
    try:
        row = (
            client.table("oauth_state_nonces")
            .select("jti")
            .eq("jti", jti)
            .limit(1)
            .execute()
        )
        return bool(row.data)
    except Exception as exc:
        # Log the error and raise a service-unavailable exception.
        # We intentionally do NOT fail-open (return False) here because
        # that would allow replay attacks if the DB is under load.
        # Instead, we fail-secure by blocking the OAuth flow when the
        # database is unreachable.
        logger.error("Failed to check OAuth state consumption for jti %s: %s", jti, exc)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "code": "oauth_state_check_failed",
                "message": "Unable to verify OAuth state. Please try again later.",
            },
        ) from exc


async def consume_oauth_state(
    *,
    jti: str,
    user_id: str,
    ttl_minutes: int,
) -> None:
    """Mark an OAuth state nonce as consumed so it cannot be replayed.

    Inserts a row into ``oauth_state_nonces`` keyed by *jti*.  If the row
    already exists (race condition between two near-simultaneous requests
    carrying the same state token) the insert is silently ignored — the
    *first* writer wins and the second request will be rejected by
    :func:`is_oauth_state_consumed`.

    Args:
        jti: The JWT ID claim from the state token.
        user_id: The user who owns this state token (for audit purposes).
        ttl_minutes: How long until the record is eligible for cleanup;
            mirrors the JWT expiry so no token can be replayed after it
            would have expired anyway.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl_minutes)
    client = _client()
    try:
        client.table("oauth_state_nonces").insert(
            {
                "jti": jti,
                "user_id": str(user_id),
                "consumed_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        ).execute()
    except Exception as exc:
        # Only swallow unique-key violations (race condition where another
        # request already consumed this nonce). Re-raise all other errors
        # to prevent masking database connectivity or schema issues.
        error_code = getattr(exc, "code", None)
        error_message = str(exc).lower()
        is_unique_violation = (
            error_code == "23505"  # PostgreSQL unique_violation
            or "duplicate" in error_message
            or "unique constraint" in error_message
            or "already exists" in error_message
        )
        if is_unique_violation:
            logger.warning("OAuth state nonce %s already consumed (race condition suppressed).", jti)
        else:
            # Re-raise non-unique-violation exceptions to fail fast on
            # real database errors (connectivity, permissions, schema, etc.)
            raise


async def purge_expired_oauth_states() -> int:
    """Delete expired nonce rows and return the count removed.

    Intended to be called from a periodic maintenance task or cron job so
    that the ``oauth_state_nonces`` table does not grow unbounded.
    """
    now = datetime.now(timezone.utc)
    client = _client()
    result = (
        client.table("oauth_state_nonces")
        .delete()
        .lt("expires_at", now.isoformat())
        .execute()
    )
    count = len(result.data) if result.data else 0
    logger.info("Purged %d expired OAuth state nonce(s).", count)
    return count


async def mark_tour_completed(user_id: str) -> None:
    """Mark the guided tour as completed."""
    client = _client()
    client.table("profiles").update({
        "tour_completed": True,
        "tour_completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", str(user_id)).execute()


async def reset_tour(user_id: str) -> None:
    """Reset tour so user can retake it."""
    client = _client()
    client.table("profiles").update({
        "tour_completed": False,
        "tour_completed_at": None,
    }).eq("user_id", str(user_id)).execute()


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
        # Insert new profile with default role and required defaults
        data["role"] = settings.default_user_role
        data.setdefault("coding_agent_provider", "anthropic")
        data.setdefault("coding_agent_model", "claude-sonnet-4")
        data.setdefault("coding_tool", "claude_code")
        client.table("profiles").insert(data).execute()


async def save_org_onboarding(*, user_id: str, payload: dict) -> None:
    client = _client()
    client.table("profiles").update(
        {
            "technical_level": payload.get("technical_level"),
            "explanation_style": payload.get("explanation_style"),
            "shipping_posture": payload.get("shipping_posture"),
            "tool_tags": payload.get("tool_tags") or [],
            "coding_tool": payload.get("coding_tool"),
            "coding_tool_other": payload.get("coding_tool_other"),
            "acquisition_source": payload.get("acquisition_source"),
            "acquisition_other": payload.get("acquisition_other"),
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
            "technical_level,explanation_style,shipping_posture,tool_tags,coding_tool,coding_tool_other,acquisition_source,acquisition_other,onboarding_complete"
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
    """Return recent scans for a user, newest first.
    
    Only returns scans for projects that the user owns. This ensures
    authorization boundaries are enforced at the database level.
    """
    client = _client()
    # Join with projects table to verify project ownership
    # This prevents returning scans for projects the user doesn't own
    row = (
        client.table("scan_reports")
        .select(
            "id,status,scan_tier,health_score,security_score,reliability_score,scalability_score,created_at,project_id,"
            "projects(id,user_id)"
        )
        .eq("user_id", str(user_id))
        .eq("projects.user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    
    # Extract scan fields from the joined result
    scans = []
    for item in (row.data or []):
        scan = {
            "id": item.get("id"),
            "status": item.get("status"),
            "scan_tier": item.get("scan_tier"),
            "health_score": item.get("health_score"),
            "security_score": item.get("security_score"),
            "reliability_score": item.get("reliability_score"),
            "scalability_score": item.get("scalability_score"),
            "created_at": item.get("created_at"),
            "project_id": item.get("project_id"),
        }
        scans.append(scan)
    
    return scans


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


async def get_projects_batch(project_ids: list[UUID]) -> dict[UUID, dict]:
    """Fetch multiple projects by IDs in a single query.

    Returns a dict mapping project_id to project dict (or empty dict if not found).
    """
    if not project_ids:
        return {}

    client = _client()
    str_ids = [str(pid) for pid in project_ids]
    rows = (
        client.table("projects")
        .select("*")
        .in_("id", str_ids)
        .execute()
    )

    result: dict[UUID, dict] = {}
    for row in rows.data:
        pid = UUID(row["id"])
        result[pid] = row
    return result


# ------------------------------------------------------------------ #
# Credits
# ------------------------------------------------------------------ #


def get_user_balance(user_id: str) -> float:
    """Return the user's current USD wallet balance."""
    client = _client()
    row = (
        client.table("profiles")
        .select("balance_usd")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return 0.0
    return float(row.data[0].get("balance_usd", 0))


def deduct_balance(
    user_id: str,
    amount: float,
    scan_id: str | None = None,
    description: str | None = None,
) -> float:
    """Deduct a USD amount from the user's wallet and log a usage transaction.

    Raises ValueError if the user has insufficient balance.
    Returns the new balance.
    """
    client = _client()
    current = get_user_balance(user_id)
    if current < amount:
        raise ValueError(f"Insufficient balance: ${current:.2f} < ${amount:.2f}")

    new_balance = round(current - amount, 4)
    client.table("profiles").update(
        {"balance_usd": new_balance}
    ).eq("user_id", str(user_id)).execute()

    tx: dict = {
        "user_id": str(user_id),
        "amount": round(-amount, 4),
        "balance_after": new_balance,
        "type": "usage",
    }
    if scan_id:
        tx["scan_id"] = scan_id
    if description:
        tx["description"] = description
    client.table("credit_transactions").insert(tx).execute()

    return new_balance


def add_balance(
    user_id: str,
    amount_usd: float,
    stripe_session_id: str | None = None,
    description: str | None = None,
) -> float:
    """Add USD to a user's wallet balance and log a purchase transaction.

    Returns the new balance.
    """
    client = _client()
    current = get_user_balance(user_id)
    new_balance = round(current + amount_usd, 4)

    client.table("profiles").update(
        {"balance_usd": new_balance}
    ).eq("user_id", str(user_id)).execute()

    tx: dict = {
        "user_id": str(user_id),
        "amount": round(amount_usd, 4),
        "balance_after": new_balance,
        "type": "purchase",
    }
    if stripe_session_id:
        tx["stripe_session_id"] = stripe_session_id
    if description:
        tx["description"] = description
    client.table("credit_transactions").insert(tx).execute()

    return new_balance


def get_credit_transactions(user_id: str, limit: int = 20) -> list[dict]:
    """Return recent credit transactions for a user, newest first."""
    client = _client()
    row = (
        client.table("credit_transactions")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return row.data or []


# ------------------------------------------------------------------ #
# Probes
# ------------------------------------------------------------------ #


async def create_probe(probe_data: dict) -> dict:
    """Insert a new probe row and return the created record."""
    client = _client()
    row = client.table("probes").insert(probe_data).execute()
    return row.data[0]


async def update_probe_status(
    probe_id: str,
    status: str,
    *,
    started_at: str | None = None,
    completed_at: str | None = None,
    duration_seconds: float | None = None,
) -> None:
    """Update probe status and optional timing fields."""
    client = _client()
    update: dict = {"status": status}
    if started_at is not None:
        update["started_at"] = started_at
    if completed_at is not None:
        update["completed_at"] = completed_at
    if duration_seconds is not None:
        update["duration_seconds"] = duration_seconds
    client.table("probes").update(update).eq("id", probe_id).execute()


async def update_probe_results(
    probe_id: str,
    *,
    total_findings: int,
    critical_count: int,
    high_count: int,
    medium_count: int,
    low_count: int,
    probe_score: int,
    report_data: dict | None = None,
) -> None:
    """Store probe results (counts, score, report data)."""
    client = _client()
    update: dict = {
        "total_findings": total_findings,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "probe_score": probe_score,
    }
    if report_data is not None:
        update["report_data"] = report_data
    client.table("probes").update(update).eq("id", probe_id).execute()


async def save_probe_findings(
    probe_id: str, user_id: str, findings: list[dict]
) -> None:
    """Bulk-insert probe finding rows."""
    if not findings:
        return
    client = _client()
    rows = [{**f, "probe_id": probe_id, "user_id": user_id} for f in findings]
    client.table("probe_findings").insert(rows).execute()


async def get_probe(probe_id: str, user_id: str | None = None) -> dict | None:
    """Fetch a probe by ID. If user_id is given, scope to that user."""
    client = _client()
    q = client.table("probes").select("*").eq("id", probe_id)
    if user_id:
        q = q.eq("user_id", user_id)
    row = q.limit(1).execute()
    if not row.data:
        return None
    return row.data[0]


async def get_probe_findings(probe_id: str, user_id: str) -> list[dict]:
    """Return all findings for a probe, scoped to user."""
    client = _client()
    row = (
        client.table("probe_findings")
        .select("*")
        .eq("probe_id", probe_id)
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return row.data or []


async def list_user_probes(user_id: str, limit: int = 20) -> list[dict]:
    """Return recent probes for a user, newest first."""
    client = _client()
    row = (
        client.table("probes")
        .select("id,target_url,status,probe_type,probe_score,total_findings,critical_count,high_count,medium_count,low_count,created_at,completed_at,duration_seconds,project_id")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return row.data or []


async def save_authorized_target(
    user_id: str, domain: str, auth_method: str, expires_at: str
) -> None:
    """Upsert an authorized target record for domain probing."""
    client = _client()
    client.table("authorized_targets").upsert(
        {
            "user_id": user_id,
            "domain": domain,
            "auth_method": auth_method,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
        },
        on_conflict="user_id,domain",
    ).execute()


async def get_authorized_target(user_id: str, domain: str) -> dict | None:
    """Fetch an authorized target record for a user + domain."""
    client = _client()
    row = (
        client.table("authorized_targets")
        .select("*")
        .eq("user_id", user_id)
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


# ------------------------------------------------------------------ #
# Telemetry
# ------------------------------------------------------------------ #


async def store_telemetry_event(data: dict) -> None:
    """Insert an anonymous telemetry event."""
    client = _client()
    client.table("telemetry_events").insert(data).execute()


async def store_shared_findings(data: dict) -> None:
    """Insert opt-in anonymized findings."""
    client = _client()
    client.table("telemetry_events").insert(
        {"event": "findings_shared", **data}
    ).execute()


# ------------------------------------------------------------------ #
# API Key management
# ------------------------------------------------------------------ #


async def update_profile_api_key(user_id: str, key_hash: str) -> None:
    """Store the hashed API key in the user's profile."""
    client = _client()
    client.table("profiles").update(
        {"api_key_hash": key_hash}
    ).eq("user_id", user_id).execute()


async def revoke_profile_api_key(user_id: str) -> None:
    """Remove the API key hash from the user's profile."""
    client = _client()
    client.table("profiles").update(
        {"api_key_hash": None}
    ).eq("user_id", user_id).execute()


async def has_api_key(user_id: str) -> bool:
    """Check if a user has an active API key."""
    client = _client()
    result = (
        client.table("profiles")
        .select("api_key_hash")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0].get("api_key_hash") is not None
    return False


async def lookup_user_by_api_key(key_hash: str) -> str | None:
    """Find a user_id by API key hash. Returns None if not found."""
    client = _client()
    result = (
        client.table("profiles")
        .select("user_id")
        .eq("api_key_hash", key_hash)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["user_id"]
    return None
