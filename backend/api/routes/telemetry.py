"""Telemetry API — anonymous scan metrics and opt-in findings sharing."""

from __future__ import annotations

import logging

from fastapi import APIRouter
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


@router.post("/telemetry")
async def ingest_telemetry(event: TelemetryEvent):
    """Store anonymous scan metrics. No auth required."""
    try:
        await db.store_telemetry_event(event.model_dump())
    except Exception:
        pass  # Never fail on telemetry
    return {"ok": True}


@router.post("/telemetry/findings")
async def ingest_findings(payload: SharedFindings):
    """Store opt-in anonymized findings. No auth required."""
    try:
        await db.store_shared_findings(payload.model_dump())
    except Exception:
        pass  # Never fail on telemetry
    return {"ok": True}
