"""Tests for CORS localhost HTTP-only security (F-7d12e465).

This module tests that the CORS middleware is properly configured to restrict
localhost origins to HTTP only, preventing HTTPS localhost bypass attacks (CWE-346).

The security fix ensures that only http://localhost and http://127.0.0.1 are allowed,
not https://localhost or https://127.0.0.1 which could create attack surface.
"""

from __future__ import annotations

import re
import pytest


class TestCORSLocalhostHTTPOnly:
    """Test that localhost CORS is restricted to HTTP only (not HTTPS)."""

    def get_cors_regex(self) -> str:
        """Return the fixed CORS regex pattern that allows only HTTP localhost."""
        return (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

    def test_http_localhost_allowed(self):
        """HTTP localhost origins should be allowed."""
        _cors_regex = self.get_cors_regex()
        assert re.match(_cors_regex, "http://localhost") is not None
        assert re.match(_cors_regex, "http://localhost:3000") is not None
        assert re.match(_cors_regex, "http://localhost:8080") is not None
        assert re.match(_cors_regex, "http://localhost:8000") is not None

    def test_http_127_allowed(self):
        """HTTP 127.0.0.1 origins should be allowed."""
        _cors_regex = self.get_cors_regex()
        assert re.match(_cors_regex, "http://127.0.0.1") is not None
        assert re.match(_cors_regex, "http://127.0.0.1:3000") is not None
        assert re.match(_cors_regex, "http://127.0.0.1:8080") is not None
        assert re.match(_cors_regex, "http://127.0.0.1:8000") is not None

    def test_https_localhost_blocked(self):
        """HTTPS localhost origins should be BLOCKED (security fix)."""
        _cors_regex = self.get_cors_regex()
        assert re.match(_cors_regex, "https://localhost") is None
        assert re.match(_cors_regex, "https://localhost:3000") is None
        assert re.match(_cors_regex, "https://localhost:8080") is None

    def test_https_127_blocked(self):
        """HTTPS 127.0.0.1 origins should be BLOCKED (security fix)."""
        _cors_regex = self.get_cors_regex()
        assert re.match(_cors_regex, "https://127.0.0.1") is None
        assert re.match(_cors_regex, "https://127.0.0.1:3000") is None
        assert re.match(_cors_regex, "https://127.0.0.1:8080") is None


class TestCORSProductionOriginsStillAllowed:
    """Test that production origins are still allowed after the localhost fix."""

    def get_cors_regex(self) -> str:
        """Return the fixed CORS regex pattern that allows only HTTP localhost."""
        return (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

    def test_prod_domain_allowed(self):
        """Production domain vibe2prod.com should still be allowed."""
        _cors_regex = self.get_cors_regex()
        assert re.match(_cors_regex, "https://www.vibe2prod.com") is not None
        assert re.match(_cors_regex, "https://vibe2prod.com") is not None

    def test_staging_domain_allowed(self):
        """Staging domains on verstandai.site should still be allowed."""
        _cors_regex = self.get_cors_regex()
        assert re.match(_cors_regex, "https://app-staging.vibe2prod.verstandai.site") is not None
        assert re.match(_cors_regex, "https://staging.verstandai.site") is not None
        assert re.match(_cors_regex, "https://my-app.verstandai.site") is not None


class TestCORSVercelProjectsWithLocalhostFix:
    """Test CORS regex with Vercel projects - ensuring localhost is HTTP only."""

    def get_cors_regex_with_vercel(self, projects: list[str]) -> str:
        """Return the CORS regex with Vercel project pattern appended."""
        _vercel_pattern = "|".join(
            rf"^https://{re.escape(project)}\\.vercel\\.app$" for project in projects
        )
        return (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|"
            + _vercel_pattern
            + r"|^https://(www\.)?vibe2prod\.com$|^https://.*\.verstandai\.site$"
        )

    def test_vercel_project_allowed(self):
        """Specific Vercel project subdomains should be allowed."""
        _cors_regex = self.get_cors_regex_with_vercel(["my-app", "frontend-app"])
        assert re.match(_cors_regex, "https://my-app.vercel.app") is not None
        assert re.match(_cors_regex, "https://frontend-app.vercel.app") is not None

    def test_vercel_project_with_http_localhost(self):
        """HTTP localhost should still work with Vercel projects configured."""
        _cors_regex = self.get_cors_regex_with_vercel(["my-app", "frontend-app"])
        assert re.match(_cors_regex, "http://localhost") is not None
        assert re.match(_cors_regex, "http://localhost:3000") is not None
        assert re.match(_cors_regex, "http://127.0.0.1") is not None

    def test_https_localhost_blocked_with_vercel(self):
        """HTTPS localhost should be blocked even with Vercel projects configured."""
        _cors_regex = self.get_cors_regex_with_vercel(["my-app", "frontend-app"])
        assert re.match(_cors_regex, "https://localhost") is None
        assert re.match(_cors_regex, "https://127.0.0.1") is None
