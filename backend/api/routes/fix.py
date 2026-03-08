"""POST /api/fix — Trigger FORGE remediation for an action item (PAID feature).

When FORGE is enabled, this route:
1. Looks up the action item and its parent scan/project
2. Creates a fix_attempt row in pending state
3. Kicks off FORGE remediation as a background task
4. Returns immediately with the fix_attempt_id

The background task:
1. Marks the fix_attempt as running
2. Calls trigger_forge_remediate() with the repo_url and scan findings
3. Stores FORGE results back in fix_attempt row
4. Updates action_item.fix_status based on success/failure
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from config import settings
from models.scan import FixRequest, FixResponse, ScanFixResponse, ScanFixStatusResponse
from api.middleware.rate_limit import limiter, rate_limit_string
from services import supabase_client as db

try:
    from services.forge_bridge import trigger_forge_remediate
except ImportError:
    trigger_forge_remediate = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_forge_fix(
    fix_attempt_id: UUID,
    action_item_id: UUID,
    repo_url: str,
    scan_findings: list[dict] | None,
    github_token: str | None = None,
) -> None:
    """Background task that runs FORGE remediation and stores results."""
    try:
        await db.update_fix_attempt(fix_attempt_id, status="running")
        await db.update_action_item_fix_status(action_item_id, "in_progress")

        result = await trigger_forge_remediate(
            repo_url=repo_url,
            scan_findings=scan_findings,
            github_token=github_token,
        )

        if result.success:
            await db.update_fix_attempt(
                fix_attempt_id,
                status="success",
                pr_url=result.pr_url or None,
                agent_logs={
                    "forge_run_id": result.forge_run_id,
                    "execution_id": result.execution_id,
                    "summary": result.summary,
                    "total_findings": result.total_findings,
                    "findings_fixed": result.findings_fixed,
                    "findings_deferred": result.findings_deferred,
                    "readiness_score": result.readiness_score,
                    "readiness_report": result.readiness_report,
                    "agent_invocations": result.agent_invocations,
                    "cost_usd": result.cost_usd,
                    "duration_seconds": result.duration_seconds,
                },
            )
            await db.update_action_item_fix_status(action_item_id, "fixed")
        else:
            await db.update_fix_attempt(
                fix_attempt_id,
                status="failed",
                agent_logs={
                    "forge_run_id": result.forge_run_id,
                    "execution_id": result.execution_id,
                    "error": result.error,
                    "status": result.status,
                    "summary": result.summary,
                    "total_findings": result.total_findings,
                    "findings_fixed": result.findings_fixed,
                    "findings_deferred": result.findings_deferred,
                },
            )
            await db.update_action_item_fix_status(action_item_id, "open")

    except Exception:
        logger.exception(
            "FORGE fix background task failed for fix_attempt %s", fix_attempt_id
        )
        try:
            await db.update_fix_attempt(fix_attempt_id, status="failed")
            await db.update_action_item_fix_status(action_item_id, "open")
        except Exception:
            logger.exception(
                "Failed to update DB after fix failure for fix_attempt %s",
                fix_attempt_id,
            )


@router.post("/fix", response_model=FixResponse)
@limiter.limit(rate_limit_string())
async def trigger_fix(
    request_body: FixRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> FixResponse:
    """Accept an action_item_id and kick off FORGE remediation.

    Requires FORGE to be enabled via FORGE_ENABLED=true in config.
    """
    user_id: str = request.state.user_id

    if not settings.forge_enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "forge_disabled",
                "message": "Auto-fix is not currently available. FORGE engine is disabled.",
            },
        )

    # Fix is gated to developers only (beta = coming soon for all)
    role = db.get_user_role(user_id)
    if role != "developer":
        raise HTTPException(
            status_code=403,
            detail={"code": "fix_coming_soon", "message": "Fix with FORGE is coming soon. Stay tuned."},
        )

    action_item = await db.get_action_item(request_body.action_item_id, user_id)
    if not action_item:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "action_item_not_found",
                "message": "Action item not found or does not belong to this user.",
            },
        )

    if action_item.get("fix_status") == "in_progress":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "fix_already_in_progress",
                "message": "A fix is already in progress for this action item.",
            },
        )

    project_id = UUID(action_item["project_id"])
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "project_not_found",
                "message": "Parent project not found.",
            },
        )

    if project.get("user_id") != user_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "forbidden",
                "message": "You do not have access to this project.",
            },
        )

    repo_url = project["repo_url"]
    github_token = await db.get_github_access_token(user_id)

    # Pull discovery findings from the scan report to enrich FORGE context
    scan_report_id = UUID(action_item["scan_report_id"])
    scan_report = await db.get_scan_report(scan_report_id, user_id)
    scan_findings = None
    if scan_report and isinstance(scan_report.get("report_data"), dict):
        scan_findings = scan_report["report_data"].get("findings")

    fix_attempt_id = await db.create_fix_attempt(
        action_item_id=request_body.action_item_id,
        project_id=project_id,
        user_id=user_id,
    )

    background_tasks.add_task(
        _run_forge_fix,
        fix_attempt_id,
        request_body.action_item_id,
        repo_url,
        scan_findings,
        github_token,
    )

    return FixResponse(
        fix_attempt_id=fix_attempt_id,
        status="pending",
        message="FORGE remediation queued. The fix is being processed.",
    )


# ------------------------------------------------------------------ #
# Scan-level remediation
# ------------------------------------------------------------------ #


async def _run_scan_forge_fix(
    fix_attempt_id: UUID,
    scan_id: UUID,
    repo_url: str,
    scan_findings: list[dict] | None,
    github_token: str | None = None,
) -> None:
    """Background task that runs FORGE remediation for an entire scan."""
    try:
        await db.update_fix_attempt(fix_attempt_id, status="running")

        result = await trigger_forge_remediate(
            repo_url=repo_url,
            scan_findings=scan_findings,
            github_token=github_token,
        )

        if result.success:
            await db.update_fix_attempt(
                fix_attempt_id,
                status="success",
                pr_url=result.pr_url or None,
                agent_logs={
                    "forge_run_id": result.forge_run_id,
                    "execution_id": result.execution_id,
                    "summary": result.summary,
                    "total_findings": result.total_findings,
                    "findings_fixed": result.findings_fixed,
                    "findings_deferred": result.findings_deferred,
                    "readiness_score": result.readiness_score,
                    "readiness_report": result.readiness_report,
                    "agent_invocations": result.agent_invocations,
                    "cost_usd": result.cost_usd,
                    "duration_seconds": result.duration_seconds,
                },
            )
        else:
            await db.update_fix_attempt(
                fix_attempt_id,
                status="failed",
                agent_logs={
                    "forge_run_id": result.forge_run_id,
                    "execution_id": result.execution_id,
                    "error": result.error,
                    "status": result.status,
                    "summary": result.summary,
                    "total_findings": result.total_findings,
                    "findings_fixed": result.findings_fixed,
                    "findings_deferred": result.findings_deferred,
                },
            )

    except Exception:
        logger.exception(
            "FORGE scan-level fix failed for fix_attempt %s", fix_attempt_id
        )
        try:
            await db.update_fix_attempt(fix_attempt_id, status="failed")
        except Exception:
            logger.exception(
                "Failed to update DB after scan fix failure for fix_attempt %s",
                fix_attempt_id,
            )


@router.post("/fix-scan/{scan_id}", response_model=ScanFixResponse)
@limiter.limit(rate_limit_string())
async def trigger_scan_fix(
    scan_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ScanFixResponse:
    """Trigger FORGE remediation for an entire scan.

    Looks up the scan, verifies ownership and status, checks for active
    fix attempts, then kicks off FORGE remediation as a background task.
    """
    user_id: str = request.state.user_id

    if not settings.forge_enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "forge_disabled",
                "message": "Auto-fix is not currently available. FORGE engine is disabled.",
            },
        )

    # Fix is gated to developers only (beta = coming soon for all)
    role = db.get_user_role(user_id)
    if role != "developer":
        raise HTTPException(
            status_code=403,
            detail={"code": "fix_coming_soon", "message": "Fix with FORGE is coming soon. Stay tuned."},
        )

    scan = await db.get_scan_report(scan_id, user_id)
    if not scan:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "scan_not_found",
                "message": "Scan not found or does not belong to this user.",
            },
        )

    if scan.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "scan_not_completed",
                "message": "Scan must be completed before remediation can start.",
            },
        )

    active = await db.get_active_scan_fix_attempt(scan_id)
    if active:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "fix_already_in_progress",
                "message": "A fix is already in progress for this scan.",
            },
        )

    project_id = UUID(scan["project_id"])
    project = await db.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "project_not_found",
                "message": "Parent project not found.",
            },
        )

    repo_url = project["repo_url"]
    github_token = await db.get_github_access_token(user_id)

    # Extract findings from scan report data
    scan_findings = None
    report_data = scan.get("report_data")
    if isinstance(report_data, dict):
        # Try top-level findings first, then nested discovery_report
        scan_findings = report_data.get("findings")
        if scan_findings is None:
            dr = report_data.get("discovery_report")
            if isinstance(dr, dict):
                scan_findings = dr.get("findings")

    fix_attempt_id = await db.create_scan_fix_attempt(
        scan_id=scan_id,
        project_id=project_id,
        user_id=user_id,
    )

    background_tasks.add_task(
        _run_scan_forge_fix,
        fix_attempt_id,
        scan_id,
        repo_url,
        scan_findings,
        github_token,
    )

    return ScanFixResponse(
        fix_attempt_id=fix_attempt_id,
        status="pending",
        message="Remediation started",
    )


@router.get("/fix-scan/{scan_id}/status", response_model=ScanFixStatusResponse)
@limiter.limit(rate_limit_string())
async def get_scan_fix_status(
    scan_id: UUID,
    request: Request,
) -> ScanFixStatusResponse:
    """Poll the status of the latest fix attempt for a scan."""
    user_id: str = request.state.user_id

    # Verify the scan belongs to the user
    scan = await db.get_scan_report(scan_id, user_id)
    if not scan:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "scan_not_found",
                "message": "Scan not found or does not belong to this user.",
            },
        )

    attempt = await db.get_latest_scan_fix_attempt(scan_id)
    if not attempt:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "no_fix_attempt",
                "message": "No fix attempt found for this scan.",
            },
        )

    # Extract details from agent_logs if available
    logs = attempt.get("agent_logs") or {}

    # Prefer FORGE-reported duration, fall back to timestamp diff
    duration_seconds = logs.get("duration_seconds")
    if duration_seconds is None:
        started_at = attempt.get("started_at")
        completed_at = attempt.get("completed_at")
        if started_at and completed_at:
            from datetime import datetime, timezone

            try:
                t_start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                t_end = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                duration_seconds = (t_end - t_start).total_seconds()
            except (ValueError, TypeError):
                pass

    return ScanFixStatusResponse(
        fix_attempt_id=UUID(attempt["id"]),
        scan_id=scan_id,
        status=attempt["status"],
        findings_fixed=logs.get("findings_fixed"),
        findings_deferred=logs.get("findings_deferred"),
        readiness_score=logs.get("readiness_score"),
        pr_url=attempt.get("pr_url"),
        summary=logs.get("summary"),
        cost_usd=logs.get("cost_usd"),
        duration_seconds=duration_seconds,
        readiness_report=logs.get("readiness_report"),
        agent_invocations=logs.get("agent_invocations"),
        error=logs.get("error"),
    )
