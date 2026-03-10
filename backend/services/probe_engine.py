"""Security probe engine for live application testing.

Performs OWASP-aligned security tests against a target URL:
- Security headers analysis
- Sensitive file exposure
- Cookie security audit
- SSL/TLS certificate validation
- Server misconfiguration detection
- SQL/NoSQL injection probing
- Reflected XSS detection
- CSRF protection checks
- Open redirect testing
- Authentication issue detection
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

import httpx

from config import settings
from models.probe import ProbeFinding, ProbeResult

logger = logging.getLogger(__name__)

# Severity deductions for probe_score calculation
_SEVERITY_DEDUCTIONS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
    "info": 1,
}

# SQL error patterns that indicate injection vulnerability
_SQL_ERROR_PATTERNS = [
    "you have an error in your sql syntax",
    "warning: mysql",
    "unclosed quotation mark",
    "quoted string not properly terminated",
    "pg_query",
    "pg_exec",
    "syntax error at or near",
    "microsoft ole db provider for sql server",
    "ora-01756",
    "ora-00933",
    "sqlite3.operationalerror",
    "mongodb.*error",
    "unterminated string",
]

# XSS test payloads
_XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "';alert(1)//",
    "<svg onload=alert(1)>",
]

# Sensitive file paths to probe
_SENSITIVE_PATHS = [
    "/.env",
    "/.git/config",
    "/debug",
    "/admin",
    "/wp-admin",
    "/phpinfo.php",
    "/.DS_Store",
    "/server-status",
    "/elmah.axd",
    "/wp-config.php.bak",
]

# Open redirect parameter names
_REDIRECT_PARAMS = ["redirect", "url", "next", "return", "returnTo", "goto", "continue"]

# Common admin/login paths
_AUTH_PATHS = [
    "/admin",
    "/admin/login",
    "/login",
    "/wp-login.php",
    "/administrator",
    "/dashboard",
    "/api/admin",
    "/console",
]


class ProbeEngine:
    """Async security probe engine with rate limiting and scope enforcement."""

    def __init__(self, target_url: str, probe_type: str = "security"):
        self.target_url = str(target_url)
        self.probe_type = probe_type
        parsed = urlparse(self.target_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.target_domain = parsed.hostname or ""
        self._semaphore = asyncio.Semaphore(settings.probe_max_concurrent)
        self._findings: list[ProbeFinding] = []

    async def run(self) -> ProbeResult:
        """Execute all security test modules and compile results."""
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
            # Check robots.txt first
            disallowed = await self._check_robots_txt(client)

            tests = [
                self._test_security_headers(client),
                self._test_sensitive_exposure(client, disallowed),
                self._test_cookie_security(client),
                self._test_ssl_tls(),
                self._test_misconfiguration(client),
                self._test_injection(client),
                self._test_xss(client),
                self._test_csrf(client),
                self._test_open_redirects(client),
                self._test_auth_issues(client),
            ]

            results = await asyncio.gather(*tests, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("Probe test %d failed: %s", i, result)
                elif isinstance(result, list):
                    self._findings.extend(result)

        duration = time.monotonic() - start
        return self._compile_result(duration)

    def _compile_result(self, duration: float) -> ProbeResult:
        """Compute probe_score from findings and build the result."""
        score = 100
        for f in self._findings:
            score -= _SEVERITY_DEDUCTIONS.get(f.severity, 0)
        score = max(0, score)
        return ProbeResult(
            findings=self._findings,
            probe_score=score,
            duration_seconds=round(duration, 2),
        )

    async def _rate_limited_get(
        self, client: httpx.AsyncClient, url: str, **kwargs
    ) -> httpx.Response | None:
        """GET with semaphore-based rate limiting and scope enforcement."""
        parsed = urlparse(url)
        if parsed.hostname != self.target_domain:
            return None
        async with self._semaphore:
            try:
                return await client.get(url, **kwargs)
            except httpx.HTTPError as exc:
                logger.debug("Request to %s failed: %s", url, exc)
                return None

    async def _check_robots_txt(self, client: httpx.AsyncClient) -> set[str]:
        """Parse robots.txt to respect Disallow directives."""
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
        """Check if a path is blocked by robots.txt."""
        for d in disallowed:
            if path.startswith(d):
                return True
        return False

    # ------------------------------------------------------------------ #
    # Test 1: Security Headers
    # ------------------------------------------------------------------ #

    async def _test_security_headers(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        resp = await self._rate_limited_get(client, self.target_url)
        if not resp:
            return findings

        headers = {k.lower(): v for k, v in resp.headers.items()}

        checks = [
            (
                "content-security-policy",
                "Missing Content-Security-Policy header",
                "Content Security Policy (CSP) helps prevent XSS and data injection attacks.",
                "medium",
                "A5:2017 - Security Misconfiguration",
                "CWE-693",
            ),
            (
                "strict-transport-security",
                "Missing Strict-Transport-Security (HSTS) header",
                "HSTS enforces secure HTTPS connections, preventing protocol downgrade attacks.",
                "medium",
                "A5:2017 - Security Misconfiguration",
                "CWE-311",
            ),
            (
                "x-frame-options",
                "Missing X-Frame-Options header",
                "X-Frame-Options prevents clickjacking by controlling iframe embedding.",
                "low",
                "A5:2017 - Security Misconfiguration",
                "CWE-1021",
            ),
            (
                "x-content-type-options",
                "Missing X-Content-Type-Options header",
                "This header prevents MIME-type sniffing attacks.",
                "low",
                "A5:2017 - Security Misconfiguration",
                "CWE-16",
            ),
            (
                "referrer-policy",
                "Missing Referrer-Policy header",
                "Controls how much referrer information is shared with requests.",
                "low",
                "A5:2017 - Security Misconfiguration",
                "CWE-200",
            ),
            (
                "permissions-policy",
                "Missing Permissions-Policy header",
                "Controls which browser features the site can use (camera, microphone, etc.).",
                "info",
                "A5:2017 - Security Misconfiguration",
                "CWE-693",
            ),
        ]

        for header_name, title, description, severity, owasp, cwe in checks:
            if header_name not in headers:
                findings.append(
                    ProbeFinding(
                        title=title,
                        description=description,
                        category="security-headers",
                        severity=severity,
                        url_tested=self.target_url,
                        method="GET",
                        response_summary=f"Header '{header_name}' not present in response",
                        owasp_category=owasp,
                        cwe_id=cwe,
                        confidence=0.95,
                    )
                )

        return findings

    # ------------------------------------------------------------------ #
    # Test 2: Sensitive File Exposure
    # ------------------------------------------------------------------ #

    async def _test_sensitive_exposure(
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
            # Verify it's not just a generic 200 page (check content length > 0)
            if len(resp.content) < 10:
                return None
            return ProbeFinding(
                title=f"Sensitive file exposed: {path}",
                description=f"The path {path} returned a 200 response, potentially exposing sensitive data.",
                category="sensitive-exposure",
                severity="high" if path in ("/.env", "/.git/config", "/wp-config.php.bak") else "medium",
                url_tested=url,
                method="GET",
                response_summary=f"HTTP 200, {len(resp.content)} bytes",
                evidence=resp.text[:200] if len(resp.text) > 0 else "",
                owasp_category="A3:2017 - Sensitive Data Exposure",
                cwe_id="CWE-538",
                confidence=0.85,
            )

        tasks = [check_path(p) for p in _SENSITIVE_PATHS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, ProbeFinding):
                findings.append(r)
        return findings

    # ------------------------------------------------------------------ #
    # Test 3: Cookie Security
    # ------------------------------------------------------------------ #

    async def _test_cookie_security(
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
                findings.append(
                    ProbeFinding(
                        title=f"Cookie '{cookie_name}' missing HttpOnly flag",
                        description="Cookies without HttpOnly can be accessed via JavaScript, increasing XSS risk.",
                        category="cookie-security",
                        severity="medium",
                        url_tested=self.target_url,
                        method="GET",
                        evidence=cookie_str[:100],
                        owasp_category="A5:2017 - Security Misconfiguration",
                        cwe_id="CWE-1004",
                        confidence=0.9,
                    )
                )

            if "secure" not in cookie_lower:
                findings.append(
                    ProbeFinding(
                        title=f"Cookie '{cookie_name}' missing Secure flag",
                        description="Cookies without the Secure flag can be sent over unencrypted HTTP connections.",
                        category="cookie-security",
                        severity="medium",
                        url_tested=self.target_url,
                        method="GET",
                        evidence=cookie_str[:100],
                        owasp_category="A5:2017 - Security Misconfiguration",
                        cwe_id="CWE-614",
                        confidence=0.9,
                    )
                )

            if "samesite" not in cookie_lower:
                findings.append(
                    ProbeFinding(
                        title=f"Cookie '{cookie_name}' missing SameSite attribute",
                        description="Cookies without SameSite may be vulnerable to CSRF attacks.",
                        category="cookie-security",
                        severity="low",
                        url_tested=self.target_url,
                        method="GET",
                        evidence=cookie_str[:100],
                        owasp_category="A8:2017 - Cross-Site Request Forgery",
                        cwe_id="CWE-352",
                        confidence=0.8,
                    )
                )

        return findings

    # ------------------------------------------------------------------ #
    # Test 4: SSL/TLS Certificate
    # ------------------------------------------------------------------ #

    async def _test_ssl_tls(self) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        parsed = urlparse(self.target_url)

        if parsed.scheme != "https":
            findings.append(
                ProbeFinding(
                    title="Site not using HTTPS",
                    description="The target URL uses HTTP instead of HTTPS. All traffic is unencrypted.",
                    category="ssl-tls",
                    severity="high",
                    url_tested=self.target_url,
                    owasp_category="A3:2017 - Sensitive Data Exposure",
                    cwe_id="CWE-319",
                    confidence=1.0,
                )
            )
            return findings

        loop = asyncio.get_event_loop()
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
                        findings.append(
                            ProbeFinding(
                                title="SSL certificate has expired",
                                description=f"Certificate expired {abs(days_left)} days ago.",
                                category="ssl-tls",
                                severity="critical",
                                url_tested=self.target_url,
                                evidence=f"Expiry: {not_after}",
                                owasp_category="A3:2017 - Sensitive Data Exposure",
                                cwe_id="CWE-295",
                                confidence=1.0,
                            )
                        )
                    elif days_left < 30:
                        findings.append(
                            ProbeFinding(
                                title="SSL certificate expiring soon",
                                description=f"Certificate expires in {days_left} days.",
                                category="ssl-tls",
                                severity="low",
                                url_tested=self.target_url,
                                evidence=f"Expiry: {not_after}",
                                owasp_category="A3:2017 - Sensitive Data Exposure",
                                cwe_id="CWE-295",
                                confidence=1.0,
                            )
                        )
        except Exception as exc:
            findings.append(
                ProbeFinding(
                    title="SSL certificate validation failed",
                    description=f"Could not validate SSL certificate: {exc}",
                    category="ssl-tls",
                    severity="high",
                    url_tested=self.target_url,
                    owasp_category="A3:2017 - Sensitive Data Exposure",
                    cwe_id="CWE-295",
                    confidence=0.7,
                )
            )

        return findings

    def _get_cert_info(self) -> dict | None:
        """Fetch SSL certificate info synchronously (run in executor)."""
        parsed = urlparse(self.target_url)
        hostname = parsed.hostname or ""
        port = parsed.port or 443
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                return ssock.getpeercert()  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # Test 5: Server Misconfiguration
    # ------------------------------------------------------------------ #

    async def _test_misconfiguration(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []

        # Directory listing check
        resp = await self._rate_limited_get(client, f"{self.base_url}/")
        if resp and resp.status_code == 200:
            body_lower = resp.text.lower()
            if "index of /" in body_lower or "<title>directory listing" in body_lower:
                findings.append(
                    ProbeFinding(
                        title="Directory listing enabled",
                        description="The server exposes directory listings, potentially revealing file structure.",
                        category="misconfiguration",
                        severity="medium",
                        url_tested=f"{self.base_url}/",
                        method="GET",
                        owasp_category="A5:2017 - Security Misconfiguration",
                        cwe_id="CWE-548",
                        confidence=0.9,
                    )
                )

        # CORS wildcard check
        resp = await self._rate_limited_get(
            client,
            self.target_url,
            headers={"Origin": "https://evil.example.com"},
        )
        if resp:
            acao = resp.headers.get("access-control-allow-origin", "")
            if acao == "*":
                findings.append(
                    ProbeFinding(
                        title="CORS allows all origins (wildcard *)",
                        description="Access-Control-Allow-Origin: * allows any site to make cross-origin requests.",
                        category="misconfiguration",
                        severity="medium",
                        url_tested=self.target_url,
                        method="GET",
                        evidence=f"Access-Control-Allow-Origin: {acao}",
                        owasp_category="A5:2017 - Security Misconfiguration",
                        cwe_id="CWE-942",
                        confidence=0.95,
                    )
                )
            elif acao == "https://evil.example.com":
                findings.append(
                    ProbeFinding(
                        title="CORS reflects arbitrary origin",
                        description="The server reflects the Origin header in Access-Control-Allow-Origin, allowing any site to make requests.",
                        category="misconfiguration",
                        severity="high",
                        url_tested=self.target_url,
                        method="GET",
                        evidence=f"Access-Control-Allow-Origin: {acao}",
                        owasp_category="A5:2017 - Security Misconfiguration",
                        cwe_id="CWE-942",
                        confidence=0.9,
                    )
                )

        # Verbose error page check (trigger 404)
        resp = await self._rate_limited_get(
            client, f"{self.base_url}/vibe2prod-nonexistent-test-page-12345"
        )
        if resp and resp.status_code >= 400:
            body_lower = resp.text.lower()
            if any(
                p in body_lower
                for p in ["stack trace", "traceback", "exception", "debug =", "server_software"]
            ):
                findings.append(
                    ProbeFinding(
                        title="Verbose error pages enabled",
                        description="Error responses contain debug information (stack traces, server details).",
                        category="misconfiguration",
                        severity="medium",
                        url_tested=f"{self.base_url}/vibe2prod-nonexistent-test-page-12345",
                        method="GET",
                        evidence=resp.text[:200],
                        owasp_category="A5:2017 - Security Misconfiguration",
                        cwe_id="CWE-209",
                        confidence=0.8,
                    )
                )

        return findings

    # ------------------------------------------------------------------ #
    # Test 6: Injection (SQL / NoSQL)
    # ------------------------------------------------------------------ #

    async def _test_injection(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        parsed = urlparse(self.target_url)
        params = parse_qs(parsed.query)

        if not params:
            # If no params in URL, try a common pattern
            test_url = f"{self.target_url}?id=1"
            params = {"id": ["1"]}
            parsed = urlparse(test_url)

        payloads = ["'", '"', "1 OR 1=1", "1' OR '1'='1"]

        for param_name in list(params.keys())[:3]:  # Limit to first 3 params
            for payload in payloads:
                test_params = dict(params)
                test_params[param_name] = [payload]
                query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=query))

                resp = await self._rate_limited_get(client, test_url)
                if not resp:
                    continue

                body_lower = resp.text.lower()
                for pattern in _SQL_ERROR_PATTERNS:
                    if pattern in body_lower:
                        findings.append(
                            ProbeFinding(
                                title=f"Potential SQL injection in parameter '{param_name}'",
                                description=f"SQL error pattern detected when injecting '{payload}' into parameter '{param_name}'.",
                                category="injection",
                                severity="critical",
                                url_tested=test_url,
                                method="GET",
                                request_summary=f"Injected '{payload}' into '{param_name}'",
                                evidence=body_lower[body_lower.index(pattern) : body_lower.index(pattern) + 100],
                                owasp_category="A1:2017 - Injection",
                                cwe_id="CWE-89",
                                confidence=0.75,
                            )
                        )
                        break  # One finding per param+payload combo

        return findings

    # ------------------------------------------------------------------ #
    # Test 7: Reflected XSS
    # ------------------------------------------------------------------ #

    async def _test_xss(
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
            for payload in _XSS_PAYLOADS:
                test_params = dict(params)
                test_params[param_name] = [payload]
                query = urlencode(test_params, doseq=True)
                test_url = urlunparse(parsed._replace(query=query))

                resp = await self._rate_limited_get(client, test_url)
                if not resp:
                    continue

                # Check if payload appears unescaped in response
                if payload in resp.text:
                    findings.append(
                        ProbeFinding(
                            title=f"Potential reflected XSS in parameter '{param_name}'",
                            description=f"XSS payload reflected unescaped in response body for parameter '{param_name}'.",
                            category="xss",
                            severity="high",
                            url_tested=test_url,
                            method="GET",
                            request_summary=f"Injected XSS payload into '{param_name}'",
                            evidence=payload,
                            owasp_category="A7:2017 - Cross-Site Scripting (XSS)",
                            cwe_id="CWE-79",
                            confidence=0.7,
                        )
                    )
                    break  # One finding per param is enough

        return findings

    # ------------------------------------------------------------------ #
    # Test 8: CSRF Protection
    # ------------------------------------------------------------------ #

    async def _test_csrf(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        resp = await self._rate_limited_get(client, self.target_url)
        if not resp or resp.status_code != 200:
            return findings

        body_lower = resp.text.lower()

        # Check if there are forms without CSRF tokens
        if "<form" in body_lower:
            has_csrf = any(
                token in body_lower
                for token in ["csrf", "_token", "authenticity_token", "csrfmiddlewaretoken", "__requestverificationtoken"]
            )
            if not has_csrf:
                findings.append(
                    ProbeFinding(
                        title="Forms without CSRF token detected",
                        description="HTML forms found without apparent CSRF protection tokens.",
                        category="csrf",
                        severity="medium",
                        url_tested=self.target_url,
                        method="GET",
                        owasp_category="A8:2017 - Cross-Site Request Forgery",
                        cwe_id="CWE-352",
                        confidence=0.6,
                    )
                )

        return findings

    # ------------------------------------------------------------------ #
    # Test 9: Open Redirects
    # ------------------------------------------------------------------ #

    async def _test_open_redirects(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []
        evil_url = "https://evil.example.com"

        for param in _REDIRECT_PARAMS:
            test_url = f"{self.base_url}/?{param}={evil_url}"
            try:
                # Don't follow redirects for this test
                async with self._semaphore:
                    resp = await client.get(
                        test_url,
                        follow_redirects=False,
                        timeout=settings.probe_request_timeout_seconds,
                    )
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location", "")
                    if "evil.example.com" in location:
                        findings.append(
                            ProbeFinding(
                                title=f"Open redirect via '{param}' parameter",
                                description=f"The application redirects to an external URL when '{param}' parameter is set to an external domain.",
                                category="open-redirect",
                                severity="medium",
                                url_tested=test_url,
                                method="GET",
                                evidence=f"Location: {location}",
                                owasp_category="A10:2021 - Server-Side Request Forgery",
                                cwe_id="CWE-601",
                                confidence=0.85,
                            )
                        )
            except httpx.HTTPError:
                continue

        return findings

    # ------------------------------------------------------------------ #
    # Test 10: Auth Issues
    # ------------------------------------------------------------------ #

    async def _test_auth_issues(
        self, client: httpx.AsyncClient
    ) -> list[ProbeFinding]:
        findings: list[ProbeFinding] = []

        for path in _AUTH_PATHS:
            url = f"{self.base_url}{path}"
            resp = await self._rate_limited_get(client, url)
            if not resp:
                continue

            # 200 on admin/login pages is a finding worth noting
            if resp.status_code == 200:
                body_lower = resp.text.lower()
                # Check if it looks like a real admin/login page
                if any(
                    indicator in body_lower
                    for indicator in ["password", "login", "sign in", "authenticate", "admin panel", "dashboard"]
                ):
                    findings.append(
                        ProbeFinding(
                            title=f"Exposed admin/login endpoint: {path}",
                            description=f"An accessible login or admin page was found at {path}.",
                            category="auth-issues",
                            severity="info",
                            url_tested=url,
                            method="GET",
                            response_summary=f"HTTP {resp.status_code}",
                            owasp_category="A2:2017 - Broken Authentication",
                            cwe_id="CWE-200",
                            confidence=0.6,
                        )
                    )

        return findings
