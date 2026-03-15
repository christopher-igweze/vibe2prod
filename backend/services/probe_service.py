"""Probe service — security probe orchestration.

This service handles the business logic for running security probes,
including background task execution and result processing.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from services import supabase_client as db
from services.probe_bridge import probe_bridge

logger = logging.getLogger(__name__)


async def run_probe(
    probe_id: str,
    target_url: str,
    user_id: str,
    probe_type: str,
    config: dict | None = None,
) -> None:
    """Background task that triggers probe service scan and stores results."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        await db.update_probe_status(probe_id, "running", started_at=now_iso)

        # Trigger scan on probe service
        trigger_result = await probe_bridge.trigger_scan(target_url, config or {})
        if trigger_result.status == "error":
            raise RuntimeError(f"Probe service error: {trigger_result.error}")

        job_id = trigger_result.job_id
        if not job_id:
            raise RuntimeError("Probe service returned no job_id")
        logger.info("Probe %s → service job %s", probe_id, job_id)

        # Poll until completion (max 70 minutes, 10s interval)
        poll_interval = 10
        max_wait = 4200  # 70 minutes
        elapsed = 0
        current_status = "queued"

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            try:
                status = await probe_bridge.get_status(job_id)
                current_status = status.get("status", "unknown")
            except Exception as poll_err:
                logger.warning("Poll failed for %s (will retry): %s", job_id, poll_err)
                continue

            if current_status in ("completed", "failed", "cancelled"):
                break

        if current_status != "completed":
            raise RuntimeError(f"Probe service scan {current_status} after {elapsed}s")

        # Fetch results
        results = await probe_bridge.get_results(job_id)
        completed_iso = datetime.now(timezone.utc).isoformat()

        await db.update_probe_results(
            probe_id,
            total_findings=results.get("total_findings", 0),
            critical_count=results.get("critical_count", 0),
            high_count=results.get("high_count", 0),
            medium_count=results.get("medium_count", 0),
            low_count=results.get("low_count", 0),
            probe_score=results.get("probe_score", 0),
            report_data={"findings_summary": results.get("findings", [])[:50]},
        )

        # Save individual findings
        finding_rows = []
        for f in results.get("findings", []):
            finding_rows.append({
                "title": f.get("title", ""),
                "description": f.get("description", ""),
                "category": f.get("tool", ""),
                "severity": f.get("severity", "info"),
                "url_tested": f.get("url", ""),
                "method": "GET",
                "request_summary": "",
                "response_summary": "",
                "evidence": f.get("evidence", ""),
                "owasp_category": "",
                "cwe_id": "",
                "confidence": f.get("confidence", 0.8),
            })
        await db.save_probe_findings(probe_id, user_id, finding_rows)

        await db.update_probe_status(
            probe_id, "completed",
            completed_at=completed_iso,
            duration_seconds=results.get("duration_seconds", 0.0),
        )
        logger.info(
            "Probe %s completed: score=%d, findings=%d",
            probe_id, results.get("probe_score", 0), results.get("total_findings", 0),
        )
    except Exception as exc:
        logger.exception("Probe %s failed: %s", probe_id, exc)
        try:
            await db.update_probe_status(
                probe_id, "failed",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception("Failed to update probe status after error for %s", probe_id)


def create_probe_id() -> str:
    """Generate a new probe ID."""
    return str(uuid4())
