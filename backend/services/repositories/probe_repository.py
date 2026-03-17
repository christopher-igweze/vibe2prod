"""Probe CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone

from services.repositories._base import _client


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
