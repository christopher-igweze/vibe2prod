"""Telemetry event persistence."""

from __future__ import annotations

from services.repositories._base import _client


async def store_telemetry_event(data: dict) -> None:
    """Insert an anonymous telemetry event."""
    client = _client()
    client.table("telemetry_events").insert(data).execute()
