"""CLI scan report ingestion — creates real scan_report rows from CLI scans.

Authenticated via X-API-Key header (v2p_ prefixed key).
Creates project + scan_report so CLI scans appear in the dashboard
alongside cloud scans, grouped by repo.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services import supabase_client as db

router = APIRouter()
logger = logging.getLogger(__name__)


class CLIScanReport(BaseModel):
    """Payload from the FORGE MCP server after a scan."""

    repo_url: str = ""  # git remote URL or file:// path
    repo_name: str = ""  # directory basename
    discovery_report: dict = {}  # full FORGE discovery report
    cost_usd: float = 0
    duration_seconds: float = 0
    model: str = ""
    version: str = ""


async def _authenticate_api_key(request: Request) -> str:
    """Resolve X-API-Key to user_id or raise 401."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    user_id = await db.lookup_user_by_api_key(key_hash)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user_id


@router.post("/cli/scan-report")
async def ingest_cli_scan(payload: CLIScanReport, request: Request):
    """Store a CLI scan as a real scan_report linked to a project.

    This makes CLI scans visible in the dashboard alongside cloud scans.
    """
    user_id = await _authenticate_api_key(request)
    scan_id = uuid4()

    try:
        # Use git remote URL if available, otherwise use repo_name as identifier
        repo_url = payload.repo_url or f"local://{payload.repo_name}"
        repo_name = payload.repo_name or repo_url.rstrip("/").rsplit("/", 1)[-1]

        # Get or create project for this repo
        project_id = await db.get_or_create_project(
            user_id=user_id,
            repo_url=repo_url,
            repo_name=repo_name,
            latest_scan_tier="forge_cli",
        )

        # Create the scan report row
        await db.create_scan_report(
            scan_id=scan_id,
            project_id=project_id,
            user_id=user_id,
            scan_tier="forge_cli",
        )

        # Store the discovery report (same path as cloud scans)
        if payload.discovery_report:
            await db.update_scan_with_discovery(
                scan_id=scan_id,
                discovery_report=payload.discovery_report,
            )
        else:
            await db.update_scan_status(scan_id, "completed")

        return {
            "ok": True,
            "scan_id": str(scan_id),
            "project_id": str(project_id),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to store CLI scan report")
        raise HTTPException(status_code=500, detail="Failed to store scan report")
