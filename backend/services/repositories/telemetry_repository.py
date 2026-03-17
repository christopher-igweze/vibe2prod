"""Telemetry event persistence."""

from __future__ import annotations

import logging

from services.repositories._base import _client

logger = logging.getLogger(__name__)


async def store_telemetry_event(data: dict) -> None:
    """Insert an anonymous telemetry event.

    Raises on failure — callers are responsible for logging and deciding
    whether to propagate or swallow the error.  This avoids double-logging
    when the route handler already logs the exception.
    """
    client = _client()
    client.table("telemetry_events").insert(data).execute()
