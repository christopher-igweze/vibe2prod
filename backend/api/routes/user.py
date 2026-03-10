"""User-facing API routes: profile info, scan history."""

from __future__ import annotations

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

    # Enrich with repo_url from projects
    project_cache: dict[str, dict] = {}
    for scan in scans:
        pid = scan.get("project_id")
        if pid and pid not in project_cache:
            project = await db.get_project(UUID(pid))
            project_cache[pid] = project or {}
        project = project_cache.get(pid, {})
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


@router.get("/user/projects")
@limiter.limit(rate_limit_string())
async def list_projects(request: Request) -> list[dict]:
    """Return all projects for the authenticated user."""
    user_id: str = request.state.user_id
    return await db.list_user_projects(user_id)


@router.get("/user/projects/{project_id}/scans")
@limiter.limit(rate_limit_string())
async def get_project_scans(project_id: UUID, request: Request) -> dict:
    """Return scan history and score trends for a project."""
    user_id: str = request.state.user_id
    project = await db.get_project(project_id)
    if not project or project.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    scans = await db.get_project_scan_history(project_id, user_id)
    return {"project": project, "scans": scans}


@router.get("/user/projects/{project_id}/intake")
@limiter.limit(rate_limit_string())
async def get_project_intake(project_id: UUID, request: Request) -> dict:
    """Return latest project_intake for pre-filling the scan wizard."""
    user_id: str = request.state.user_id
    project = await db.get_project(project_id)
    if not project or project.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    intake = await db.get_latest_project_intake(project_id, user_id)
    return {"project_intake": intake}
