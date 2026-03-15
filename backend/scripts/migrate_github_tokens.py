"""Migration script to encrypt existing plaintext GitHub OAuth tokens.

This script migrates unencrypted GitHub access tokens stored in the profiles table
to the encrypted format. It should be run once after deploying the encryption feature.

Usage:
    # Dry run (shows what would be migrated without making changes)
    python scripts/migrate_github_tokens.py --dry-run

    # Actual migration
    python scripts/migrate_github_tokens.py

    # Migrate specific users
    python scripts/migrate_github_tokens.py --user-id user_123 --user-id user_456

Environment:
    Requires GITHUB_TOKEN_ENCRYPTION_KEY to be set to a valid 32-byte base64-encoded key.

Safety:
    - Tokens that are already encrypted will be skipped
    - Tokens that fail encryption will be logged but not modified
    - A backup of affected rows is recommended before running
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from services.token_encryption import encrypt_token, is_encrypted
from supabase import create_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_supabase_client() -> Any:
    """Create a Supabase client."""
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def get_tokens_to_migrate(
    client: Any, user_ids: list[str] | None = None
) -> list[dict]:
    """Fetch profiles with unencrypted GitHub access tokens.

    Args:
        client: Supabase client
        user_ids: Optional list of specific user IDs to migrate

    Returns:
        List of profile records with plaintext tokens
    """
    query = (
        client.table("profiles")
        .select("user_id, github_access_token, github_username")
        .not_.is_("github_access_token", "null")
    )

    if user_ids:
        query = query.in_("user_id", user_ids)

    result = query.execute()
    profiles = result.data or []

    # Filter to only those with unencrypted tokens
    plaintext_profiles = []
    for profile in profiles:
        token = profile.get("github_access_token")
        if token and not is_encrypted(token):
            plaintext_profiles.append(profile)

    return plaintext_profiles


async def migrate_token(
    client: Any, user_id: str, plaintext_token: str, dry_run: bool = False
) -> bool:
    """Encrypt and save a single token.

    Args:
        client: Supabase client
        user_id: The user's ID
        plaintext_token: The unencrypted token
        dry_run: If True, don't actually update the database

    Returns:
        True if migration was successful or skipped, False on error
    """
    try:
        encrypted_token = encrypt_token(
            plaintext_token, settings.github_token_encryption_key
        )

        if dry_run:
            logger.info(
                "[DRY RUN] Would encrypt token for user %s (%s -> %s...)",
                user_id,
                plaintext_token[:8],
                encrypted_token[:20],
            )
            return True

        client.table("profiles").update(
            {"github_access_token": encrypted_token}
        ).eq("user_id", user_id).execute()

        logger.info(
            "Successfully encrypted token for user %s (%s -> %s...)",
            user_id,
            plaintext_token[:8],
            encrypted_token[:20],
        )
        return True

    except Exception as exc:
        logger.error("Failed to encrypt token for user %s: %s", user_id, exc)
        return False


async def main() -> int:
    """Run the migration.

    Returns:
        Exit code (0 for success, 1 for partial failure, 2 for complete failure)
    """
    parser = argparse.ArgumentParser(
        description="Migrate plaintext GitHub tokens to encrypted format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--user-id",
        action="append",
        dest="user_ids",
        help="Migrate specific user ID (can be specified multiple times)",
    )
    args = parser.parse_args()

    # Verify encryption key is configured
    if not settings.github_token_encryption_key:
        logger.error(
            "GITHUB_TOKEN_ENCRYPTION_KEY is not set. "
            "Generate a key with: python -c \"import secrets, base64; "
            "print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
        )
        return 2

    client = get_supabase_client()

    logger.info("Fetching profiles with unencrypted tokens...")
    profiles = await get_tokens_to_migrate(client, args.user_ids)

    if not profiles:
        logger.info("No unencrypted tokens found. Migration complete!")
        return 0

    logger.info("Found %d profile(s) with unencrypted tokens", len(profiles))

    if args.dry_run:
        logger.info("\n[DRY RUN MODE - No changes will be made]\n")

    success_count = 0
    fail_count = 0

    for profile in profiles:
        user_id = profile["user_id"]
        token = profile["github_access_token"]
        username = profile.get("github_username", "unknown")

        logger.info(
            "Processing user %s (GitHub: %s, token prefix: %s...)",
            user_id,
            username,
            token[:8] if token else "None",
        )

        if await migrate_token(client, user_id, token, args.dry_run):
            success_count += 1
        else:
            fail_count += 1

    logger.info(
        "\nMigration complete: %d succeeded, %d failed", success_count, fail_count
    )

    if fail_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
