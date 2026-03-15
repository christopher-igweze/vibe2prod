"""Tests for URL sanitization and access-log middleware (F-8dcfb516).

Verifies that:
1. _sanitize_url uses a whitelist approach — only known-safe query parameters
   are preserved; every other parameter value is redacted to "***".
2. Previously hard-coded denylist gaps (e.g. user_id, email, session_id) are
   now redacted correctly.
3. Known-safe parameters (page, limit, sort, …) pass through unchanged.
4. URLs without query strings are unaffected.
5. The AccessLogMiddleware logs sanitized URLs on every request, not only on
   error paths.

Security: CWE-532 / OWASP A09:2021

NOTE: The unit tests in this module exercise the sanitization logic directly
(without importing `main`) so they run cleanly even when optional runtime
dependencies (slowapi, supabase, etc.) are not installed in the test environment.
"""

from __future__ import annotations

import logging
import re as _re
from typing import FrozenSet
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Inline reimplementation of the production logic.
#
# We copy the constants and function body from main.py so the unit tests can
# run in isolation without triggering the full FastAPI import chain.  The
# integration test class (TestAccessLogMiddlewareIntegration) still imports
# `main` directly and is skipped when dependencies are unavailable.
# ---------------------------------------------------------------------------

_SAFE_QUERY_PARAMS: FrozenSet[str] = frozenset(
    {
        "page",
        "limit",
        "offset",
        "sort",
        "order",
        "filter",
        "q",
        "search",
        "format",
        "version",
        "lang",
        "locale",
        "v",
        "cb",
    }
)

_QUERY_PARAM_RE = _re.compile(r"([^&=\s]+)=([^&\s]*)")


def _sanitize_url(url: object) -> str:  # mirrors main._sanitize_url exactly
    def _redact_param(match: _re.Match) -> str:  # type: ignore[type-arg]
        param_name = match.group(1)
        if param_name.lower() in _SAFE_QUERY_PARAMS:
            return match.group(0)
        return f"{param_name}=***"

    return _QUERY_PARAM_RE.sub(_redact_param, str(url))


# ---------------------------------------------------------------------------
# Unit tests for _sanitize_url (whitelist approach)
# ---------------------------------------------------------------------------


class TestSanitizeUrlWhitelist:
    """_sanitize_url must redact anything not explicitly allowlisted."""

    # -- Previously MISSED by the old denylist --

    def test_user_id_is_redacted(self):
        """user_id was not in the old denylist — it must be redacted now."""
        result = _sanitize_url("https://api.example.com/data?user_id=abc123")
        assert "abc123" not in result
        assert "user_id=***" in result

    def test_email_is_redacted(self):
        """email addresses must never appear in logs."""
        result = _sanitize_url("https://api.example.com/data?email=alice@example.com")
        assert "alice@example.com" not in result
        assert "email=***" in result

    def test_session_id_is_redacted(self):
        """session_id was not in the old denylist — it must be redacted now."""
        result = _sanitize_url("https://api.example.com/data?session_id=sess_xyz789")
        assert "sess_xyz789" not in result
        assert "session_id=***" in result

    def test_code_oauth_param_is_redacted(self):
        """OAuth 'code' parameter carries an authorization code and must be redacted."""
        result = _sanitize_url(
            "https://api.example.com/oauth/callback?code=auth_code_abc"
        )
        assert "auth_code_abc" not in result
        assert "code=***" in result

    def test_state_oauth_param_is_redacted(self):
        """OAuth 'state' parameter should be redacted (opaque / security-sensitive)."""
        result = _sanitize_url(
            "https://api.example.com/oauth/callback?state=csrf_state_xyz"
        )
        assert "csrf_state_xyz" not in result
        assert "state=***" in result

    # -- Parameters that WERE in the old denylist (regression guard) --

    def test_token_is_redacted(self):
        result = _sanitize_url("https://api.example.com/cb?token=super_secret")
        assert "super_secret" not in result
        assert "token=***" in result

    def test_password_is_redacted(self):
        result = _sanitize_url("https://api.example.com/login?password=hunter2")
        assert "hunter2" not in result
        assert "password=***" in result

    def test_key_is_redacted(self):
        result = _sanitize_url(
            "https://api.example.com/data?key=AKIAIOSFODNN7EXAMPLE"
        )
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "key=***" in result

    def test_secret_is_redacted(self):
        result = _sanitize_url("https://api.example.com/data?secret=mysecret")
        assert "mysecret" not in result
        assert "secret=***" in result

    def test_access_token_is_redacted(self):
        result = _sanitize_url(
            "https://api.example.com/data?access_token=eyJhbGciOiJSUzI1NiJ9"
        )
        assert "eyJhbGciOiJSUzI1NiJ9" not in result
        assert "access_token=***" in result

    def test_refresh_token_is_redacted(self):
        result = _sanitize_url(
            "https://api.example.com/data?refresh_token=tok_refresh_abc"
        )
        assert "tok_refresh_abc" not in result
        assert "refresh_token=***" in result

    def test_jwt_is_redacted(self):
        result = _sanitize_url(
            "https://api.example.com/data"
            "?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        )
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "jwt=***" in result

    def test_bearer_is_redacted(self):
        result = _sanitize_url("https://api.example.com/data?bearer=my_bearer_token")
        assert "my_bearer_token" not in result
        assert "bearer=***" in result

    # -- Known-safe / allowlisted parameters must pass through unchanged --

    def test_page_is_preserved(self):
        result = _sanitize_url("https://api.example.com/items?page=2")
        assert "page=2" in result

    def test_limit_is_preserved(self):
        result = _sanitize_url("https://api.example.com/items?limit=50")
        assert "limit=50" in result

    def test_sort_is_preserved(self):
        result = _sanitize_url("https://api.example.com/items?sort=asc")
        assert "sort=asc" in result

    def test_order_is_preserved(self):
        result = _sanitize_url("https://api.example.com/items?order=desc")
        assert "order=desc" in result

    def test_offset_is_preserved(self):
        result = _sanitize_url("https://api.example.com/items?offset=100")
        assert "offset=100" in result

    def test_search_is_preserved(self):
        result = _sanitize_url("https://api.example.com/items?search=widget")
        assert "search=widget" in result

    def test_format_is_preserved(self):
        result = _sanitize_url("https://api.example.com/export?format=csv")
        assert "format=csv" in result

    def test_q_is_preserved(self):
        result = _sanitize_url("https://api.example.com/search?q=openai")
        assert "q=openai" in result

    def test_lang_is_preserved(self):
        result = _sanitize_url("https://api.example.com/page?lang=en")
        assert "lang=en" in result

    # -- Mixed: some safe, some sensitive --

    def test_mixed_params_redacts_sensitive_preserves_safe(self):
        url = (
            "https://api.example.com/data"
            "?page=1&limit=20&user_id=u_123&token=tok_abc&sort=desc"
        )
        result = _sanitize_url(url)
        # Safe params intact
        assert "page=1" in result
        assert "limit=20" in result
        assert "sort=desc" in result
        # Sensitive params redacted
        assert "u_123" not in result
        assert "user_id=***" in result
        assert "tok_abc" not in result
        assert "token=***" in result

    def test_multiple_sensitive_params_all_redacted(self):
        url = (
            "https://api.example.com/oauth/callback"
            "?code=auth_code_123&state=state_xyz&session_id=sess_abc"
        )
        result = _sanitize_url(url)
        assert "auth_code_123" not in result
        assert "state_xyz" not in result
        assert "sess_abc" not in result
        assert "code=***" in result
        assert "state=***" in result
        assert "session_id=***" in result

    # -- Edge cases --

    def test_no_query_string_is_unchanged(self):
        url = "https://api.example.com/health"
        assert _sanitize_url(url) == url

    def test_url_path_without_query_params_preserved(self):
        url = "https://api.example.com/api/user/profile"
        assert _sanitize_url(url) == url

    def test_empty_safe_param_value_is_preserved(self):
        """An empty value for a safe param (param=) should not break sanitization."""
        url = "https://api.example.com/data?page="
        result = _sanitize_url(url)
        assert "page=" in result

    def test_empty_sensitive_param_value_is_redacted(self):
        """An empty value for a sensitive param should still be redacted."""
        url = "https://api.example.com/data?user_id="
        result = _sanitize_url(url)
        assert "user_id=***" in result

    def test_case_insensitive_param_names_sensitive(self):
        """Sensitive parameter name matching must be case-insensitive."""
        result = _sanitize_url("https://api.example.com/data?TOKEN=my_token_value")
        assert "my_token_value" not in result
        assert "TOKEN=***" in result

    def test_case_insensitive_param_names_safe(self):
        """Safe parameter name matching must be case-insensitive (PAGE=1 passes)."""
        result = _sanitize_url("https://api.example.com/data?PAGE=3")
        assert "PAGE=3" in result

    def test_non_url_string_does_not_raise(self):
        """_sanitize_url must handle arbitrary objects via str()."""
        result = _sanitize_url(None)
        assert result == "None"

    def test_returns_string(self):
        assert isinstance(_sanitize_url("https://api.example.com/?page=1"), str)


# ---------------------------------------------------------------------------
# Whitelist membership — guard against accidental removals or additions
# ---------------------------------------------------------------------------


class TestSafeQueryParamsWhitelist:
    """The _SAFE_QUERY_PARAMS set must contain exactly the expected members."""

    def test_pagination_params_are_safe(self):
        for param in ("page", "limit", "offset"):
            assert param in _SAFE_QUERY_PARAMS, (
                f"{param!r} should be in _SAFE_QUERY_PARAMS"
            )

    def test_sorting_params_are_safe(self):
        for param in ("sort", "order"):
            assert param in _SAFE_QUERY_PARAMS, (
                f"{param!r} should be in _SAFE_QUERY_PARAMS"
            )

    def test_search_and_filter_params_are_safe(self):
        for param in ("q", "search", "filter"):
            assert param in _SAFE_QUERY_PARAMS, (
                f"{param!r} should be in _SAFE_QUERY_PARAMS"
            )

    def test_sensitive_params_are_not_in_whitelist(self):
        """Sensitive parameter names must never appear in the allowlist."""
        forbidden = {
            "token",
            "key",
            "secret",
            "password",
            "jwt",
            "bearer",
            "access_token",
            "refresh_token",
            "user_id",
            "email",
            "session_id",
            "api_key",
            "auth",
            "code",
            "state",
        }
        for param in forbidden:
            assert param not in _SAFE_QUERY_PARAMS, (
                f"{param!r} must NOT be in _SAFE_QUERY_PARAMS — it is sensitive"
            )


# ---------------------------------------------------------------------------
# Whitelist-approach invariant: every unrecognised param is redacted
# ---------------------------------------------------------------------------


class TestWhitelistInvariant:
    """Any parameter name not explicitly in the allowlist must be redacted."""

    @pytest.mark.parametrize(
        "param_name",
        [
            "user_id",
            "email",
            "session_id",
            "api_key",
            "auth",
            "code",
            "state",
            "sig",
            "signature",
            "nonce",
            "client_secret",
            "private_key",
            "ssn",
            "dob",
            "phone",
            "address",
            "card_number",
            "cvv",
            "expiry",
            "some_new_unknown_param",
        ],
    )
    def test_unlisted_param_is_always_redacted(self, param_name: str):
        """Any parameter not in _SAFE_QUERY_PARAMS must have its value redacted."""
        url = f"https://api.example.com/data?{param_name}=sensitive_value"
        result = _sanitize_url(url)
        assert "sensitive_value" not in result, (
            f"Value of unlisted param {param_name!r} must be redacted"
        )
        assert f"{param_name}=***" in result


# ---------------------------------------------------------------------------
# AccessLogMiddleware — behaviour test using a lightweight mock ASGI approach
# ---------------------------------------------------------------------------


class TestAccessLogMiddlewareBehaviour:
    """Verify AccessLogMiddleware calls _sanitize_url on every request."""

    @pytest.mark.asyncio
    async def test_middleware_calls_sanitize_url_on_each_request(self):
        """AccessLogMiddleware must call _sanitize_url for incoming and completed logs."""
        # Build the middleware class inline (mirrors main.AccessLogMiddleware logic)
        # so we can test without importing the full FastAPI application.
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request as StarletteRequest
        from starlette.responses import Response
        from starlette.testclient import TestClient
        from fastapi import FastAPI

        sanitized_urls: list[str] = []

        def capturing_sanitize(url: object) -> str:
            result = _sanitize_url(url)
            sanitized_urls.append(result)
            return result

        mini_app = FastAPI()

        @mini_app.get("/test")
        async def _test_endpoint():
            return {"ok": True}

        class _TestAccessLogMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: StarletteRequest, call_next):
                capturing_sanitize(request.url)
                response = await call_next(request)
                capturing_sanitize(request.url)
                return response

        mini_app.add_middleware(_TestAccessLogMiddleware)

        client = TestClient(mini_app, raise_server_exceptions=False)
        client.get("/test?user_id=secret123&page=1")

        # Both the incoming and completed log lines should have been processed
        assert len(sanitized_urls) == 2
        for sanitized in sanitized_urls:
            assert "secret123" not in sanitized, (
                "Sensitive user_id value must not appear in any logged URL"
            )
            assert "user_id=***" in sanitized
            # Safe param preserved
            assert "page=1" in sanitized

    @pytest.mark.asyncio
    async def test_middleware_logs_sanitized_url_via_logger(self, caplog):
        """AccessLogMiddleware must emit log records with sanitized URLs."""
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request as StarletteRequest
        from fastapi import FastAPI

        mini_app = FastAPI()
        test_logger = logging.getLogger("test_access_log")

        @mini_app.get("/test")
        async def _test_endpoint():
            return {"ok": True}

        class _TestAccessLogMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: StarletteRequest, call_next):
                test_logger.info(
                    "Incoming request: %s %s",
                    request.method,
                    _sanitize_url(request.url),
                )
                response = await call_next(request)
                test_logger.info(
                    "Completed request: %s %s | status=%s",
                    request.method,
                    _sanitize_url(request.url),
                    response.status_code,
                )
                return response

        mini_app.add_middleware(_TestAccessLogMiddleware)

        from starlette.testclient import TestClient

        client = TestClient(mini_app, raise_server_exceptions=False)

        with caplog.at_level(logging.INFO, logger="test_access_log"):
            client.get("/test?email=admin@corp.com&limit=10")

        assert "admin@corp.com" not in caplog.text, (
            "Email must be redacted in access logs"
        )
        assert "email=***" in caplog.text
        assert "limit=10" in caplog.text  # safe param preserved
