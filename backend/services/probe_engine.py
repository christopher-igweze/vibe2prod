"""Security probe engine — facade for backward compatibility.

Core logic has been split into:
- services/domain/probe_executor.py — test execution
- services/domain/probe_result_processor.py — result processing/scoring

This module preserves the original ProbeEngine API so existing callers
(probe_service.py) continue to work unchanged.
"""

from __future__ import annotations

import logging
import time

import httpx

from config import settings
from models.probe import ProbeResult
from services.domain.probe_executor import ProbeExecutor
from services.domain.probe_result_processor import compile_result

logger = logging.getLogger(__name__)


class ProbeEngine:
    """Async security probe engine with rate limiting and scope enforcement."""

    def __init__(self, target_url: str, probe_type: str = "security", config: dict | None = None):
        self.target_url = str(target_url)
        self.probe_type = probe_type
        self.config = config or {}
        self._executor = ProbeExecutor(self.target_url, self.config)

    async def run(self) -> ProbeResult:
        """Execute enabled security test modules and compile results."""
        start = time.monotonic()

        async with httpx.AsyncClient(
            timeout=settings.probe_request_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": "Vibe2Prod-SecurityProbe/1.0",
                "X-Vibe2Prod-Probe": "true",
            },
            verify=True,
        ) as client:
            findings = await self._executor.execute_all(client)

        duration = time.monotonic() - start
        return compile_result(findings, duration)
