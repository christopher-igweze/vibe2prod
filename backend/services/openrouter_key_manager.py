"""OpenRouter BYOK key storage, retrieval, and validation.

Users who supply their own OpenRouter API key (BYOK) pay OpenRouter
directly instead of being charged from their wallet balance.  Keys are
encrypted at rest with AES-256-GCM (same scheme as GitHub tokens).
"""

from __future__ import annotations

import logging

import httpx

from config import settings
from services.repositories import user_repository as db
from services.token_encryption import decrypt_token, encrypt_token, is_encrypted

logger = logging.getLogger(__name__)

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


async def save_key(user_id: str, plaintext_key: str) -> str:
    """Validate, encrypt, and persist the user's OpenRouter API key.

    Returns a masked hint (e.g. ``sk-or-v1-abc...****``).

    Raises ``ValueError`` if the key fails validation.
    """
    if not await validate_key(plaintext_key):
        raise ValueError("The provided OpenRouter API key is invalid or could not be verified.")

    encrypted = encrypt_token(plaintext_key, settings.github_token_encryption_key)
    await db.save_openrouter_key(user_id, encrypted)
    return _mask_key(plaintext_key)


async def get_decrypted_key(user_id: str) -> str | None:
    """Retrieve and decrypt the stored OpenRouter API key for a user."""
    raw = await db.get_openrouter_key_encrypted(user_id)
    if not raw:
        return None
    if is_encrypted(raw):
        try:
            return decrypt_token(raw, settings.github_token_encryption_key)
        except Exception:
            logger.exception(
                "Failed to decrypt OpenRouter key for user %s — key may be corrupt",
                user_id,
            )
            return None
    # Legacy plaintext fallback
    return raw


async def get_key_hint(user_id: str) -> str | None:
    """Return a masked hint of the stored key, or None if not set."""
    key = await get_decrypted_key(user_id)
    if not key:
        return None
    return _mask_key(key)


async def remove_key(user_id: str) -> None:
    """Remove the stored OpenRouter API key."""
    await db.remove_openrouter_key(user_id)


async def validate_key(api_key: str) -> bool:
    """Test an OpenRouter API key by hitting the /models endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _OPENROUTER_MODELS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp.status_code == 200
    except httpx.HTTPError:
        logger.warning("OpenRouter key validation request failed")
        return False


def _mask_key(key: str) -> str:
    """Return a safe display hint: first 8 chars + ****."""
    if len(key) <= 8:
        return "****"
    return key[:8] + "****"
