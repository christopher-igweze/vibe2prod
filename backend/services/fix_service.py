"""Fix service — FORGE remediation orchestration.

This service handles the business logic for triggering and managing
automated security fixes via the FORGE engine.
"""

from __future__ import annotations

import logging
from uuid import UUID

from services import supabase_client as db

try:
    from services.forge_bridge import trigger_forge_remediate
except ImportError:
    trigger_forge_remediate = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


async def run_forge_fix(
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


async def run_scan_forge_fix(
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
