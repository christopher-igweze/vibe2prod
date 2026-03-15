"""HTTP bridge to Security Probe Service.

Usage:
    from services.probe_bridge import probe_bridge

    result = await probe_bridge.trigger_scan("https://target.com", config)
    status = await probe_bridge.get_status(result.job_id)
    findings = await probe_bridge.get_results(result.job_id)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from config import settings
from services.http_client import shared_client

logger = logging.getLogger(__name__)


@dataclass
class ProbeServiceResult:
    """Result from a probe service API call."""
    job_id: str = ""
    status: str = "unknown"
    error: str = ""


class ProbeBridge:
    """HTTP client for the Security Probe microservice."""

    def __init__(
        self,
        service_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 30,
    ):
        self.service_url = (service_url or getattr(settings, "probe_service_url", "")).rstrip("/")
        self.api_key = api_key or getattr(settings, "probe_service_api_key", "")
        self.timeout = timeout

    async def _post(self, path: str, payload: dict) -> dict:
        """POST JSON to probe service."""
        url = f"{self.service_url}{path}"
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        resp = await shared_client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _get(self, path: str) -> dict:
        """GET from probe service."""
        url = f"{self.service_url}{path}"
        headers = {"X-API-Key": self.api_key}
        resp = await shared_client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, path: str) -> dict:
        """DELETE to probe service."""
        url = f"{self.service_url}{path}"
        headers = {"X-API-Key": self.api_key}
        resp = await shared_client.delete(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def trigger_scan(self, target_url: str, config: dict) -> ProbeServiceResult:
        """Start a scan on the probe service."""
        try:
            resp = await self._post("/api/v1/scans", {
                "target_url": target_url,
                "authorization_confirmed": True,
                "config": config,
            })
            return ProbeServiceResult(
                job_id=resp.get("job_id", ""),
                status=resp.get("status", "queued"),
            )
        except Exception as e:
            logger.error("Failed to trigger probe scan: %s", e)
            return ProbeServiceResult(status="error", error=str(e))

    async def get_status(self, job_id: str) -> dict:
        """Get scan status from probe service."""
        try:
            return await self._get(f"/api/v1/scans/{job_id}")
        except Exception as e:
            logger.error("Failed to get probe status for %s: %s", job_id, e)
            return {"job_id": job_id, "status": "error", "error": str(e)}

    async def get_results(self, job_id: str) -> dict:
        """Get final scan results from probe service."""
        try:
            return await self._get(f"/api/v1/scans/{job_id}/results")
        except Exception as e:
            logger.error("Failed to get probe results for %s: %s", job_id, e)
            return {"job_id": job_id, "status": "error", "error": str(e)}

    async def cancel_scan(self, job_id: str) -> dict:
        """Cancel a running scan."""
        try:
            return await self._delete(f"/api/v1/scans/{job_id}")
        except Exception as e:
            logger.error("Failed to cancel probe %s: %s", job_id, e)
            return {"job_id": job_id, "status": "error", "error": str(e)}


# Module-level singleton (initialized from settings)
probe_bridge = ProbeBridge()
