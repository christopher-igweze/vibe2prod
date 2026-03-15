"""Tests for the safe_request global exception-handling wrapper.

These tests verify that SharedHttpClient.safe_request (and the module-level
safe_request convenience alias) correctly catches common network-level
exceptions from httpx and converts them into structured FastAPI HTTPExceptions
with the appropriate HTTP status codes and log output.

Test Location: backend/tests/test_http_client_safe_request.py
Project: services/http_client.py
Framework: pytest / pytest-asyncio
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Import helpers – support both direct and package-relative imports so the
# tests work regardless of how pytest is invoked.
# ---------------------------------------------------------------------------
try:
    from services.http_client import SharedHttpClient, get_http_client, safe_request, shared_client
except ImportError:
    try:
        from backend.services.http_client import (
            SharedHttpClient,
            get_http_client,
            safe_request,
            shared_client,
        )
    except ImportError:
        import sys

        backend_path = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_path))
        from services.http_client import (
            SharedHttpClient,
            get_http_client,
            safe_request,
            shared_client,
        )

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> SharedHttpClient:
    """Return a fresh SharedHttpClient for isolation between tests."""
    return get_http_client()


# ---------------------------------------------------------------------------
# Unit tests for SharedHttpClient.safe_request
# ---------------------------------------------------------------------------


class TestSafeRequestExists:
    """Verify safe_request is present and callable."""

    def test_shared_client_has_safe_request_method(self):
        """SharedHttpClient exposes a safe_request method."""
        assert hasattr(shared_client, "safe_request")
        assert callable(shared_client.safe_request)

    def test_module_level_safe_request_is_callable(self):
        """The module-level safe_request function is importable and callable."""
        assert callable(safe_request)

    def test_safe_request_is_coroutine_function(self):
        """safe_request must be awaitable (async)."""
        import inspect

        assert inspect.iscoroutinefunction(shared_client.safe_request)
        assert inspect.iscoroutinefunction(safe_request)


class TestSafeRequestSuccessPath:
    """safe_request returns the response unchanged on success."""

    @pytest.mark.asyncio
    async def test_returns_response_on_success(self):
        """A successful httpx.Response is returned as-is."""
        client = _make_client()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.safe_request("GET", "https://api.example.com/ok")

        assert result is mock_response
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_passes_method_and_url_through(self):
        """safe_request forwards the method and URL to the underlying request."""
        client = _make_client()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201

        with patch.object(client, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await client.safe_request("POST", "https://api.example.com/items", json={"key": "value"})

        mock_req.assert_called_once_with("POST", "https://api.example.com/items", json={"key": "value"})

    @pytest.mark.asyncio
    async def test_passes_extra_kwargs_to_request(self):
        """Keyword arguments such as headers, params, timeout are forwarded."""
        client = _make_client()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        headers = {"Authorization": "Bearer token"}
        params = {"page": 1}

        with patch.object(client, "request", new_callable=AsyncMock, return_value=mock_response) as mock_req:
            await client.safe_request(
                "GET",
                "https://api.example.com/data",
                headers=headers,
                params=params,
            )

        mock_req.assert_called_once_with(
            "GET",
            "https://api.example.com/data",
            headers=headers,
            params=params,
        )

    @pytest.mark.asyncio
    async def test_does_not_suppress_http_error_status_codes(self):
        """HTTP-level 4xx/5xx responses are returned, not caught – callers decide."""
        client = _make_client()
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404  # HTTP error, not a network error

        with patch.object(client, "request", new_callable=AsyncMock, return_value=mock_response):
            result = await client.safe_request("GET", "https://api.example.com/missing")

        # Should come back as a normal response – not converted to HTTPException
        assert result.status_code == 404


# ---------------------------------------------------------------------------
# Timeout → 504
# ---------------------------------------------------------------------------


class TestSafeRequestTimeoutException:
    """httpx.TimeoutException → HTTPException(504)."""

    @pytest.mark.asyncio
    async def test_timeout_raises_http_exception_504(self):
        """TimeoutException is converted to HTTPException with status 504."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://slow.example.com/data")

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_timeout_detail_message(self):
        """504 HTTPException carries a human-readable detail string."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("read timeout"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("POST", "https://slow.example.com/submit")

        assert "timed out" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_timeout_logs_warning(self, caplog):
        """A warning-level log message is emitted on timeout."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("connect timeout"),
        ):
            with caplog.at_level(logging.WARNING, logger="services.http_client"):
                with pytest.raises(HTTPException):
                    await client.safe_request("GET", "https://slow.example.com/")

        assert any("timeout" in record.message.lower() for record in caplog.records)

    @pytest.mark.asyncio
    async def test_read_timeout_subclass_caught(self):
        """httpx.ReadTimeout (a subclass of TimeoutException) is also caught."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.ReadTimeout("read timeout"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://slow.example.com/large")

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_connect_timeout_subclass_caught(self):
        """httpx.ConnectTimeout (a subclass of TimeoutException) yields 504."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectTimeout("connect timeout"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://unreachable.example.com/")

        assert exc_info.value.status_code == 504


# ---------------------------------------------------------------------------
# ConnectError → 503
# ---------------------------------------------------------------------------


class TestSafeRequestConnectError:
    """httpx.ConnectError → HTTPException(503)."""

    @pytest.mark.asyncio
    async def test_connect_error_raises_http_exception_503(self):
        """ConnectError is converted to HTTPException with status 503."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("connection refused"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://down.example.com/")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_connect_error_detail_message(self):
        """503 HTTPException carries a human-readable detail string."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("connection refused"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://down.example.com/")

        assert "unavailable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_connect_error_logs_warning(self, caplog):
        """A warning-level log message is emitted on connection error."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("connection refused"),
        ):
            with caplog.at_level(logging.WARNING, logger="services.http_client"):
                with pytest.raises(HTTPException):
                    await client.safe_request("GET", "https://down.example.com/")

        assert any("connection" in record.message.lower() for record in caplog.records)


# ---------------------------------------------------------------------------
# Generic RequestError → 502
# ---------------------------------------------------------------------------


class TestSafeRequestGenericRequestError:
    """Other httpx.RequestError subclasses → HTTPException(502)."""

    @pytest.mark.asyncio
    async def test_request_error_raises_http_exception_502(self):
        """A generic RequestError is converted to HTTPException with status 502."""
        client = _make_client()

        # httpx.RequestError is the base class; use a concrete subclass that is
        # NOT TimeoutException and NOT ConnectError.
        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.RemoteProtocolError("invalid HTTP response"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://bad.example.com/")

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_request_error_detail_message(self):
        """502 HTTPException carries a human-readable detail string."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.RemoteProtocolError("malformed response"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("GET", "https://bad.example.com/")

        assert "gateway" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_request_error_logs_at_error_level(self, caplog):
        """An error-level log message is emitted for unexpected RequestError."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.RemoteProtocolError("protocol error"),
        ):
            with caplog.at_level(logging.ERROR, logger="services.http_client"):
                with pytest.raises(HTTPException):
                    await client.safe_request("GET", "https://bad.example.com/")

        assert any(record.levelno >= logging.ERROR for record in caplog.records)

    @pytest.mark.asyncio
    async def test_write_error_caught_as_502(self):
        """httpx.WriteError (a RequestError subclass) yields 502."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.WriteError("broken pipe"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await client.safe_request("POST", "https://bad.example.com/upload")

        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Non-httpx exceptions are NOT caught
# ---------------------------------------------------------------------------


class TestSafeRequestDoesNotSuppressNonHttpxErrors:
    """Unexpected / non-network exceptions should propagate unchanged."""

    @pytest.mark.asyncio
    async def test_value_error_propagates(self):
        """A ValueError raised inside request() is not swallowed."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=ValueError("unexpected internal error"),
        ):
            with pytest.raises(ValueError, match="unexpected internal error"):
                await client.safe_request("GET", "https://api.example.com/")

    @pytest.mark.asyncio
    async def test_runtime_error_propagates(self):
        """A RuntimeError raised inside request() is not swallowed."""
        client = _make_client()

        with patch.object(
            client,
            "request",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(RuntimeError, match="boom"):
                await client.safe_request("GET", "https://api.example.com/")


# ---------------------------------------------------------------------------
# Module-level safe_request convenience alias
# ---------------------------------------------------------------------------


class TestModuleLevelSafeRequest:
    """The module-level safe_request delegates to shared_client.safe_request."""

    @pytest.mark.asyncio
    async def test_module_safe_request_delegates_to_shared_client(self):
        """Module-level safe_request uses the module shared_client."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(shared_client, "safe_request", new_callable=AsyncMock, return_value=mock_response) as mock_sr:
            result = await safe_request("GET", "https://api.example.com/")

        mock_sr.assert_called_once_with("GET", "https://api.example.com/")
        assert result is mock_response

    @pytest.mark.asyncio
    async def test_module_safe_request_raises_504_on_timeout(self):
        """Module-level safe_request converts TimeoutException → 504."""
        with patch.object(
            shared_client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await safe_request("GET", "https://slow.example.com/")

        assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_module_safe_request_raises_503_on_connect_error(self):
        """Module-level safe_request converts ConnectError → 503."""
        with patch.object(
            shared_client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("refused"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await safe_request("POST", "https://down.example.com/")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_module_safe_request_raises_502_on_request_error(self):
        """Module-level safe_request converts generic RequestError → 502."""
        with patch.object(
            shared_client,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.RemoteProtocolError("bad response"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await safe_request("GET", "https://bad.example.com/")

        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Backwards-compatibility: existing direct methods still work
# ---------------------------------------------------------------------------


class TestBackwardsCompatibility:
    """Adding safe_request must not break existing shared_client usage."""

    def test_shared_client_still_has_get_method(self):
        assert hasattr(shared_client, "get")

    def test_shared_client_still_has_post_method(self):
        assert hasattr(shared_client, "post")

    def test_shared_client_still_has_put_method(self):
        assert hasattr(shared_client, "put")

    def test_shared_client_still_has_delete_method(self):
        assert hasattr(shared_client, "delete")

    def test_shared_client_still_is_async_client(self):
        assert isinstance(shared_client, httpx.AsyncClient)

    def test_shared_client_still_has_limits(self):
        limits = shared_client._limits
        assert limits is not None
        assert limits.max_connections >= 100
        assert limits.max_keepalive_connections >= 20

    def test_get_http_client_returns_shared_http_client(self):
        client = get_http_client()
        assert isinstance(client, SharedHttpClient)

    @pytest.mark.asyncio
    async def test_existing_direct_get_still_works(self):
        """Callers using shared_client.get() directly are unaffected."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(shared_client, "get", new_callable=AsyncMock, return_value=mock_response):
            result = await shared_client.get("https://api.example.com/data")

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_existing_direct_post_still_works(self):
        """Callers using shared_client.post() directly are unaffected."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 201

        with patch.object(shared_client, "post", new_callable=AsyncMock, return_value=mock_response):
            result = await shared_client.post("https://api.example.com/items", json={})

        assert result.status_code == 201
