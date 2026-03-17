"""GitHub OAuth and token management operations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidTag

from config import settings
from services.repositories._base import _client
from services.token_encryption import decrypt_token

logger = logging.getLogger(__name__)


async def get_github_access_token(user_id: str) -> str | None:
    """Retrieve and decrypt the stored GitHub OAuth access token for *user_id*."""
    client = _client()
    row = (
        client.table("profiles")
        .select("github_access_token")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None
    raw = row.data[0].get("github_access_token")
    if not raw:
        return None
    try:
        return decrypt_token(raw, settings.github_token_encryption_key)
    except (InvalidTag, ValueError) as exc:
        logger.warning(
            "Failed to decrypt GitHub access token for user %s: %s. "
            "The stored credential may be corrupted or was encrypted with a "
            "different key.  Treating as disconnected.",
            user_id,
            exc,
        )
        return None


async def get_github_profile(user_id: str) -> tuple[str | None, str | None]:
    """Retrieve GitHub username and avatar URL from the user's profile."""
    client = _client()
    row = (
        client.table("profiles")
        .select("github_username, avatar_url")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return None, None
    return row.data[0].get("github_username"), row.data[0].get("avatar_url")


async def save_github_connection(
    *,
    user_id: str,
    access_token: str,
    github_username: str | None = None,
    avatar_url: str | None = None,
) -> None:
    """Persist GitHub OAuth credentials and profile metadata for a user.

    The *access_token* is expected to already be encrypted by the caller
    (``GitHubOAuthService.connect_user``).  This layer stores it as-is to
    avoid double-encryption.
    """
    client = _client()
    client.table("profiles").update(
        {
            "github_access_token": access_token,
            "github_username": github_username,
            "avatar_url": avatar_url,
        }
    ).eq("user_id", str(user_id)).execute()


async def clear_github_connection(*, user_id: str) -> None:
    """Remove stored GitHub OAuth credentials for a user."""
    client = _client()
    client.table("profiles").update(
        {
            "github_access_token": None,
            "github_username": None,
        }
    ).eq("user_id", str(user_id)).execute()


async def is_oauth_state_consumed(jti: str) -> bool:
    """Return True if the OAuth state nonce *jti* has already been consumed."""
    client = _client()
    try:
        row = (
            client.table("oauth_state_nonces")
            .select("jti")
            .eq("jti", jti)
            .limit(1)
            .execute()
        )
        return bool(row.data)
    except Exception as exc:
        logger.error("Failed to check OAuth state consumption for jti %s: %s", jti, exc)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "code": "oauth_state_check_failed",
                "message": "Unable to verify OAuth state. Please try again later.",
            },
        ) from exc


async def consume_oauth_state(
    *,
    jti: str,
    user_id: str,
    ttl_minutes: int,
) -> None:
    """Mark an OAuth state nonce as consumed so it cannot be replayed.

    .. deprecated:: Use :func:`consume_oauth_state_atomic` instead.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl_minutes)
    client = _client()
    try:
        client.table("oauth_state_nonces").insert(
            {
                "jti": jti,
                "user_id": str(user_id),
                "consumed_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        ).execute()
    except Exception as exc:
        error_code = getattr(exc, "code", None)
        error_message = str(exc).lower()
        is_unique_violation = (
            error_code == "23505"
            or "duplicate" in error_message
            or "unique constraint" in error_message
            or "already exists" in error_message
        )
        if is_unique_violation:
            logger.warning("OAuth state nonce %s already consumed (race condition suppressed).", jti)
        else:
            raise


async def consume_oauth_state_atomic(
    *,
    jti: str,
    user_id: str,
    ttl_minutes: int,
) -> bool:
    """Atomically consume an OAuth state nonce.

    Attempts a single INSERT into oauth_state_nonces.  The table has a
    UNIQUE constraint on ``jti``, so concurrent requests for the same
    nonce will fail with a unique-violation — only the first caller wins.

    Returns True if the nonce was successfully consumed (first use),
    False if it was already consumed (duplicate / replay).
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl_minutes)
    client = _client()
    try:
        client.table("oauth_state_nonces").insert(
            {
                "jti": jti,
                "user_id": str(user_id),
                "consumed_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        ).execute()
        return True
    except Exception as exc:
        error_code = getattr(exc, "code", None)
        error_message = str(exc).lower()
        is_unique_violation = (
            error_code == "23505"
            or "duplicate" in error_message
            or "unique constraint" in error_message
            or "already exists" in error_message
        )
        if is_unique_violation:
            logger.warning("OAuth state nonce %s already consumed (atomic reject).", jti)
            return False
        raise


async def purge_expired_oauth_states() -> int:
    """Delete expired nonce rows and return the count removed."""
    now = datetime.now(timezone.utc)
    client = _client()
    result = (
        client.table("oauth_state_nonces")
        .delete()
        .lt("expires_at", now.isoformat())
        .execute()
    )
    count = len(result.data) if result.data else 0
    logger.info("Purged %d expired OAuth state nonce(s).", count)
    return count
