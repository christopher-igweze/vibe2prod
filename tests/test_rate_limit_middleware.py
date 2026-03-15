"""Tests for rate limit middleware implementation.

These tests verify that the rate_limit middleware provides meaningful
rate limiting functionality including request tracking, limits enforcement,
and proper HTTP 429 responses.

Test Location: tests/test_rate_limit_middleware.py
Framework: pytest
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request, HTTPException
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

# Try to import the rate_limit module
try:
    from api.middleware.rate_limit import RateLimitMiddleware, get_rate_limiter
except ImportError:
    # Try alternative import path
    try:
        from backend.api.middleware.rate_limit import RateLimitMiddleware, get_rate_limiter
    except ImportError:
        # If neither works, we'll skip tests that require it
        RateLimitMiddleware = None
        get_rate_limiter = None


class TestRateLimitMiddlewareExists:
    """Test suite verifying rate limit middleware exists and is properly implemented."""

    def test_rate_limit_middleware_class_exists(self):
        """Test that RateLimitMiddleware class is defined and importable."""
        assert RateLimitMiddleware is not None, "RateLimitMiddleware class must be defined"

    def test_rate_limit_middleware_is_base_http_middleware(self):
        """Test that RateLimitMiddleware inherits from BaseHTTPMiddleware."""
        if RateLimitMiddleware is None:
            pytest.skip("RateLimitMiddleware not available")
        assert issubclass(RateLimitMiddleware, BaseHTTPMiddleware), \
            "RateLimitMiddleware must inherit from BaseHTTPMiddleware"

    def test_rate_limit_middleware_has_dispatch_method(self):
        """Test that RateLimitMiddleware implements dispatch method."""
        if RateLimitMiddleware is None:
            pytest.skip("RateLimitMiddleware not available")
        assert hasattr(RateLimitMiddleware, 'dispatch'), \
            "RateLimitMiddleware must have a dispatch method"
        assert callable(RateLimitMiddleware.dispatch), \
            "dispatch must be callable"

    def test_get_rate_limiter_function_exists(self):
        """Test that get_rate_limiter function is defined for configuration."""
        assert get_rate_limiter is not None, \
            "get_rate_limiter function must be defined for configuration"


class TestRateLimitMiddlewareFunctionality:
    """Test suite for rate limiting functionality."""

    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app for testing."""
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        return app

    def test_rate_limiter_accepts_configuration_parameters(self):
        """Test that rate limiter can be configured with limits and windows."""
        if get_rate_limiter is None:
            pytest.skip("get_rate_limiter not available")

        # Should accept configuration for requests per time window
        limiter = get_rate_limiter(requests_per_minute=60, window_seconds=60)
        assert limiter is not None, "Rate limiter should return a configured instance"

    def test_rate_limiter_tracks_client_requests(self):
        """Test that rate limiter tracks requests per client identifier."""
        if get_rate_limiter is None:
            pytest.skip("get_rate_limiter not available")

        limiter = get_rate_limiter(requests_per_minute=10, window_seconds=60)

        # Simulate requests from same client
        client_id = "test-client-123"

        # First request should be allowed
        result = limiter.check_rate_limit(client_id)
        assert result.allowed is True, "First request should be allowed"

        # Request count should increment
        assert result.request_count >= 1

    def test_rate_limiter_blocks_excess_requests(self):
        """Test that rate limiter blocks requests exceeding the limit."""
        if get_rate_limiter is None:
            pytest.skip("get_rate_limiter not available")

        # Set very low limit for testing
        limiter = get_rate_limiter(requests_per_minute=2, window_seconds=60)
        client_id = "test-client-over-limit"

        # Make requests up to the limit
        for i in range(2):
            result = limiter.check_rate_limit(client_id)
            assert result.allowed is True, f"Request {i+1} should be allowed"

        # Third request should be blocked
        result = limiter.check_rate_limit(client_id)
        assert result.allowed is False, "Request exceeding limit should be blocked"

    def test_rate_limiter_returns_retry_after_info(self):
        """Test that rate limiter provides retry-after information when blocked."""
        if get_rate_limiter is None:
            pytest.skip("get_rate_limiter not available")

        limiter = get_rate_limiter(requests_per_minute=1, window_seconds=60)
        client_id = "test-client-retry"

        # First request
        limiter.check_rate_limit(client_id)

        # Second request should be blocked
        result = limiter.check_rate_limit(client_id)
        assert result.allowed is False
        assert hasattr(result, 'retry_after'), "Should provide retry_after information"
        assert result.retry_after > 0, "retry_after should be positive"

    def test_different_clients_have_independent_limits(self):
        """Test that different clients have independent rate limit counters."""
        if get_rate_limiter is None:
            pytest.skip("get_rate_limiter not available")

        limiter = get_rate_limiter(requests_per_minute=1, window_seconds=60)

        client_a = "client-a"
        client_b = "client-b"

        # Client A uses their limit
        result_a1 = limiter.check_rate_limit(client_a)
        assert result_a1.allowed is True

        result_a2 = limiter.check_rate_limit(client_a)
        assert result_a2.allowed is False  # Client A blocked

        # Client B should still be allowed (independent limit)
        result_b = limiter.check_rate_limit(client_b)
        assert result_b.allowed is True, "Client B should have independent limit"


class TestRateLimitMiddlewareIntegration:
    """Integration tests for rate limit middleware with FastAPI."""

    def test_middleware_can_be_added_to_app(self):
        """Test that rate limit middleware can be added to FastAPI app."""
        if RateLimitMiddleware is None or get_rate_limiter is None:
            pytest.skip("Middleware components not available")

        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        # Add rate limiting middleware
        limiter = get_rate_limiter(requests_per_minute=60, window_seconds=60)
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return JSONResponse({"status": "ok"})

        # Verify app was created successfully
        assert app is not None

    def test_middleware_returns_429_when_rate_limited(self):
        """Test that middleware returns HTTP 429 when rate limit is exceeded."""
        if RateLimitMiddleware is None or get_rate_limiter is None:
            pytest.skip("Middleware components not available")

        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        # Add rate limiting middleware with very low limit
        limiter = get_rate_limiter(requests_per_minute=1, window_seconds=60)
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return JSONResponse({"status": "ok"})

        client = TestClient(app)

        # First request should succeed
        response = client.get("/test")
        assert response.status_code == 200

        # Second request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429, \
            "Should return 429 Too Many Requests when rate limited"

    def test_middleware_identifies_clients_by_ip(self):
        """Test that middleware identifies clients by IP address."""
        if RateLimitMiddleware is None or get_rate_limiter is None:
            pytest.skip("Middleware components not available")

        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        limiter = get_rate_limiter(requests_per_minute=1, window_seconds=60)
        app.add_middleware(RateLimitMiddleware, limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return JSONResponse({"status": "ok"})

        client = TestClient(app, headers={"X-Forwarded-For": "192.168.1.1"})

        # Request from first IP
        response1 = client.get("/test")
        assert response1.status_code == 200

        # Second request from same IP should be blocked
        response2 = client.get("/test")
        assert response2.status_code == 429

        # Request from different IP should succeed
        client_diff = TestClient(app, headers={"X-Forwarded-For": "192.168.1.2"})
        response3 = client_diff.get("/test")
        assert response3.status_code == 200, \
            "Different IP should have independent rate limit"
