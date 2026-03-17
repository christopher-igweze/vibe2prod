"""Core probe execution logic — backward-compatible facade.

Re-exports from split sub-modules:
  - probe_setup: Test patterns, payloads, and configuration
  - probe_runner: Individual security test methods
  - probe_result_collector: Result aggregation
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import httpx

from config import settings
from models.probe import ProbeFinding

# Re-export patterns and constants for backward compatibility
from services.domain.probe_setup import (  # noqa: F401
    SQL_ERROR_PATTERNS,
    XSS_PAYLOADS,
    SENSITIVE_PATHS,
    REDIRECT_PARAMS,
    AUTH_PATHS,
)
from services.domain.probe_runner import ProbeRunner  # noqa: F401
from services.domain.probe_result_collector import collect_results  # noqa: F401

logger = logging.getLogger(__name__)


class ProbeExecutor:
    """Runs individual security test modules against a target URL.

    Delegates to ProbeRunner for test execution and collect_results
    for aggregation.
    """

    def __init__(self, target_url: str, config: dict | None = None):
        self.target_url = str(target_url)
        self.config = config or {}
        parsed = urlparse(self.target_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.target_domain = parsed.hostname or ""
        self._semaphore = asyncio.Semaphore(settings.probe_max_concurrent)
        self._runner = ProbeRunner(
            target_url=self.target_url,
            base_url=self.base_url,
            target_domain=self.target_domain,
            semaphore=self._semaphore,
        )

    def _is_test_enabled(self, test_id: str) -> bool:
        selected = self.config.get("tests")
        if not selected:
            return True
        return test_id in selected

    async def execute_all(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        """Run all enabled tests and return combined findings."""
        disallowed = await self._runner.check_robots_txt(client)

        tests = []
        if self._is_test_enabled("security_headers"):
            tests.append(self._runner.test_security_headers(client))
        if self._is_test_enabled("sensitive_data"):
            tests.append(self._runner.test_sensitive_exposure(client, disallowed))
        if self._is_test_enabled("cookie_security"):
            tests.append(self._runner.test_cookie_security(client))
        if self._is_test_enabled("ssl_tls"):
            tests.append(self._runner.test_ssl_tls())
        if self._is_test_enabled("server_misconfig"):
            tests.append(self._runner.test_misconfiguration(client))
        if self._is_test_enabled("sql_injection"):
            tests.append(self._runner.test_injection(client))
        if self._is_test_enabled("xss"):
            tests.append(self._runner.test_xss(client))
        if self._is_test_enabled("csrf"):
            tests.append(self._runner.test_csrf(client))
        if self._is_test_enabled("open_redirects"):
            tests.append(self._runner.test_open_redirects(client))
        if self._is_test_enabled("auth_issues"):
            tests.append(self._runner.test_auth_issues(client))

        return await collect_results(tests)

    # Backward-compatible delegation methods for direct access
    async def _rate_limited_get(
        self, client: httpx.AsyncClient, url: str, **kwargs
    ) -> httpx.Response | None:
        return await self._runner._rate_limited_get(client, url, **kwargs)

    async def _check_robots_txt(self, client: httpx.AsyncClient) -> set[str]:
        return await self._runner.check_robots_txt(client)

    def _is_disallowed(self, path: str, disallowed: set[str]) -> bool:
        return self._runner._is_disallowed(path, disallowed)

    async def _test_security_headers(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_security_headers(client)

    async def _test_sensitive_exposure(self, client: httpx.AsyncClient, disallowed: set[str]) -> list[ProbeFinding]:
        return await self._runner.test_sensitive_exposure(client, disallowed)

    async def _test_cookie_security(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_cookie_security(client)

    async def _test_ssl_tls(self) -> list[ProbeFinding]:
        return await self._runner.test_ssl_tls()

    async def _test_misconfiguration(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_misconfiguration(client)

    async def _test_injection(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_injection(client)

    async def _test_xss(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_xss(client)

    async def _test_csrf(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_csrf(client)

    async def _test_open_redirects(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_open_redirects(client)

    async def _test_auth_issues(self, client: httpx.AsyncClient) -> list[ProbeFinding]:
        return await self._runner.test_auth_issues(client)
