"""Scan report CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from models.findings import AuditReport
from models.scan import ScanStatus
from services.repositories._base import _client
from services.repositories.health_repository import _compute_scores_from_discovery

logger = logging.getLogger(__name__)


async def create_scan_report(
    scan_id: UUID,
    project_id: UUID,
    user_id: str,
    scan_tier: str = "deep",
    project_intake: dict | None = None,
    primer_summary: str | None = None,
    audit_confidence: int | None = None,
) -> UUID:
    """Insert a new scan_reports row using the caller-supplied *scan_id*."""
    client = _client()
    row = (
        client.table("scan_reports")
        .insert(
            {
                "id": str(scan_id),
                "project_id": str(project_id),
                "user_id": str(user_id),
                "scan_tier": scan_tier,
                "status": ScanStatus.pending.value,
                "project_intake": project_intake,
                "primer_summary": primer_summary,
                "audit_confidence": audit_confidence,
            }
        )
        .execute()
    )
    return UUID(row.data[0]["id"])


async def update_scan_status(
    scan_id: UUID,
    status: ScanStatus,
    *,
    failure_reason: str | None = None,
) -> None:
    client = _client()
    update: dict = {"status": status.value}
    if failure_reason is not None:
        update["failure_reason"] = failure_reason
    try:
        client.table("scan_reports").update(update).eq(
            "id", str(scan_id)
        ).execute()
    except Exception:
        if failure_reason is not None:
            client.table("scan_reports").update(
                {"status": status.value}
            ).eq("id", str(scan_id)).execute()
        else:
            raise


async def fail_orphaned_scans() -> int:
    """Mark any scans stuck in 'pending' or 'scanning' as 'failed'."""
    client = _client()
    result = (
        client.table("scan_reports")
        .update({"status": ScanStatus.failed.value})
        .in_("status", [ScanStatus.pending.value, ScanStatus.scanning.value])
        .execute()
    )
    return len(result.data) if result.data else 0


async def update_scan_with_discovery(
    scan_id: UUID,
    discovery_report: dict,
    *,
    evaluation: dict | None = None,
    aivss_score: dict | None = None,
) -> None:
    """Store FORGE discovery report data and computed scores."""
    scores = _compute_scores_from_discovery(discovery_report, evaluation=evaluation)
    client = _client()

    report_data: dict = {"discovery_report": discovery_report}
    if evaluation:
        report_data["evaluation"] = evaluation
    if aivss_score:
        report_data["aivss_score"] = aivss_score

    client.table("scan_reports").update(
        {
            "status": ScanStatus.completed.value,
            "report_data": report_data,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            **scores,
        }
    ).eq("id", str(scan_id)).execute()


async def save_report(
    scan_id: UUID,
    report: AuditReport,
    scan_tier: str = "deep",
    report_data_extra: dict | None = None,
) -> None:
    """Persist the final assembled report."""
    client = _client()
    report_data = report.model_dump(mode="json")
    if isinstance(report_data_extra, dict) and report_data_extra:
        report_data.update(report_data_extra)

    client.table("scan_reports").update(
        {
            "status": ScanStatus.completed.value,
            "health_score": report.health_score,
            "security_score": report.security_score,
            "reliability_score": report.reliability_score,
            "scalability_score": report.scalability_score,
            "audit_confidence": report.audit_confidence,
            "primer_summary": report.primer_summary,
            "evolution_report": report.evolution.model_dump(mode="json"),
            "report_data": report_data,
        }
    ).eq("id", str(scan_id)).execute()

    scan_row = (
        client.table("scan_reports")
        .select("project_id")
        .eq("id", str(scan_id))
        .limit(1)
        .execute()
    )
    if scan_row.data:
        project_id = scan_row.data[0]["project_id"]
        project_row = (
            client.table("projects")
            .select("scan_count")
            .eq("id", project_id)
            .limit(1)
            .execute()
        )
        current_scan_count = 0
        if project_row.data:
            current_scan_count = int(project_row.data[0].get("scan_count") or 0)
        client.table("projects").update(
            {
                "latest_health_score": report.health_score,
                "latest_scan_tier": scan_tier,
                "scan_count": current_scan_count + 1,
            }
        ).eq("id", project_id).execute()


async def list_user_scans(
    user_id: str, *, limit: int = 20, offset: int = 0,
) -> list[dict]:
    """Return scans for a user, newest first."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select(
            "id,status,scan_tier,health_score,security_score,reliability_score,scalability_score,created_at,project_id,"
            "projects(id,user_id)"
        )
        .eq("user_id", str(user_id))
        .eq("projects.user_id", str(user_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    scans = []
    for item in (row.data or []):
        scan = {
            "id": item.get("id"),
            "status": item.get("status"),
            "scan_tier": item.get("scan_tier"),
            "health_score": item.get("health_score"),
            "security_score": item.get("security_score"),
            "reliability_score": item.get("reliability_score"),
            "scalability_score": item.get("scalability_score"),
            "created_at": item.get("created_at"),
            "project_id": item.get("project_id"),
        }
        scans.append(scan)

    return scans


async def count_user_scans(user_id: str) -> int:
    """Return the total number of scans for a user."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .execute()
    )
    return row.count or 0


async def get_scan_report(scan_id: UUID, user_id: str) -> dict | None:
    """Fetch a scan report row by ID, scoped to the requesting user."""
    client = _client()
    row = (
        client.table("scan_reports")
        .select("*")
        .eq("id", str(scan_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


async def delete_scan_report(scan_id: UUID, user_id: str) -> bool:
    """Delete a scan report scoped to the requesting user."""
    client = _client()
    result = (
        client.table("scan_reports")
        .delete()
        .eq("id", str(scan_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    return bool(result.data)
