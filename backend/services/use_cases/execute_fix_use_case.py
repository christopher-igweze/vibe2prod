"""Orchestrate fix execution: validate action item, create fix attempt, trigger FORGE.

This use case encapsulates the business logic currently in the fix route.
Route files should NOT be modified to use this yet — it exists as the
target architecture for future refactoring.
"""

from __future__ import annotations

import logging
from uuid import UUID

from services.repositories.findings_repository import get_action_item
from services.repositories.project_repository import get_project
from services.repositories.scan_repository import get_scan_report
from services.repositories.build_repository import (
    create_fix_attempt,
    create_scan_fix_attempt,
    get_active_scan_fix_attempt,
)
from services.repositories.oauth_repository import get_github_access_token
from services.repositories.user_repository import get_user_role

logger = logging.getLogger(__name__)


class ExecuteFixUseCase:
    """Orchestrates fix attempt lifecycle.

    Steps:
    1. Validate FORGE is enabled
    2. Validate user role and permissions
    3. Look up action item / scan and verify ownership
    4. Check for in-progress fixes (prevent duplicates)
    5. Create fix_attempt record
    6. Return context needed to run FORGE in a background task
    """

    async def validate_item_fix(
        self,
        action_item_id: UUID,
        user_id: str,
    ) -> dict:
        """Validate and prepare context for an action-item-level fix.

        Returns dict with action_item, project, repo_url, github_token,
        scan_findings, fix_attempt_id.

        Raises ValueError for validation failures.
        """
        role = get_user_role(user_id)
        if role != "developer":
            raise ValueError("fix_coming_soon")

        action_item = await get_action_item(action_item_id, user_id)
        if not action_item:
            raise ValueError("action_item_not_found")

        if action_item.get("fix_status") == "in_progress":
            raise ValueError("fix_already_in_progress")

        project_id = UUID(action_item["project_id"])
        project = await get_project(project_id)
        if not project:
            raise ValueError("project_not_found")

        if project.get("user_id") != user_id:
            raise ValueError("forbidden")

        repo_url = project["repo_url"]
        github_token = await get_github_access_token(user_id)

        scan_report_id = UUID(action_item["scan_report_id"])
        scan_report = await get_scan_report(scan_report_id, user_id)
        scan_findings = None
        if scan_report and isinstance(scan_report.get("report_data"), dict):
            scan_findings = scan_report["report_data"].get("findings")

        fix_attempt_id = await create_fix_attempt(
            action_item_id=action_item_id,
            project_id=project_id,
            user_id=user_id,
        )

        return {
            "fix_attempt_id": fix_attempt_id,
            "action_item_id": action_item_id,
            "repo_url": repo_url,
            "scan_findings": scan_findings,
            "github_token": github_token,
        }

    async def validate_scan_fix(
        self,
        scan_id: UUID,
        user_id: str,
    ) -> dict:
        """Validate and prepare context for a scan-level fix.

        Returns dict with scan, project, repo_url, github_token,
        scan_findings, fix_attempt_id.

        Raises ValueError for validation failures.
        """
        role = get_user_role(user_id)
        if role != "developer":
            raise ValueError("fix_coming_soon")

        scan = await get_scan_report(scan_id, user_id)
        if not scan:
            raise ValueError("scan_not_found")

        if scan.get("status") != "completed":
            raise ValueError("scan_not_completed")

        active = await get_active_scan_fix_attempt(scan_id, user_id)
        if active:
            raise ValueError("fix_already_in_progress")

        project_id = UUID(scan["project_id"])
        project = await get_project(project_id)
        if not project:
            raise ValueError("project_not_found")

        repo_url = project["repo_url"]
        github_token = await get_github_access_token(user_id)

        scan_findings = None
        report_data = scan.get("report_data")
        if isinstance(report_data, dict):
            scan_findings = report_data.get("findings")
            if scan_findings is None:
                dr = report_data.get("discovery_report")
                if isinstance(dr, dict):
                    scan_findings = dr.get("findings")

        fix_attempt_id = await create_scan_fix_attempt(
            scan_id=scan_id,
            project_id=project_id,
            user_id=user_id,
        )

        return {
            "fix_attempt_id": fix_attempt_id,
            "scan_id": scan_id,
            "repo_url": repo_url,
            "scan_findings": scan_findings,
            "github_token": github_token,
        }


execute_fix_use_case = ExecuteFixUseCase()
