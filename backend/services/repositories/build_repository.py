"""Fix attempt (build) persistence operations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from services.repositories._base import _client


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
    """Insert a fix_attempts row for a scan-level remediation and return its ID."""
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


async def get_active_scan_fix_attempt(scan_id: UUID, user_id: str) -> dict | None:
    """Return the active (pending/running) fix_attempt for a scan, if any.

    Filters by user_id to prevent IDOR — callers must not be able to
    query fix attempts belonging to another user's scan.
    """
    try:
        client = _client()
        row = (
            client.table("fix_attempts")
            .select("*")
            .eq("scan_report_id", str(scan_id))
            .eq("user_id", str(user_id))
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


async def get_latest_scan_fix_attempt(scan_id: UUID, user_id: str) -> dict | None:
    """Return the most recent fix_attempt for a scan.

    Filters by user_id to prevent IDOR — callers must not be able to
    query fix attempts belonging to another user's scan.
    """
    try:
        client = _client()
        row = (
            client.table("fix_attempts")
            .select("*")
            .eq("scan_report_id", str(scan_id))
            .eq("user_id", str(user_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not row.data:
            return None
        return row.data[0]
    except Exception:
        return None
