"""GitHub token storage, retrieval, and encryption.

Extracted from github_oauth_service.py for single-responsibility.
"""

from __future__ import annotations

import logging

from config import settings
from services import supabase_client as db
from services.token_encryption import decrypt_token, encrypt_token, is_encrypted

logger = logging.getLogger(__name__)


async def get_decrypted_token(user_id: str) -> str | None:
    """Retrieve and decrypt the stored GitHub access token for a user.

    Handles legacy plaintext tokens gracefully: if the stored value does
    not look encrypted it is returned as-is (migration path).
    """
    raw = await db.get_github_access_token(user_id)
    if not raw:
        return None
    if is_encrypted(raw):
        try:
            return decrypt_token(raw, settings.github_token_encryption_key)
        except Exception:
            logger.exception(
                "Failed to decrypt GitHub token for user %s — token may be corrupt",
                user_id,
            )
            return None
    # Legacy plaintext token — return as-is
    return raw


async def connect_user(
    user_id: str,
    access_token: str,
    github_username: str | None = None,
    avatar_url: str | None = None,
) -> None:
    """Persist GitHub OAuth credentials for a user.

    The access token is encrypted with AES-256-GCM before storage so that
    a database compromise does not expose usable GitHub tokens.
    """
    encrypted = encrypt_token(access_token, settings.github_token_encryption_key)
    await db.save_github_connection(
        user_id=user_id,
        access_token=encrypted,
        github_username=github_username,
        avatar_url=avatar_url,
    )


async def disconnect_user(user_id: str) -> None:
    """Remove GitHub OAuth credentials for a user."""
    await db.clear_github_connection(user_id=user_id)
