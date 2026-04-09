"""User profile operations — roles, onboarding flags, API keys."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import settings
from services.repositories._base import _client

logger = logging.getLogger(__name__)


def get_user_role(user_id: str) -> str:
    """Return the user's role. Defaults to 'user' if profile missing."""
    client = _client()
    row = (
        client.table("profiles")
        .select("role")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return "user"
    return row.data[0].get("role", "user")


def get_user_profile(user_id: str) -> dict | None:
    """Return the user's profile including role and onboarding status."""
    client = _client()
    row = (
        client.table("profiles")
        .select("user_id,email,display_name,avatar_url,role,onboarding_complete,tour_completed,scan_credits,balance_usd,openrouter_key_encrypted")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    profile = row.data[0]
    # Expose boolean flag without leaking ciphertext
    profile["has_openrouter_key"] = profile.pop("openrouter_key_encrypted", None) is not None
    return profile


async def upgrade_user_role(user_id: str, new_role: str) -> bool:
    """Upgrade a user's role. Returns True if profile was updated."""
    client = _client()
    existing = (
        client.table("profiles")
        .select("role")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not existing.data:
        return False
    client.table("profiles").update({"role": new_role}).eq("user_id", str(user_id)).execute()
    return True


async def upsert_profile_from_clerk(
    user_id: str,
    email: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
    github_username: str | None = None,
) -> None:
    """Upsert a user profile from Clerk webhook data."""
    client = _client()
    data: dict = {
        "user_id": user_id,
        "email": email,
        "display_name": display_name,
        "avatar_url": avatar_url,
    }
    if github_username:
        data["github_username"] = github_username

    existing = (
        client.table("profiles")
        .select("user_id")
        .eq("user_id", user_id)
        .execute()
    )

    if existing.data:
        # Update existing profile (don't overwrite fields with None)
        update_data = {k: v for k, v in data.items() if v is not None and k != "user_id"}
        if update_data:
            client.table("profiles").update(update_data).eq("user_id", user_id).execute()
    else:
        # Insert new profile with default role and required defaults
        data["role"] = settings.default_user_role
        data.setdefault("coding_agent_provider", "anthropic")
        data.setdefault("coding_agent_model", "claude-sonnet-4")
        data.setdefault("coding_tool", "claude_code")
        client.table("profiles").insert(data).execute()


async def mark_tour_completed(user_id: str) -> None:
    """Mark the guided tour as completed."""
    client = _client()
    client.table("profiles").update({
        "tour_completed": True,
        "tour_completed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("user_id", str(user_id)).execute()


async def reset_tour(user_id: str) -> None:
    """Reset tour so user can retake it."""
    client = _client()
    client.table("profiles").update({
        "tour_completed": False,
        "tour_completed_at": None,
    }).eq("user_id", str(user_id)).execute()


async def update_profile_api_key(user_id: str, key_hash: str) -> None:
    """Store the hashed API key in the user's profile."""
    client = _client()
    client.table("profiles").update(
        {"api_key_hash": key_hash}
    ).eq("user_id", user_id).execute()


async def revoke_profile_api_key(user_id: str) -> None:
    """Remove the API key hash from the user's profile."""
    client = _client()
    client.table("profiles").update(
        {"api_key_hash": None}
    ).eq("user_id", user_id).execute()


async def has_api_key(user_id: str) -> bool:
    """Check if a user has an active API key."""
    client = _client()
    result = (
        client.table("profiles")
        .select("api_key_hash")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0].get("api_key_hash") is not None
    return False


async def lookup_user_by_api_key(key_hash: str) -> str | None:
    """Find a user_id by API key hash. Returns None if not found."""
    client = _client()
    result = (
        client.table("profiles")
        .select("user_id")
        .eq("api_key_hash", key_hash)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]["user_id"]
    return None


# ── OpenRouter BYOK key storage ──────────────────────────────────────


async def save_openrouter_key(user_id: str, encrypted_key: str) -> None:
    """Store the encrypted OpenRouter API key in the user's profile."""
    client = _client()
    client.table("profiles").update(
        {"openrouter_key_encrypted": encrypted_key}
    ).eq("user_id", user_id).execute()


async def remove_openrouter_key(user_id: str) -> None:
    """Remove the OpenRouter API key from the user's profile."""
    client = _client()
    client.table("profiles").update(
        {"openrouter_key_encrypted": None}
    ).eq("user_id", user_id).execute()


async def get_openrouter_key_encrypted(user_id: str) -> str | None:
    """Return the raw encrypted OpenRouter key, or None if not set."""
    client = _client()
    result = (
        client.table("profiles")
        .select("openrouter_key_encrypted")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0].get("openrouter_key_encrypted")
    return None
