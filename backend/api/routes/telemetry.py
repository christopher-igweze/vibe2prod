"""Telemetry API — anonymous scan metrics and opt-in findings sharing.

CLI users authenticate with ``X-API-Key: v2p_...`` header.  When present,
the telemetry event is linked to their account via SHA-256 hash lookup.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from services import supabase_client as db

router = APIRouter()
logger = logging.getLogger(__name__)


class TelemetryEvent(BaseModel):
    event: str  # "scan_complete", "findings_shared"
    machine_id: str = ""  # hashed, anonymous
    version: str = ""
    model: str = ""
    mode: str = ""
    findings_count: int = 0
    duration_seconds: float = 0
    cost_usd: float = 0
    timestamp: str = ""


class SharedFindings(BaseModel):
    machine_id: str = ""
    version: str = ""
    findings: list[dict] = []  # anonymized finding patterns
    repo_profile: dict = {}  # language, framework stats


async def _resolve_api_key(request: Request) -> str | None:
    """Resolve an X-API-Key header to a user_id, or None."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        return None
    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return await db.lookup_user_by_api_key(key_hash)
    except Exception:
        logger.exception("Failed to resolve API key to user_id")
        return None


@router.post("/telemetry")
async def ingest_telemetry(event: TelemetryEvent, request: Request):
    """Store anonymous scan metrics. No auth required. API key optional."""
    try:
        data = event.model_dump()
        user_id = await _resolve_api_key(request)
        if user_id:
            data["user_id"] = user_id
        await db.store_telemetry_event(data)
    except Exception:
        logger.exception("Failed to store telemetry event")
    return {"ok": True}


@router.post("/telemetry/findings")
async def ingest_findings(payload: SharedFindings, request: Request):
    """Store opt-in anonymized findings. No auth required. API key optional."""
    try:
        data = payload.model_dump()
        user_id = await _resolve_api_key(request)
        if user_id:
            data["user_id"] = user_id
        await db.store_shared_findings(data)
    except Exception:
        logger.exception("Failed to store shared findings")
    return {"ok": True}
