"""Audit routes.

`POST /api/audit` triggers a FORGE discovery scan via AgentField.
The discovery report is stored in scan_reports.report_data JSONB.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from api.middleware.rate_limit import limiter, rate_limit_string
from api.routes._sse import event_buses
from models.agent_log import AgentLogEntry, AgentName, LogLevel, SSEEventType
from models.scan import AuditRequest, AuditResponse, ScanStatus
from api.routes.webhook_forge import register_scan_token, unregister_scan_token
from config import settings
from services import supabase_client as db
from services.github import get_repo_info, parse_repo_url

logger = logging.getLogger(__name__)
router = APIRouter()

_LIMIT_STATUS = 403


def _limit_exception(code: str, message: str, extra: dict | None = None) -> HTTPException:
    payload = {"code": code, "message": message}
    if extra:
        payload.update(extra)
    return HTTPException(status_code=_LIMIT_STATUS, detail=payload)


async def _run_forge_audit(
    scan_id: UUID,
    repo_url: str,
    project_context: dict | None = None,
    github_token: str | None = None,
) -> None:
    """Background task that runs FORGE discovery scan and stores results."""
    from services.forge_bridge import trigger_forge_scan

    bus = event_buses.get(scan_id)

    def emit(entry: AgentLogEntry) -> None:
        if bus is not None:
            bus.append(entry)

    # Generate per-scan webhook token and URL
    webhook_token = secrets.token_urlsafe(32)
    webhook_url = (
        f"{settings.forge_webhook_base_url}/api/webhook/forge"
        if settings.forge_webhook_base_url
        else ""
    )
    if webhook_url:
        register_scan_token(scan_id, webhook_token)

    try:
        await db.update_scan_status(scan_id, ScanStatus.scanning)

        emit(
            AgentLogEntry(
                event_type=SSEEventType.agent_start,
                agent=AgentName.orchestrator,
                message="Starting FORGE discovery scan.",
                level=LogLevel.info,
            )
        )

        result = await trigger_forge_scan(
            repo_url,
            scan_id=scan_id,
            github_token=github_token,
            project_context=project_context,
            emit=emit,
            webhook_url=webhook_url,
            webhook_token=webhook_token,
        )

        if result.success and result.discovery_report:
            await db.update_scan_with_discovery(
                scan_id=scan_id,
                discovery_report=result.discovery_report,
            )

            total = result.discovery_report.get("total_findings", 0)
            emit(
                AgentLogEntry(
                    event_type=SSEEventType.scan_complete,
                    agent=AgentName.orchestrator,
                    message=f"FORGE discovery complete. {total} findings.",
                    level=LogLevel.success,
                    data={
                        "findings_count": total,
                        "report_artifact_available": True,
                    },
                )
            )
        else:
            error_msg = result.error or "FORGE discovery scan failed."
            logger.error("FORGE audit failed for scan %s: %s", scan_id, error_msg)
            emit(
                AgentLogEntry(
                    event_type=SSEEventType.scan_error,
                    agent=AgentName.orchestrator,
                    message=error_msg,
                    level=LogLevel.error,
                )
            )
            await db.update_scan_status(scan_id, ScanStatus.failed)
    except Exception as exc:
        logger.exception("FORGE audit background task failed for scan %s", scan_id)
        emit(
            AgentLogEntry(
                event_type=SSEEventType.scan_error,
                agent=AgentName.orchestrator,
                message=f"FORGE discovery scan failed: {type(exc).__name__}",
                level=LogLevel.error,
            )
        )
        try:
            await db.update_scan_status(scan_id, ScanStatus.failed)
        except Exception:
            logger.exception("Failed to update scan status after error for scan %s", scan_id)
    finally:
        # Give SSE clients a grace period to read the terminal event,
        # then clean up the event bus to prevent unbounded memory growth.
        await asyncio.sleep(30)
        event_buses.pop(scan_id, None)
        unregister_scan_token(scan_id)
        logger.debug("Cleaned up event bus for scan %s", scan_id)


async def _preflight(
    request_body: AuditRequest,
    user_id: str,
    github_token: str | None,
) -> dict:
    """Validate onboarding, project limits, and resolve repo metadata."""
    if not await db.is_onboarding_complete(user_id):
        raise _limit_exception(
            "onboarding_required",
            "Organization onboarding is required before starting scans.",
        )

    existing_project = await db.get_project_by_repo_url(user_id, str(request_body.repo_url))

    owner, repo = await parse_repo_url(str(request_body.repo_url))
    repo_info = await get_repo_info(owner, repo, github_token)

    return {
        "existing_project": existing_project,
        "repo_name": repo_info.full_name,
    }


@router.post("/audit", response_model=AuditResponse)
@limiter.limit(rate_limit_string())
async def start_audit(
    request_body: AuditRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> AuditResponse:
    """Accept a GitHub URL and kick off a FORGE discovery scan."""
    user_id: str = request.state.user_id
    scan_id = uuid4()

    event_buses[scan_id] = []

    try:
        github_token = await db.get_github_access_token(user_id)
        preflight = await _preflight(request_body, user_id, github_token)

        project_id = (
            UUID(preflight["existing_project"]["id"])
            if preflight["existing_project"]
            else await db.get_or_create_project(
                user_id=user_id,
                repo_url=str(request_body.repo_url),
                repo_name=preflight["repo_name"],
                vibe_prompt=request_body.vibe_prompt,
                project_charter=request_body.project_charter,
                latest_scan_tier="forge",
            )
        )

        await db.create_scan_report(
            scan_id=scan_id,
            project_id=project_id,
            user_id=user_id,
            scan_tier="forge",
            project_intake=request_body.project_intake.model_dump(mode="json"),
            primer_summary=(request_body.primer.summary if request_body.primer else None),
            audit_confidence=(request_body.primer.confidence if request_body.primer else None),
        )

        project_context = request_body.project_intake.model_dump(mode="json")
        background_tasks.add_task(
            _run_forge_audit,
            scan_id,
            str(request_body.repo_url),
            project_context,
            github_token,
        )

        return AuditResponse(
            scan_id=scan_id,
            tier="forge",
        )
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("Validation error in start_audit: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.TimeoutException:
        logger.warning("Timeout during start_audit preflight")
        raise HTTPException(status_code=504, detail="Upstream request timed out")
    except httpx.HTTPError as exc:
        logger.warning("HTTP error during start_audit preflight: %s", exc)
        raise HTTPException(status_code=502, detail="Upstream service error")
    except Exception:
        logger.exception("Failed to create scan report row")
        raise HTTPException(status_code=500, detail="Failed to create scan")


