"""GET /api/status/{scan_id} — SSE stream of audit progress.

The frontend connects to this endpoint immediately after calling
POST /api/audit and receives a real-time stream of agent logs,
findings, probe results, and the final report.

When an in-memory event bus exists (scan actively running in this
process), events stream in real-time.  If the bus has been cleaned
up or was never created (e.g. after a server restart), the endpoint
falls back to polling the database for the scan's final status so
the client always gets a terminal event.
"""

from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException
from sse_starlette.sse import EventSourceResponse

from api.middleware.rate_limit import limiter, rate_limit_string
from models.agent_log import SSEEventType
from api.routes._sse import event_buses
from services import supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


async def _event_generator(scan_id: UUID, user_id: str):
    """Yield SSE events as agents produce them.

    If the in-memory event bus exists, stream real-time events from it.
    Otherwise, fall back to polling the database until the scan reaches
    a terminal status (completed / failed).
    """
    bus = event_buses.get(scan_id)

    if bus is not None:
        # ── Real-time mode: stream from in-memory event bus ──
        cursor = 0
        idle_ticks = 0
        max_idle = 600  # 10 minutes with no new events → close

        while True:
            # Re-fetch in case bus was removed externally
            current_bus = event_buses.get(scan_id)
            if current_bus is None:
                break

            if cursor < len(current_bus):
                for entry in current_bus[cursor:]:
                    yield {
                        "event": entry.event_type.value,
                        "data": json.dumps(
                            entry.model_dump(mode="json"), default=str
                        ),
                    }

                    if entry.event_type in (
                        SSEEventType.scan_complete,
                        SSEEventType.scan_error,
                    ):
                        return

                cursor = len(current_bus)
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= max_idle:
                    yield {
                        "event": "timeout",
                        "data": json.dumps({"message": "Stream timed out"}),
                    }
                    return

            await asyncio.sleep(1)
    else:
        # ── Fallback mode: poll database for terminal status ──
        max_polls = 200  # ~10 minutes at 3s intervals

        for poll in range(max_polls):
            scan = await db.get_scan_report(scan_id, user_id)
            if not scan:
                yield {
                    "event": "scan_error",
                    "data": json.dumps({"message": "Scan not found"}),
                }
                return

            status = scan.get("status", "pending")

            if status == "completed":
                total = 0
                report = scan.get("report_data", {})
                if isinstance(report, dict):
                    dr = report.get("discovery_report", {})
                    if isinstance(dr, dict):
                        total = dr.get("total_findings", 0)
                yield {
                    "event": "scan_complete",
                    "data": json.dumps({
                        "status": "completed",
                        "findings_count": total,
                    }),
                }
                return

            if status == "failed":
                yield {
                    "event": "scan_error",
                    "data": json.dumps({
                        "status": "failed",
                        "message": "Scan failed",
                    }),
                }
                return

            # Still running — send a heartbeat so the client knows we're alive
            yield {
                "event": "heartbeat",
                "data": json.dumps({"status": status, "poll": poll}),
            }

            await asyncio.sleep(3)

        yield {
            "event": "timeout",
            "data": json.dumps({"message": "Stream timed out waiting for scan"}),
        }


@router.get("/status/{scan_id}")
@limiter.limit(rate_limit_string())
async def stream_status(scan_id: UUID, request: Request):
    """Stream audit events for a given scan via SSE."""
    user_id: str = request.state.user_id
    scan = await db.get_scan_report(scan_id, user_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return EventSourceResponse(
        _event_generator(scan_id, user_id),
        media_type="text/event-stream",
    )
