"""Orchestrate scan creation: validate, create project, create scan record, trigger FORGE.

This use case encapsulates the business logic currently spread across
the audit route handler. Route files should NOT be modified to use this
yet — it exists as the target architecture for future refactoring.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from models.scan import AuditRequest, ScanStatus
from services.repositories.onboarding_repository import is_onboarding_complete
from services.repositories.project_repository import (
    get_or_create_project,
    get_project_by_repo_url,
)
from services.repositories.scan_repository import (
    create_scan_report,
    update_scan_status,
    update_scan_with_discovery,
)
from services.repositories.oauth_repository import get_github_access_token
from services.repositories.user_repository import get_user_role
from services.repositories.credits_repository import get_user_balance, deduct_balance
from services.github import get_repo_info, parse_repo_url

logger = logging.getLogger(__name__)


class CreateScanUseCase:
    """Orchestrates the full scan creation lifecycle.

    Steps:
    1. Validate user onboarding status
    2. Check role and balance
    3. Resolve repo metadata via GitHub API
    4. Get or create the project record
    5. Create a scan_reports row
    6. Trigger FORGE discovery (caller handles background task)
    """

    async def preflight(
        self,
        request_body: AuditRequest,
        user_id: str,
    ) -> dict:
        """Validate preconditions and resolve repo metadata.

        Returns a dict with 'existing_project', 'repo_name', 'github_token',
        'role' for downstream use.

        Raises ValueError for validation failures.
        """
        if not await is_onboarding_complete(user_id):
            raise ValueError("onboarding_required")

        role = get_user_role(user_id)
        if role == "user":
            raise ValueError("waitlist_required")

        if role != "developer" and get_user_balance(user_id) <= 0:
            raise ValueError("no_balance")

        github_token = await get_github_access_token(user_id)
        existing_project = await get_project_by_repo_url(
            user_id, str(request_body.repo_url)
        )

        owner, repo = await parse_repo_url(str(request_body.repo_url))
        repo_info = await get_repo_info(owner, repo, github_token)

        return {
            "existing_project": existing_project,
            "repo_name": repo_info.full_name,
            "github_token": github_token,
            "role": role,
        }

    async def create(
        self,
        request_body: AuditRequest,
        user_id: str,
        preflight_result: dict,
    ) -> UUID:
        """Create project (if needed) and scan record. Returns scan_id."""
        scan_id = uuid4()

        project_id = (
            UUID(preflight_result["existing_project"]["id"])
            if preflight_result["existing_project"]
            else await get_or_create_project(
                user_id=user_id,
                repo_url=str(request_body.repo_url),
                repo_name=preflight_result["repo_name"],
                vibe_prompt=request_body.vibe_prompt,
                project_charter=request_body.project_charter,
                latest_scan_tier="forge",
            )
        )

        await create_scan_report(
            scan_id=scan_id,
            project_id=project_id,
            user_id=user_id,
            scan_tier="forge",
            project_intake=request_body.project_intake.model_dump(mode="json"),
            primer_summary=(
                request_body.primer.summary if request_body.primer else None
            ),
            audit_confidence=(
                request_body.primer.confidence if request_body.primer else None
            ),
        )

        return scan_id

    async def run_forge_audit(
        self,
        scan_id: UUID,
        repo_url: str,
        project_context: dict | None = None,
        github_token: str | None = None,
        user_id: str | None = None,
        role: str | None = None,
    ) -> None:
        """Execute FORGE discovery and store results. Meant for background tasks."""
        from services.forge_bridge import trigger_forge_scan

        try:
            await update_scan_status(scan_id, ScanStatus.scanning)

            result = await trigger_forge_scan(
                repo_url,
                scan_id=scan_id,
                github_token=github_token,
                project_context=project_context,
            )

            if result.success:
                await update_scan_with_discovery(
                    scan_id=scan_id,
                    discovery_report=result.discovery_report,
                    evaluation=result.evaluation or None,
                    aivss_score=result.aivss_score or None,
                )
                if user_id and role != "developer":
                    try:
                        from models.credits import compute_scan_charge

                        charge = compute_scan_charge(result.cost_usd)
                        deduct_balance(
                            user_id,
                            charge["charged_amount"],
                            scan_id=str(scan_id),
                            description=(
                                f"Scan: LLM ${charge['llm_cost']:.2f} + "
                                f"Infra ${charge['infra_cost']:.2f} = "
                                f"${charge['total_raw']:.2f} x {charge['markup']}x"
                            ),
                        )
                    except ValueError:
                        logger.warning(
                            "Insufficient balance for user %s (scan %s)",
                            user_id,
                            scan_id,
                        )
            else:
                error_msg = result.error or "FORGE discovery scan failed."
                logger.error("FORGE audit failed for scan %s: %s", scan_id, error_msg)
                await update_scan_status(
                    scan_id, ScanStatus.failed, failure_reason=error_msg
                )
        except Exception as exc:
            logger.exception("FORGE audit failed for scan %s", scan_id)
            try:
                await update_scan_status(
                    scan_id,
                    ScanStatus.failed,
                    failure_reason=f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                logger.exception("Failed to update scan status for scan %s", scan_id)


create_scan_use_case = CreateScanUseCase()
