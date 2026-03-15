"""Tests for auth middleware E2E testing bypass security.

These tests verify that the SupabaseAuthMiddleware properly prevents
the E2E testing bypass from being activated in production environments,
even if e2e_testing is incorrectly enabled.

The fix checks environment FIRST before checking e2e_testing, ensuring
that the bypass cannot be activated in production even if misconfigured.

Test Location: backend/tests/test_auth_middleware_e2e_bypass.py
Project: backend/api/middleware/auth.py
Framework: pytest
"""

import pytest
from pydantic import SecretStr
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request
from starlette.responses import JSONResponse

# Import the middleware class
try:
    from backend.api.middleware.auth import SupabaseAuthMiddleware
except ImportError:
    try:
        from api.middleware.auth import SupabaseAuthMiddleware
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.middleware.auth import SupabaseAuthMiddleware


class MockSettings:
    """Mock settings object for testing different configurations.

    ``e2e_testing_token`` is stored as a ``SecretStr`` to match the real
    ``Settings`` type, ensuring the middleware's ``.get_secret_value()`` call
    works correctly in tests (CWE-532).
    """

    def __init__(self, environment: str = "development", e2e_testing: bool = False,
                 e2e_testing_token: str = ""):
        self.environment = environment
        self.e2e_testing = e2e_testing
        self.e2e_testing_token = SecretStr(e2e_testing_token)


def create_mock_request(path: str = "/api/test", method: str = "GET"):
    """Create a mock request object."""
    request = MagicMock(spec=Request)
    request.url.path = path
    request.method = method
    request.state = MagicMock()
    return request


class TestE2EBypassProductionSecurity:
    """Test suite for E2E testing bypass security in production environments.
    
    These tests verify that the fix properly checks environment FIRST
    before allowing the e2e_testing bypass.
    """

    @pytest.mark.asyncio
    async def test_production_environment_blocks_e2e_testing_enabled(self):
        """Test that e2e_testing=True in production environment returns 403.
        
        This is the core security fix: checking environment FIRST before
        allowing the e2e_testing bypass. Even if e2e_testing is enabled,
        it must be blocked in production.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        # Create mock settings with production environment and e2e_testing enabled
        middleware.settings = MockSettings(
            environment="production",
            e2e_testing=True,
            e2e_testing_token="test-token"
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should block with 403 in production even with e2e_testing enabled
        assert response.status_code == 403
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_production_environment_blocks_e2e_testing_enabled_with_no_token(self):
        """Test that e2e_testing=True with no token in production returns 403.
        
        Even if the token is missing, production should block the request.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="production",
            e2e_testing=True,
            e2e_testing_token=""
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should block with 403 in production
        assert response.status_code == 403
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_production_environment_allows_normal_auth_when_e2e_disabled(self):
        """Test that production with e2e_testing=False proceeds to JWT verification.
        
        When in production with e2e_testing disabled, the request should proceed
        to normal authentication flow.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="production",
            e2e_testing=False,
            e2e_testing_token=""
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should proceed to call_next (normal flow)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_development_environment_allows_e2e_testing_with_valid_token(self):
        """Test that development environment with e2e_testing=True allows bypass.
        
        In development, the e2e_testing bypass should work when a token is provided.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="development",
            e2e_testing=True,
            e2e_testing_token="valid-test-token"
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should proceed to call_next (bypass is allowed in development)
        call_next.assert_called_once()
        # Should set the e2e_test_user
        assert request.state.user_id == 'e2e_test_user'

    @pytest.mark.asyncio
    async def test_development_environment_blocks_e2e_testing_without_token(self):
        """Test that development with e2e_testing=True but no token returns 403.
        
        Even in development, if e2e_testing is enabled but no token is set,
        the request should be blocked.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="development",
            e2e_testing=True,
            e2e_testing_token=""
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should block with 403 - token required
        assert response.status_code == 403
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_development_environment_allows_normal_auth_when_e2e_disabled(self):
        """Test that development with e2e_testing=False proceeds to JWT verification.
        
        When e2e_testing is disabled, even in development, normal auth should run.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="development",
            e2e_testing=False,
            e2e_testing_token=""
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should proceed to call_next (normal flow)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_staging_environment_blocks_e2e_testing_enabled(self):
        """Test that staging environment blocks e2e_testing=True.
        
        Staging is not development, so e2e_testing bypass should be blocked.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="staging",
            e2e_testing=True,
            e2e_testing_token="test-token"
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should block with 403 in staging (not development)
        assert response.status_code == 403
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_staging_environment_allows_normal_auth_when_e2e_disabled(self):
        """Test that staging with e2e_testing=False proceeds to JWT verification.
        """
        mock_app = MagicMock()
        middleware = SupabaseAuthMiddleware(mock_app)
        
        middleware.settings = MockSettings(
            environment="staging",
            e2e_testing=False,
            e2e_testing_token=""
        )
        
        request = create_mock_request("/api/test")
        call_next = AsyncMock(return_value=JSONResponse(content={}))
        
        response = await middleware.dispatch(request, call_next)
        
        # Should proceed to call_next (normal flow)
        call_next.assert_called_once()
