"""User-facing API routes: profile info, scan history, API key management."""

from __future__ import annotations

import hashlib
import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import Response

from api.middleware.rate_limit import limiter, rate_limit_string
from constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT, PROJECTS_DEFAULT_LIMIT
from services import supabase_client as db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/user/me")
@limiter.limit(rate_limit_string())
async def get_me(request: Request) -> dict:
    """Return the authenticated user's profile (role, onboarding status)."""
    user_id: str = request.state.user_id
    try:
        profile = db.get_user_profile(user_id)
    except Exception as e:
        logger.exception("Failed to retrieve user profile for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve user profile")
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
async def list_scans(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(
        PAGINATION_DEFAULT_LIMIT,
        ge=1,
        le=PAGINATION_MAX_LIMIT,
        description="Items per page",
    ),
) -> dict:
    """Return the authenticated user's scans with pagination."""
    user_id: str = request.state.user_id
    offset = (page - 1) * limit
    try:
        scans = await db.list_user_scans(user_id, limit=limit, offset=offset)
        total = await db.count_user_scans(user_id)
    except Exception:
        logger.exception("Failed to retrieve scans for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve scans")

    # Batch fetch all projects to avoid N+1 queries
    project_ids = [UUID(s["project_id"]) for s in scans if s.get("project_id")]
    project_cache: dict[UUID, dict] = {}
    if project_ids:
        try:
            project_cache = await db.get_projects_batch(project_ids)
        except Exception:
            logger.exception(
                "Failed to batch-fetch projects for user %s; returning scans without enrichment",
                user_id,
            )

    # Defense-in-depth: explicitly filter out any scans for projects
    # the user doesn't own (protects against edge cases)
    authorized_scans = []
    for scan in scans:
        pid = scan.get("project_id")
        if pid:
            project = project_cache.get(UUID(pid), {})
            if project.get("user_id") != user_id:
                continue
            scan["repo_url"] = project.get("repo_url", "")
            scan["repo_name"] = project.get("repo_name", "")
        authorized_scans.append(scan)

    return {
        "items": authorized_scans,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/user/scans/{scan_id}")
@limiter.limit(rate_limit_string())
async def get_scan_detail(scan_id: UUID, request: Request) -> dict:
    """Return full scan report data for a completed scan."""
    user_id: str = request.state.user_id
    try:
        scan = await db.get_scan_report(scan_id, user_id)
    except Exception as e:
        logger.exception("Failed to retrieve scan %s", scan_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve scan")
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Enrich with project info and verify ownership
    pid = scan.get("project_id")
    if pid:
        try:
            project = await db.get_project(UUID(pid))
        except Exception:
            logger.exception("Failed to fetch project for scan %s; returning scan without enrichment", scan_id)
            project = {}
        if project:
            # Defense-in-depth: verify the authenticated user owns the project
            if project.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            scan["repo_url"] = project.get("repo_url", "")
            scan["repo_name"] = project.get("repo_name", "")

    return scan


@router.delete("/user/scans/{scan_id}", status_code=204)
@limiter.limit(rate_limit_string())
async def delete_scan(scan_id: UUID, request: Request) -> Response:
    """Delete a scan report and all associated data."""
    user_id: str = request.state.user_id
    try:
        deleted = await db.delete_scan_report(scan_id, user_id)
    except Exception as e:
        logger.exception("Failed to delete scan %s for user %s", scan_id, user_id)
        raise HTTPException(status_code=500, detail="Failed to delete scan")
    if not deleted:
        raise HTTPException(status_code=404, detail="Scan not found")
    return Response(status_code=204)


@router.post("/user/tour/complete")
@limiter.limit(rate_limit_string())
async def complete_tour(request: Request) -> dict:
    """Mark the guided tour as completed for the authenticated user."""
    user_id: str = request.state.user_id
    try:
        await db.mark_tour_completed(user_id)
    except Exception as e:
        logger.exception("Failed to complete tour for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to complete tour")
    return {"ok": True}


@router.post("/user/tour/reset")
@limiter.limit(rate_limit_string())
async def reset_tour(request: Request) -> dict:
    """Reset the guided tour so the user can retake it."""
    user_id: str = request.state.user_id
    try:
        await db.reset_tour(user_id)
    except Exception as e:
        logger.exception("Failed to reset tour for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to reset tour")
    return {"ok": True}


@router.get("/user/projects")
@limiter.limit(rate_limit_string())
async def list_projects(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(
        PROJECTS_DEFAULT_LIMIT,
        ge=1,
        le=PAGINATION_MAX_LIMIT,
        description="Items per page",
    ),
) -> dict:
    """Return projects for the authenticated user with pagination."""
    user_id: str = request.state.user_id
    offset = (page - 1) * limit
    try:
        projects = await db.list_user_projects(user_id, limit=limit, offset=offset)
        total = await db.count_user_projects(user_id)
    except Exception:
        logger.exception("Failed to retrieve projects for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve projects")
    return {
        "items": projects,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0,
    }


@router.get("/user/projects/{project_id}/scans")
@limiter.limit(rate_limit_string())
async def get_project_scans(project_id: UUID, request: Request) -> dict:
    """Return scan history and score trends for a project."""
    user_id: str = request.state.user_id
    try:
        project, scans = await db.get_project_with_scans(project_id, user_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"project": project, "scans": scans}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to retrieve scans for project %s", project_id)
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
        logger.exception("Failed to retrieve project intake for project %s", project_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve project intake")


# ------------------------------------------------------------------ #
# API Key management
# ------------------------------------------------------------------ #


@router.get("/user/api-key")
@limiter.limit(rate_limit_string())
async def get_api_key_status(request: Request) -> dict:
    """Check whether the user has an active API key."""
    user_id: str = request.state.user_id
    try:
        has_key = await db.has_api_key(user_id)
    except Exception:
        logger.exception("Failed to check API key status for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to check API key status")
    return {"has_key": has_key}


@router.post("/user/api-key")
@limiter.limit(rate_limit_string())
async def generate_api_key(request: Request) -> dict:
    """Generate a v2p_ prefixed API key. Shown once — user must save it."""
    user_id: str = request.state.user_id
    raw_key = f"v2p_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    try:
        await db.update_profile_api_key(user_id, key_hash)
    except Exception as e:
        logger.exception("Failed to generate API key for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to generate API key")
    return {"api_key": raw_key, "message": "Save this key — it won't be shown again."}


@router.delete("/user/api-key", status_code=204)
@limiter.limit(rate_limit_string())
async def revoke_api_key(request: Request) -> Response:
    """Revoke the user's API key."""
    user_id: str = request.state.user_id
    try:
        await db.revoke_profile_api_key(user_id)
    except Exception as e:
        logger.exception("Failed to revoke API key for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to revoke API key")
    return Response(status_code=204)
