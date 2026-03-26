"""Forgeignore training data persistence."""

from __future__ import annotations

import logging

from services.repositories._base import _client

logger = logging.getLogger(__name__)


async def store_forgeignore_entry(data: dict) -> bool:
    """Insert a forgeignore entry. Returns True if inserted, False if duplicate.

    Uses upsert with ON CONFLICT (fingerprint) DO NOTHING so that
    duplicate submissions are silently deduplicated.
    """
    client = _client()
    result = (
        client.table("forgeignore_entries")
        .upsert(data, on_conflict="fingerprint", ignore_duplicates=True)
        .execute()
    )
    return bool(result.data)
