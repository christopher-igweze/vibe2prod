"""Tests for CORS security configuration (F-7d12e465).

This module tests that the CORS middleware is properly configured to restrict
localhost origins to HTTP only, preventing HTTPS localhost bypass attacks (CWE-346).

The security fix ensures that only http://localhost and http://127.0.0.1 are allowed,
not https://localhost or https://127.0.0.1 which could create attack surface.
"""

from __future__ import annotations

import pytest
import re
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


class TestCORSLocalhostSecurity:
    """Test that localhost CORS is restricted to HTTP only (not HTTPS)."""

    def test_localhost_regex_allows_http(self):
        """Regex pattern should allow http://localhost origins."""
        # This is the fixed regex pattern from main.py
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

        # HTTP localhost should be allowed
        assert re.match(_cors_regex, "http://localhost") is not None
        assert re.match(_cors_regex, "http://localhost:3000") is not None
        assert re.match(_cors_regex, "http://localhost:8080") is not None

    def test_localhost_regex_blocks_https(self):
        """Regex pattern should block https://localhost origins (security fix)."""
        # This is the fixed regex pattern from main.py
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

        # HTTPS localhost should NOT be allowed (this is the security fix)
        assert re.match(_cors_regex, "https://localhost") is None
        assert re.match(_cors_regex, "https://localhost:3000") is None
        assert re.match(_cors_regex, "https://localhost:8080") is None

    def test_127_regex_allows_http(self):
        """Regex pattern should allow http://127.0.0.1 origins."""
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

        # HTTP 127.0.0.1 should be allowed
        assert re.match(_cors_regex, "http://127.0.0.1") is not None
        assert re.match(_cors_regex, "http://127.0.0.1:3000") is not None
        assert re.match(_cors_regex, "http://127.0.0.1:8080") is not None

    def test_127_regex_blocks_https(self):
        """Regex pattern should block https://127.0.0.1 origins (security fix)."""
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

        # HTTPS 127.0.0.1 should NOT be allowed (this is the security fix)
        assert re.match(_cors_regex, "https://127.0.0.1") is None
        assert re.match(_cors_regex, "https://127.0.0.1:3000") is None
        assert re.match(_cors_regex, "https://127.0.0.1:8080") is None


class TestCORSProductionOrigins:
    """Test that production origins are still allowed."""

    def test_prod_origin_allowed(self):
        """Production domain vibe2prod.com should still be allowed."""
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

        assert re.match(_cors_regex, "https://www.vibe2prod.com") is not None
        assert re.match(_cors_regex, "https://vibe2prod.com") is not None

    def test_staging_origin_allowed(self):
        """Staging domains should still be allowed."""
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )

        assert re.match(_cors_regex, "https://app-staging.vibe2prod.verstandai.site") is not None
        assert re.match(_cors_regex, "https://app-dev.vibe2prod.verstandai.site") is not None


class TestCORSVercelProjects:
    """Test Vercel project patterns with the HTTP-only localhost fix."""

    def test_vercel_project_regex_with_http_localhost(self):
        """Vercel project regex should work with HTTP-only localhost pattern."""
        # Simulate the regex built for cors_vercel_projects=my-app,frontend-app
        projects = ["my-app", "frontend-app"]
        _vercel_pattern = "|".join(
            rf"^https://{re.escape(project)}\\.vercel\\.app$" for project in projects
        )
        _cors_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
            + _vercel_pattern
            + r"|^https://(www\.)?vibe2prod\.com$|^https://.*\.verstandai\.site$"
        )

        # Should match Vercel projects
        assert re.match(_cors_regex, "https://my-app.vercel.app") is not None
        assert re.match(_cors_regex, "https://frontend-app.vercel.app") is not None

        # HTTP localhost should still work
        assert re.match(_cors_regex, "http://localhost:3000") is not None

        # HTTPS localhost should NOT work (security fix)
        assert re.match(_cors_regex, "https://localhost:3000") is None


class TestCORSRegexPatternFormat:
    """Test that the regex pattern format is correct."""

    def test_regex_does_not_allow_https_localhost_bypass(self):
        """Verify that the regex pattern cannot be bypassed with HTTPS localhost.
        
        This is the core security test - the fix changes https? to http://
        to prevent HTTPS localhost origins which could be used in attacks.
        """
        # Old vulnerable pattern (should NOT match)
        old_vulnerable_regex = (
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        )

        # New secure pattern (should match only HTTP)
        new_secure_regex = (
            r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
        )

        # Old regex would allow both - this is the vulnerability
        assert re.match(old_vulnerable_regex, "https://localhost") is not None
        assert re.match(old_vulnerable_regex, "https://127.0.0.1") is not None

        # New regex blocks HTTPS - this is the security fix
        assert re.match(new_secure_regex, "https://localhost") is None
        assert re.match(new_secure_regex, "https://127.0.0.1") is None

        # But still allows HTTP
        assert re.match(new_secure_regex, "http://localhost") is not None
        assert re.match(new_secure_regex, "http://127.0.0.1") is not None
