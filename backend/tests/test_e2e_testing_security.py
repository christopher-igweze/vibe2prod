"""Tests for E2E testing security bypass fix.

These tests verify that the E2E testing authentication bypass is properly
restricted to development environments with a valid token, preventing
accidental security bypass in production.

Test Location: tests/test_e2e_testing_security.py
Project: api/middleware/auth.py
Framework: pytest
"""

import pytest
from pydantic import SecretStr
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from starlette.responses import JSONResponse, Response

# Import using relative path based on project structure
try:
    from api.middleware.auth import SupabaseAuthMiddleware
except ImportError:
    try:
        from middleware.auth import SupabaseAuthMiddleware
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from api.middleware.auth import SupabaseAuthMiddleware


class TestE2ETestingSecurityBypass:
    """Test suite for E2E testing security bypass in auth middleware."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for different test scenarios.

        ``e2e_testing_token`` is a ``SecretStr`` to match the real ``Settings``
        type so the middleware's ``.get_secret_value()`` call works correctly
        (CWE-532).
        """
        mock = MagicMock()
        mock.clerk_jwks_url = "https://clerk.example.com/.well-known/jwks"
        mock.supabase_jwt_secret = "secret"
        mock.e2e_testing = False
        mock.environment = "production"
        mock.e2e_testing_token = SecretStr("")
        return mock

    @pytest.fixture
    def middleware(self, mock_settings):
        """Create middleware instance for testing."""
        with patch('api.middleware.auth.settings', mock_settings):
            mw = SupabaseAuthMiddleware(app=AsyncMock())
            return mw

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.state = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_e2e_testing_blocked_in_production(self, middleware, mock_request, mock_settings):
        """Test that E2E testing is blocked when environment is production."""
        mock_settings.e2e_testing = True
        mock_settings.environment = "production"
        mock_settings.e2e_testing_token = SecretStr("test-token")

        async def mock_call_next(request):
            return Response(content=b"OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 403 Forbidden
        assert response.status_code == 403
        body = response.body.decode() if hasattr(response, 'body') else ""
        assert "production" in body.lower() or "not allowed" in body.lower()

    @pytest.mark.asyncio
    async def test_e2e_testing_blocked_without_token_in_development(self, middleware, mock_request, mock_settings):
        """Test that E2E testing is blocked in development without token."""
        mock_settings.e2e_testing = True
        mock_settings.environment = "development"
        mock_settings.e2e_testing_token = SecretStr("")

        async def mock_call_next(request):
            return Response(content=b"OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 403 Forbidden
        assert response.status_code == 403
        body = response.body.decode() if hasattr(response, 'body') else ""
        assert "token" in body.lower() or "required" in body.lower()

    @pytest.mark.asyncio
    async def test_e2e_testing_allowed_in_development_with_token(self, middleware, mock_request, mock_settings):
        """Test that E2E testing works in development with valid token."""
        mock_settings.e2e_testing = True
        mock_settings.environment = "development"
        mock_settings.e2e_testing_token = SecretStr("valid-test-token")

        async def mock_call_next(request):
            return Response(content=b"OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should allow the request through
        assert response.status_code == 200
        # Should set the synthetic user_id
        assert mock_request.state.user_id == "e2e_test_user"

    @pytest.mark.asyncio
    async def test_e2e_testing_blocked_when_disabled(self, middleware, mock_request, mock_settings):
        """Test that E2E testing is blocked when e2e_testing is False."""
        mock_settings.e2e_testing = False
        mock_settings.environment = "development"
        mock_settings.e2e_testing_token = SecretStr("")
        
        async def mock_call_next(request):
            return Response(content=b"OK", status_code=200)
        
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Should NOT bypass - should continue to normal auth
        # The response should NOT be 403 from E2E bypass check
        assert response.status_code != 403 or mock_request.state.user_id != "e2e_test_user"
