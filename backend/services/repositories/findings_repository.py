"""Findings, action items, and education card persistence."""

from __future__ import annotations

from uuid import UUID

from models.findings import ActionItem, EducationCard, Finding
from services.repositories._base import _client


async def save_findings(
    scan_id: UUID, project_id: UUID, user_id: str, findings: list[Finding]
) -> None:
    """Bulk-insert action_items rows from Scanner findings."""
    if not findings:
        return
    client = _client()
    rows = [
        {
            "scan_report_id": str(scan_id),
            "project_id": str(project_id),
            "user_id": str(user_id),
            "title": f.title,
            "description": f.description,
            "category": f.category.value,
            "severity": f.severity.value,
            "source": f.source.value,
            "file_path": f.file_path,
            "line_number": f.line_number,
        }
        for f in findings
    ]
    client.table("action_items").insert(rows).execute()


async def save_action_items(
    scan_id: UUID, project_id: UUID, user_id: str, items: list[ActionItem]
) -> None:
    """Persist prioritised action items from the Planner."""
    if not items:
        return
    client = _client()
    rows = [
        {
            "id": str(item.id),
            "scan_report_id": str(scan_id),
            "project_id": str(project_id),
            "user_id": str(user_id),
            "title": item.title,
            "description": item.description,
            "category": item.category.value,
            "severity": item.severity.value,
            "file_path": item.file_path,
            "line_number": item.line_number,
        }
        for item in items
    ]
    client.table("action_items").insert(rows).execute()


async def save_education(
    scan_id: UUID,
    project_id: UUID,
    user_id: str,
    cards: list[EducationCard],
) -> None:
    """Attach education text to specific action_items rows."""
    if not cards:
        return
    client = _client()
    for card in cards:
        client.table("action_items").update(
            {
                "why_it_matters": card.why_it_matters,
                "cto_perspective": card.cto_perspective,
            }
        ).eq("id", str(card.action_item_id)).execute()


async def get_action_item(action_item_id: UUID, user_id: str) -> dict | None:
    """Fetch a single action item by ID, scoped to the requesting user."""
    client = _client()
    row = (
        client.table("action_items")
        .select("*")
        .eq("id", str(action_item_id))
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]


async def update_action_item_fix_status(
    action_item_id: UUID, fix_status: str
) -> None:
    """Update the fix_status on an action item."""
    client = _client()
    client.table("action_items").update(
        {"fix_status": fix_status}
    ).eq("id", str(action_item_id)).execute()


async def store_shared_findings(data: dict) -> None:
    """Insert opt-in anonymized findings."""
    client = _client()
    client.table("telemetry_events").insert(
        {"event": "findings_shared", **data}
    ).execute()
