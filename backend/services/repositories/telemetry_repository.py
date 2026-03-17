"""Telemetry event persistence."""

from __future__ import annotations

import logging

from services.repositories._base import _client

logger = logging.getLogger(__name__)


async def store_telemetry_event(data: dict) -> None:
    """Insert an anonymous telemetry event."""
    try:
        client = _client()
        client.table("telemetry_events").insert(data).execute()
    except Exception:
        logger.exception("Failed to insert telemetry event into database")
        raise
