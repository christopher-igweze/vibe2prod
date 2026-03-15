"""Probe service — security probe orchestration.

This service handles the business logic for running security probes,
including background task execution and result processing.

Usage:
    from services.probe_service import ProbeService
    
    probe_service = ProbeService()
    await probe_service.run_probe(probe_id, target_url, user_id, probe_type, config)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from services import supabase_client as db
from services.probe_bridge import probe_bridge

logger = logging.getLogger(__name__)


class ProbeService:
    """Service for orchestrating security probes."""
    
    # Default polling configuration
    DEFAULT_POLL_INTERVAL = 10  # seconds
    DEFAULT_MAX_WAIT = 4200  # 70 minutes
    
    async def run_probe(
        self,
        probe_id: str,
        target_url: str,
        user_id: str,
        probe_type: str,
        config: dict | None = None,
    ) -> None:
        """Execute a security probe against a target URL.
        
        This is the main entry point for running a probe. It:
        1. Updates probe status to running
        2. Triggers scan on probe service
        3. Polls for completion
        4. Stores results and findings in DB
        """
        import asyncio
        
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

            # Poll until completion
            await self._poll_for_completion(probe_id, job_id)

            # Fetch and store results
            await self._process_results(probe_id, job_id, user_id)
            
            logger.info("Probe %s completed successfully", probe_id)
            
        except Exception as exc:
            logger.exception("Probe %s failed: %s", probe_id, exc)
            await self._handle_probe_failure(probe_id)

    async def _poll_for_completion(self, probe_id: str, job_id: str) -> None:
        """Poll probe service until scan completes or times out."""
        import asyncio
        
        poll_interval = self.DEFAULT_POLL_INTERVAL
        max_wait = self.DEFAULT_MAX_WAIT
        elapsed = 0

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
                if current_status != "completed":
                    raise RuntimeError(f"Probe service scan {current_status} after {elapsed}s")
                return

        raise RuntimeError(f"Probe service scan timed out after {elapsed}s")

    async def _process_results(self, probe_id: str, job_id: str, user_id: str) -> None:
        """Fetch and store probe results and findings."""
        results = await probe_bridge.get_results(job_id)
        completed_iso = datetime.now(timezone.utc).isoformat()

        # Store aggregate results
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
        finding_rows = self._build_finding_rows(results.get("findings", []))
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

    def _build_finding_rows(self, findings: list[dict]) -> list[dict]:
        """Transform raw findings into database rows."""
        return [
            {
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
            }
            for f in findings
        ]

    async def _handle_probe_failure(self, probe_id: str) -> None:
        """Handle probe execution failure."""
        try:
            await db.update_probe_status(
                probe_id, "failed",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception("Failed to update probe status after error for %s", probe_id)


# Module-level singleton
probe_service = ProbeService()
