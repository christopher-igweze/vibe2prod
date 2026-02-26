"""POST /api/fix — Trigger FORGE remediation for an action item (PAID feature).

When FORGE is enabled, this route:
1. Looks up the action item and its parent scan/project
2. Creates a fix_attempt row in pending state
3. Kicks off FORGE remediation as a background task
4. Returns immediately with the fix_attempt_id

The background task:
1. Marks the fix_attempt as running
2. Calls trigger_forge_remediate() with the repo_url and tier1 findings
3. Stores FORGE results back in fix_attempt row
4. Updates action_item.fix_status based on success/failure
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from config import settings
from models.scan import FixRequest, FixResponse
from api.middleware.rate_limit import limiter, rate_limit_string
from services import supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_forge_fix(
    fix_attempt_id: UUID,
    action_item_id: UUID,
    repo_url: str,
    tier1_findings: list[dict] | None,
) -> None:
    """Background task that runs FORGE remediation and stores results."""
    from services.forge_bridge import trigger_forge_remediate

    try:
        await db.update_fix_attempt(fix_attempt_id, status="running")
        await db.update_action_item_fix_status(action_item_id, "in_progress")

        result = await trigger_forge_remediate(
            repo_url=repo_url,
            tier1_findings=tier1_findings,
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
                },
            )
            await db.update_action_item_fix_status(action_item_id, "open")

    except Exception:
        logger.exception(
            "FORGE fix background task failed for fix_attempt %s", fix_attempt_id
        )
        await db.update_fix_attempt(fix_attempt_id, status="failed")
        await db.update_action_item_fix_status(action_item_id, "open")


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

    repo_url = project["repo_url"]

    # Pull tier1 findings from the scan report to enrich FORGE context
    scan_report_id = UUID(action_item["scan_report_id"])
    scan_report = await db.get_scan_report(scan_report_id, user_id)
    tier1_findings = None
    if scan_report and isinstance(scan_report.get("report_data"), dict):
        tier1_findings = scan_report["report_data"].get("findings")

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
        tier1_findings,
    )

    return FixResponse(
        fix_attempt_id=fix_attempt_id,
        status="pending",
        message="FORGE remediation queued. The fix is being processed.",
    )
