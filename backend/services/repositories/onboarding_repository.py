"""Onboarding persistence operations."""

from __future__ import annotations

from services.repositories._base import _client


async def save_org_onboarding(*, user_id: str, payload: dict) -> None:
    client = _client()
    client.table("profiles").update(
        {
            "technical_level": payload.get("technical_level"),
            "explanation_style": payload.get("explanation_style"),
            "shipping_posture": payload.get("shipping_posture"),
            "tool_tags": payload.get("tool_tags") or [],
            "coding_tool": payload.get("coding_tool"),
            "coding_tool_other": payload.get("coding_tool_other"),
            "acquisition_source": payload.get("acquisition_source"),
            "acquisition_other": payload.get("acquisition_other"),
            "onboarding_complete": True,
        }
    ).eq("user_id", str(user_id)).execute()


async def is_onboarding_complete(user_id: str) -> bool:
    client = _client()
    row = (
        client.table("profiles")
        .select("onboarding_complete")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return False
    return bool(row.data[0].get("onboarding_complete"))


async def get_user_onboarding_preferences(user_id: str) -> dict | None:
    """Return stored onboarding preferences for report personalization."""
    client = _client()
    row = (
        client.table("profiles")
        .select(
            "technical_level,explanation_style,shipping_posture,tool_tags,coding_tool,coding_tool_other,acquisition_source,acquisition_other,onboarding_complete"
        )
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    return row.data[0]
