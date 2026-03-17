"""Probe execution — runs individual security tests against a target URL.

Extracted from probe_executor.py for single-responsibility.
Contains the core test methods for security scanning.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

import httpx

from config import settings
from models.probe import ProbeFinding
from services.domain.probe_setup import (
    AUTH_PATHS,
    REDIRECT_PARAMS,
    SENSITIVE_PATHS,
    SQL_ERROR_PATTERNS,
    XSS_PAYLOADS,
)

logger = logging.getLogger(__name__)


class ProbeRunner:
    """Runs individual security test methods against a target URL.

    This class contains all the actual test logic. ProbeExecutor
    orchestrates which tests run; ProbeRunner performs them.
    """

    def __init__(self, target_url: str, base_url: str, target_domain: str, semaphore: asyncio.Semaphore):
        self.target_url = target_url
        self.base_url = base_url
        self.target_domain = target_domain
        self._semaphore = semaphore

    async def _rate_limited_get(
        self, client: httpx.AsyncClient, url: str, **kwargs
    ) -> httpx.Response | None:
        parsed = urlparse(url)
        if parsed.hostname != self.target_domain:
            return None
        async with self._semaphore:
            try:
                return await client.get(url, **kwargs)
            except httpx.HTTPError as exc:
                logger.debug("Request to %s failed: %s", url, exc)
                return None

    async def check_robots_txt(self, client: httpx.AsyncClient) -> set[str]:
        disallowed: set[str] = set()
        resp = await self._rate_limited_get(client, f"{self.base_url}/robots.txt")
        if resp and resp.status_code == 200:
            for line in resp.text.splitlines():
                line = line.strip().lower()
                if line.startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.add(path)
        return disallowed

    def _is_disallowed(self, path: str, disallowed: set[str]) -> bool:
        for d in disallowed:
            if path.startswith(d):
                return True
        return False

    async def test_security_headers(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        resp = await self._rate_limited_get(client, self.target_url)
        if not resp:
            return findings

        headers = {k.lower(): v for k, v in resp.headers.items()}

        checks = [
            ("content-security-policy", "Missing Content-Security-Policy header",
             "Content Security Policy (CSP) helps prevent XSS and data injection attacks.",
             "medium", "A05:2021 - Security Misconfiguration", "CWE-693"),
            ("strict-transport-security", "Missing Strict-Transport-Security (HSTS) header",
             "HSTS enforces secure HTTPS connections, preventing protocol downgrade attacks.",
             "medium", "A05:2021 - Security Misconfiguration", "CWE-311"),
            ("x-frame-options", "Missing X-Frame-Options header",
             "X-Frame-Options prevents clickjacking by controlling iframe embedding.",
             "low", "A05:2021 - Security Misconfiguration", "CWE-1021"),
            ("x-content-type-options", "Missing X-Content-Type-Options header",
             "This header prevents MIME-type sniffing attacks.",
             "low", "A05:2021 - Security Misconfiguration", "CWE-16"),
            ("referrer-policy", "Missing Referrer-Policy header",
             "Controls how much referrer information is shared with requests.",
             "low", "A05:2021 - Security Misconfiguration", "CWE-200"),
            ("permissions-policy", "Missing Permissions-Policy header",
             "Controls which browser features the site can use (camera, microphone, etc.).",
             "info", "A05:2021 - Security Misconfiguration", "CWE-693"),
        ]

        for header_name, title, description, severity, owasp, cwe in checks:
            if header_name not in headers:
                findings.append(
                    ProbeFinding(
                        title=title, description=description,
                        category="security-headers", severity=severity,
                        url_tested=self.target_url, method="GET",
                        response_summary=f"Header '{header_name}' not present in response",
                        owasp_category=owasp, cwe_id=cwe, confidence=0.95,
                    )
                )
        return findings

    async def test_sensitive_exposure(
        self, client: httpx.AsyncClient, disallowed: set[str]
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []

        async def check_path(path: str) -> ProbeFinding | None:
            if self._is_disallowed(path, disallowed):
                return None
            url = f"{self.base_url}{path}"
            resp = await self._rate_limited_get(client, url)
            if not resp or resp.status_code != 200:
                return None
            if len(resp.content) < 10:
                return None
            return ProbeFinding(
                title=f"Sensitive file exposed: {path}",
                description=f"The path {path} returned a 200 response, potentially exposing sensitive data.",
                category="sensitive-exposure",
                severity="high" if path in ("/.env", "/.git/config", "/wp-config.php.bak") else "medium",
                url_tested=url, method="GET",
                response_summary=f"HTTP 200, {len(resp.content)} bytes",
                evidence=resp.text[:200] if len(resp.text) > 0 else "",
                owasp_category="A02:2021 - Cryptographic Failures",
                cwe_id="CWE-538", confidence=0.85,
            )

        tasks = [check_path(p) for p in SENSITIVE_PATHS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, ProbeFinding):
                findings.append(r)
        return findings

    async def test_cookie_security(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        resp = await self._rate_limited_get(client, self.target_url)
        if not resp:
            return findings

        cookies = resp.headers.get_list("set-cookie")
        for cookie_str in cookies:
            cookie_lower = cookie_str.lower()
            cookie_name = cookie_str.split("=")[0].strip() if "=" in cookie_str else "unknown"

            if "httponly" not in cookie_lower:
                findings.append(ProbeFinding(
                    title=f"Cookie '{cookie_name}' missing HttpOnly flag",
                    description="Cookies without HttpOnly can be accessed via JavaScript, increasing XSS risk.",
                    category="cookie-security", severity="medium",
                    url_tested=self.target_url, method="GET",
                    evidence=cookie_str[:100],
                    owasp_category="A05:2021 - Security Misconfiguration",
                    cwe_id="CWE-1004", confidence=0.9,
                ))
            if "secure" not in cookie_lower:
                findings.append(ProbeFinding(
                    title=f"Cookie '{cookie_name}' missing Secure flag",
                    description="Cookies without the Secure flag can be sent over unencrypted HTTP connections.",
                    category="cookie-security", severity="medium",
                    url_tested=self.target_url, method="GET",
                    evidence=cookie_str[:100],
                    owasp_category="A05:2021 - Security Misconfiguration",
                    cwe_id="CWE-614", confidence=0.9,
                ))
            if "samesite" not in cookie_lower:
                findings.append(ProbeFinding(
                    title=f"Cookie '{cookie_name}' missing SameSite attribute",
                    description="Cookies without SameSite may be vulnerable to CSRF attacks.",
                    category="cookie-security", severity="low",
                    url_tested=self.target_url, method="GET",
                    evidence=cookie_str[:100],
                    owasp_category="A01:2021 - Broken Access Control",
                    cwe_id="CWE-352", confidence=0.8,
                ))
        return findings

    async def test_ssl_tls(self) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        parsed = urlparse(self.target_url)

        if parsed.scheme != "https":
            findings.append(ProbeFinding(
                title="Site not using HTTPS",
                description="The target URL uses HTTP instead of HTTPS. All traffic is unencrypted.",
                category="ssl-tls", severity="high",
                url_tested=self.target_url,
                owasp_category="A02:2021 - Cryptographic Failures",
                cwe_id="CWE-319", confidence=1.0,
            ))
            return findings

        loop = asyncio.get_running_loop()
        try:
            cert_info = await loop.run_in_executor(None, self._get_cert_info)
            if cert_info:
                not_after = cert_info.get("notAfter")
                if not_after:
                    from email.utils import parsedate_to_datetime
                    expiry = parsedate_to_datetime(not_after)
                    now = datetime.now(timezone.utc)
                    days_left = (expiry - now).days
                    if days_left < 0:
                        findings.append(ProbeFinding(
                            title="SSL certificate has expired",
                            description=f"Certificate expired {abs(days_left)} days ago.",
                            category="ssl-tls", severity="critical",
                            url_tested=self.target_url,
                            evidence=f"Expiry: {not_after}",
                            owasp_category="A02:2021 - Cryptographic Failures",
                            cwe_id="CWE-295", confidence=1.0,
                        ))
                    elif days_left < 30:
                        findings.append(ProbeFinding(
                            title="SSL certificate expiring soon",
                            description=f"Certificate expires in {days_left} days.",
                            category="ssl-tls", severity="low",
                            url_tested=self.target_url,
                            evidence=f"Expiry: {not_after}",
                            owasp_category="A02:2021 - Cryptographic Failures",
                            cwe_id="CWE-295", confidence=1.0,
                        ))
        except Exception as exc:
            findings.append(ProbeFinding(
                title="SSL certificate validation failed",
                description=f"Could not validate SSL certificate: {exc}",
                category="ssl-tls", severity="high",
                url_tested=self.target_url,
                owasp_category="A02:2021 - Cryptographic Failures",
                cwe_id="CWE-295", confidence=0.7,
            ))
        return findings

    def _get_cert_info(self) -> dict | None:
        parsed = urlparse(self.target_url)
        hostname = parsed.hostname or ""
        port = parsed.port or 443
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                return ssock.getpeercert()  # type: ignore[return-value]

    async def test_misconfiguration(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []

        resp = await self._rate_limited_get(client, f"{self.base_url}/")
        if resp and resp.status_code == 200:
            body_lower = resp.text.lower()
            if "index of /" in body_lower or "<title>directory listing" in body_lower:
                findings.append(ProbeFinding(
                    title="Directory listing enabled",
                    description="The server exposes directory listings, potentially revealing file structure.",
                    category="misconfiguration", severity="medium",
                    url_tested=f"{self.base_url}/", method="GET",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    cwe_id="CWE-548", confidence=0.9,
                ))

        resp = await self._rate_limited_get(
            client, self.target_url,
            headers={"Origin": "https://evil.example.com"},
        )
        if resp:
            acao = resp.headers.get("access-control-allow-origin", "")
            if acao == "*":
                findings.append(ProbeFinding(
                    title="CORS allows all origins (wildcard *)",
                    description="Access-Control-Allow-Origin: * allows any site to make cross-origin requests.",
                    category="misconfiguration", severity="medium",
                    url_tested=self.target_url, method="GET",
                    evidence=f"Access-Control-Allow-Origin: {acao}",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    cwe_id="CWE-942", confidence=0.95,
                ))
            elif acao == "https://evil.example.com":
                findings.append(ProbeFinding(
                    title="CORS reflects arbitrary origin",
                    description="The server reflects the Origin header in Access-Control-Allow-Origin.",
                    category="misconfiguration", severity="high",
                    url_tested=self.target_url, method="GET",
                    evidence=f"Access-Control-Allow-Origin: {acao}",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    cwe_id="CWE-942", confidence=0.9,
                ))

        resp = await self._rate_limited_get(
            client, f"{self.base_url}/vibe2prod-nonexistent-test-page-12345"
        )
        if resp and resp.status_code >= 400:
            body_lower = resp.text.lower()
            if any(p in body_lower for p in ["stack trace", "traceback", "exception", "debug =", "server_software"]):
                findings.append(ProbeFinding(
                    title="Verbose error pages enabled",
                    description="Error responses contain debug information.",
                    category="misconfiguration", severity="medium",
                    url_tested=f"{self.base_url}/vibe2prod-nonexistent-test-page-12345",
                    method="GET", evidence=resp.text[:200],
                    owasp_category="A05:2021 - Security Misconfiguration",
                    cwe_id="CWE-209", confidence=0.8,
                ))
        return findings

    async def test_injection(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        parsed = urlparse(self.target_url)
        params = parse_qs(parsed.query)

        if not params:
            test_url = f"{self.target_url}?id=1"
            params = {"id": ["1"]}
            parsed = urlparse(test_url)

        payloads = ["'", '"', "1 OR 1=1", "1' OR '1'='1"]

        for param_name in list(params.keys())[:3]:
            for payload in payloads:
                test_params = dict(params)
                test_params[param_name] = [payload]
                query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=query))

                resp = await self._rate_limited_get(client, test_url)
                if not resp:
                    continue

                body_lower = resp.text.lower()
                for pattern in SQL_ERROR_PATTERNS:
                    if pattern in body_lower:
                        findings.append(ProbeFinding(
                            title=f"Potential SQL injection in parameter '{param_name}'",
                            description=f"SQL error pattern detected when injecting '{payload}' into '{param_name}'.",
                            category="injection", severity="critical",
                            url_tested=test_url, method="GET",
                            request_summary=f"Injected '{payload}' into '{param_name}'",
                            evidence=body_lower[body_lower.index(pattern):body_lower.index(pattern) + 100],
                            owasp_category="A03:2021 - Injection",
                            cwe_id="CWE-89", confidence=0.75,
                        ))
                        break
        return findings

    async def test_xss(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        parsed = urlparse(self.target_url)
        params = parse_qs(parsed.query)

        if not params:
            test_url = f"{self.target_url}?q=test"
            params = {"q": ["test"]}
            parsed = urlparse(test_url)

        for param_name in list(params.keys())[:3]:
            for payload in XSS_PAYLOADS:
                test_params = dict(params)
                test_params[param_name] = [payload]
                query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=query))

                resp = await self._rate_limited_get(client, test_url)
                if not resp:
                    continue

                if payload in resp.text:
                    findings.append(ProbeFinding(
                        title=f"Potential reflected XSS in parameter '{param_name}'",
                        description=f"XSS payload reflected unescaped in response body for '{param_name}'.",
                        category="xss", severity="high",
                        url_tested=test_url, method="GET",
                        request_summary=f"Injected XSS payload into '{param_name}'",
                        evidence=payload,
                        owasp_category="A03:2021 - Injection",
                        cwe_id="CWE-79", confidence=0.7,
                    ))
                    break
        return findings

    async def test_csrf(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        resp = await self._rate_limited_get(client, self.target_url)
        if not resp or resp.status_code != 200:
            return findings

        body_lower = resp.text.lower()
        if "<form" in body_lower:
            has_csrf = any(
                token in body_lower
                for token in ["csrf", "_token", "authenticity_token", "csrfmiddlewaretoken", "__requestverificationtoken"]
            )
            if not has_csrf:
                findings.append(ProbeFinding(
                    title="Forms without CSRF token detected",
                    description="HTML forms found without apparent CSRF protection tokens.",
                    category="csrf", severity="medium",
                    url_tested=self.target_url, method="GET",
                    owasp_category="A01:2021 - Broken Access Control",
                    cwe_id="CWE-352", confidence=0.6,
                ))
        return findings

    async def test_open_redirects(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        evil_url = "https://evil.example.com"

        for param in REDIRECT_PARAMS:
            test_url = f"{self.base_url}/?{param}={evil_url}"
            try:
                async with self._semaphore:
                    resp = await client.get(
                        test_url, follow_redirects=False,
                        timeout=settings.probe_request_timeout_seconds,
                    )
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location", "")
                    if "evil.example.com" in location:
                        findings.append(ProbeFinding(
                            title=f"Open redirect via '{param}' parameter",
                            description=f"The application redirects to an external URL when '{param}' is set to an external domain.",
                            category="open-redirect", severity="medium",
                            url_tested=test_url, method="GET",
                            evidence=f"Location: {location}",
                            owasp_category="A10:2021 - Server-Side Request Forgery",
                            cwe_id="CWE-601", confidence=0.85,
                        ))
            except httpx.HTTPError:
                continue
        return findings

    async def test_auth_issues(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []

        for path in AUTH_PATHS:
            url = f"{self.base_url}{path}"
            resp = await self._rate_limited_get(client, url)
            if not resp:
                continue

            if resp.status_code == 200:
                body_lower = resp.text.lower()
                if any(
                    indicator in body_lower
                    for indicator in ["password", "login", "sign in", "authenticate", "admin panel", "dashboard"]
                ):
                    findings.append(ProbeFinding(
                        title=f"Exposed admin/login endpoint: {path}",
                        description=f"An accessible login or admin page was found at {path}.",
                        category="auth-issues", severity="info",
                        url_tested=url, method="GET",
                        response_summary=f"HTTP {resp.status_code}",
                        owasp_category="A07:2021 - Identification and Authentication Failures",
                        cwe_id="CWE-200", confidence=0.6,
                    ))
        return findings
