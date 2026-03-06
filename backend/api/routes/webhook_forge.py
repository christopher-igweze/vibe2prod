"""FORGE webhook receiver — accepts real-time scan progress from sandboxed FORGE engines.

Each active scan registers a per-scan HMAC token. The FORGE engine
running inside a Daytona sandbox sends events via HTTP POST, signed
with that token. Events are appended to the shared SSE event bus so
the frontend receives live progress updates.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.routes._sse import event_buses
from models.agent_log import AgentLogEntry, AgentName, LogLevel, SSEEventType

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Per-scan token registry ────────────────────────────────────────────

_scan_tokens: dict[UUID, str] = {}


def register_scan_token(scan_id: UUID, token: str) -> None:
    """Register an HMAC token for a scan so the webhook can verify it."""
    _scan_tokens[scan_id] = token


def unregister_scan_token(scan_id: UUID) -> None:
    """Remove the HMAC token for a scan (cleanup after completion)."""
    _scan_tokens.pop(scan_id, None)


# ── Enum lookup helpers ────────────────────────────────────────────────

_EVENT_TYPE_MAP: dict[str, SSEEventType] = {e.value: e for e in SSEEventType}
_AGENT_NAME_MAP: dict[str, AgentName] = {a.value: a for a in AgentName}
_LOG_LEVEL_MAP: dict[str, LogLevel] = {l.value: l for l in LogLevel}


def _parse_event_type(raw: str) -> SSEEventType:
    """Map a string event_type to SSEEventType enum, defaulting to agent_log."""
    return _EVENT_TYPE_MAP.get(raw, SSEEventType.agent_log)


def _parse_agent_name(raw: str) -> AgentName:
    """Map a string agent name to AgentName enum, defaulting to orchestrator."""
    return _AGENT_NAME_MAP.get(raw, AgentName.orchestrator)


def _parse_log_level(raw: str) -> LogLevel:
    """Map a string level to LogLevel enum, defaulting to info."""
    return _LOG_LEVEL_MAP.get(raw, LogLevel.info)


# ── Webhook endpoint ──────────────────────────────────────────────────


@router.post("/forge")
async def forge_webhook(request: Request) -> JSONResponse:
    """Receive a signed event from the FORGE engine running in a sandbox."""
    body_bytes = await request.body()

    try:
        payload = json.loads(body_bytes)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    scan_id_raw = payload.get("scan_id")
    if not scan_id_raw:
        return JSONResponse(status_code=400, content={"error": "Missing scan_id"})

    try:
        scan_id = UUID(str(scan_id_raw))
    except (ValueError, AttributeError):
        return JSONResponse(status_code=400, content={"error": "Invalid scan_id"})

    # Look up the per-scan token
    token = _scan_tokens.get(scan_id)
    if token is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Scan not registered or already cleaned up"},
        )

    # Verify HMAC-SHA256 signature
    signature_header = request.headers.get("X-Forge-Signature", "")
    if not signature_header.startswith("sha256="):
        return JSONResponse(status_code=401, content={"error": "Missing or malformed signature"})

    expected_sig = hmac.new(
        token.encode(), body_bytes, hashlib.sha256
    ).hexdigest()
    provided_sig = signature_header.removeprefix("sha256=")

    if not hmac.compare_digest(expected_sig, provided_sig):
        return JSONResponse(status_code=401, content={"error": "Invalid signature"})

    # Build the AgentLogEntry and append to the event bus
    entry = AgentLogEntry(
        event_type=_parse_event_type(payload.get("event_type", "agent_log")),
        agent=_parse_agent_name(payload.get("agent", "Orchestrator")),
        message=payload.get("message", ""),
        level=_parse_log_level(payload.get("level", "info")),
        data=payload.get("data"),
    )

    bus = event_buses.get(scan_id)
    if bus is not None:
        bus.append(entry)

    return JSONResponse(status_code=200, content={"ok": True})
