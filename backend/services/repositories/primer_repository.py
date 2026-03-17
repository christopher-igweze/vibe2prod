"""Project primer cache operations."""

from __future__ import annotations

from uuid import UUID

from services.repositories._base import _client


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
