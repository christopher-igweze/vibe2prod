"""User-facing API routes: profile info, scan history."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

from api.middleware.rate_limit import limiter, rate_limit_string
from services import supabase_client as db

router = APIRouter()


@router.get("/user/me")
@limiter.limit(rate_limit_string())
async def get_me(request: Request) -> dict:
    """Return the authenticated user's profile (role, onboarding status)."""
    user_id: str = request.state.user_id
    profile = db.get_user_profile(user_id)
    if not profile:
        return {
            "user_id": user_id,
            "role": "user",
            "onboarding_complete": False,
            "lifetime_scans_used": 0,
            "lifetime_scan_cap": 5,
            "scan_credits": 1,
            "balance_usd": 0.0,
        }
    return profile


@router.get("/user/scans")
@limiter.limit(rate_limit_string())
async def list_scans(request: Request) -> list[dict]:
    """Return the authenticated user's recent scans."""
    user_id: str = request.state.user_id
    scans = await db.list_user_scans(user_id)

    # Batch fetch all projects to avoid N+1 queries
    project_ids = [UUID(s["project_id"]) for s in scans if s.get("project_id")]
    project_cache: dict[UUID, dict] = {}
    if project_ids:
        project_cache = await db.get_projects_batch(project_ids)

    # Enrich with repo_url from projects
    for scan in scans:
        pid = scan.get("project_id")
        if pid:
            project = project_cache.get(UUID(pid), {})
            scan["repo_url"] = project.get("repo_url", "")
            scan["repo_name"] = project.get("repo_name", "")

    return scans


@router.get("/user/scans/{scan_id}")
@limiter.limit(rate_limit_string())
async def get_scan_detail(scan_id: UUID, request: Request) -> dict:
    """Return full scan report data for a completed scan."""
    user_id: str = request.state.user_id
    scan = await db.get_scan_report(scan_id, user_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Enrich with project info
    pid = scan.get("project_id")
    if pid:
        project = await db.get_project(UUID(pid))
        if project:
            scan["repo_url"] = project.get("repo_url", "")
            scan["repo_name"] = project.get("repo_name", "")

    return scan


@router.delete("/user/scans/{scan_id}", status_code=204)
@limiter.limit(rate_limit_string())
async def delete_scan(scan_id: UUID, request: Request) -> Response:
    """Delete a scan report and all associated data."""
    user_id: str = request.state.user_id
    deleted = await db.delete_scan_report(scan_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scan not found")
    return Response(status_code=204)


@router.post("/user/tour/complete")
@limiter.limit(rate_limit_string())
async def complete_tour(request: Request) -> dict:
    """Mark the guided tour as completed for the authenticated user."""
    user_id: str = request.state.user_id
    await db.mark_tour_completed(user_id)
    return {"ok": True}


@router.post("/user/tour/reset")
@limiter.limit(rate_limit_string())
async def reset_tour(request: Request) -> dict:
    """Reset the guided tour so the user can retake it."""
    user_id: str = request.state.user_id
    await db.reset_tour(user_id)
    return {"ok": True}


@router.get("/user/projects")
@limiter.limit(rate_limit_string())
async def list_projects(request: Request) -> list[dict]:
    """Return all projects for the authenticated user."""
    user_id: str = request.state.user_id
    try:
        return await db.list_user_projects(user_id)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error listing projects for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")


@router.get("/user/projects/{project_id}/scans")
@limiter.limit(rate_limit_string())
async def get_project_scans(project_id: UUID, request: Request) -> dict:
    """Return scan history and score trends for a project."""
    user_id: str = request.state.user_id
    try:
        project = await db.get_project(project_id)
        if not project or project.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Project not found")
        scans = await db.get_project_scan_history(project_id, user_id)
        return {"project": project, "scans": scans}
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching scans for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project scans")


@router.get("/user/projects/{project_id}/intake")
@limiter.limit(rate_limit_string())
async def get_project_intake(project_id: UUID, request: Request) -> dict:
    """Return latest project_intake for pre-filling the scan wizard."""
    user_id: str = request.state.user_id
    try:
        project = await db.get_project(project_id)
        if not project or project.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Project not found")
        intake = await db.get_latest_project_intake(project_id, user_id)
        return {"project_intake": intake}
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching intake for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve project intake")
