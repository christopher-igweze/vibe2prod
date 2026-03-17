"""Project CRUD operations."""

from __future__ import annotations

import asyncio
from uuid import UUID

from services.repositories._base import _client


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


async def list_user_projects(
    user_id: str, *, limit: int = 50, offset: int = 0,
) -> list[dict]:
    """Return projects for a user, with latest scan info."""
    client = _client()
    row = (
        client.table("projects")
        .select("id,repo_url,repo_name,scan_count,latest_health_score,latest_scan_tier,created_at,updated_at")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return row.data or []


async def count_user_projects(user_id: str) -> int:
    """Return the total number of projects for a user."""
    client = _client()
    row = (
        client.table("projects")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    return row.count or 0


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
    """Fetch project and its scan history concurrently."""
    project_task = get_project(project_id)
    scans_task = get_project_scan_history(project_id, user_id, limit)

    project, scans = await asyncio.gather(project_task, scans_task)

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
    """Fetch multiple projects by IDs in a single query."""
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
