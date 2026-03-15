"""Tests for GitHub OAuth route delegation to service.

These tests verify that the github_oauth.py route file properly
delegates OAuth business logic to the GitHubOAuthService.

Test Location: tests/test_github_oauth_route_delegation.py
Project: backend/api/routes/github_oauth.py
Framework: pytest
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the route module
try:
    from api.routes import github_oauth
except ImportError:
    try:
        from backend.api.routes import github_oauth
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.routes import github_oauth
        else:
            raise ImportError("Could not import github_oauth routes")


# Required environment variables for settings
BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "GITHUB_CLIENT_ID": "test-client-id",
    "GITHUB_CLIENT_SECRET": "test-client-secret",
    "GITHUB_OAUTH_STATE_SECRET": "test-state-secret",
}


class TestGitHubOAuthRouteExists:
    """Test that the github_oauth router exists and has required endpoints."""

    def test_router_exists(self):
        """Test that the router is properly defined."""
        assert github_oauth.router is not None

    def test_github_oauth_endpoint_exists(self):
        """Test that the github_oauth endpoint handler exists."""
        assert github_oauth.github_oauth is not None
        assert callable(github_oauth.github_oauth)


class TestGitHubOAuthRouteDelegation:
    """Test suite for route delegation to service."""

    @pytest.fixture
    def mock_service(self):
        """Mock the github_oauth_service."""
        with patch("api.routes.github_oauth.github_oauth_service") as mock:
            mock.disconnect_user = AsyncMock()
            mock.get_auth_url = MagicMock(return_value="https://github.com/login/oauth/authorize?state=test")
            mock.validate_oauth_state = MagicMock()
            mock.exchange_code_for_access_token = AsyncMock(return_value="test-access-token")
            mock.get_github_profile = AsyncMock(return_value={"login": "testuser", "avatar_url": "https://example.com/avatar.png"})
            mock.save_github_connection = AsyncMock()
            mock.list_user_repositories = AsyncMock(return_value=[])
            yield mock

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock()
        request.state.user_id = "test-user-123"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_disconnect_delegates_to_service(self, mock_service, mock_request):
        """Test that disconnect action calls the service method."""
        from api.routes.github_oauth import GithubOAuthRequest
        
        request_body = GithubOAuthRequest(action="disconnect")
        
        with patch.dict("os.environ", BASE_ENV, clear=True):
            await github_oauth.github_oauth(request_body, mock_request)
        
        mock_service.disconnect_user.assert_called_once_with(user_id="test-user-123")

    @pytest.mark.asyncio
    async def test_get_auth_url_delegates_to_service(self, mock_service, mock_request):
        """Test that get_auth_url action calls the service method."""
        from api.routes.github_oauth import GithubOAuthRequest
        
        request_body = GithubOAuthRequest(
            action="get_auth_url",
            redirect_uri="https://example.com/callback",
        )
        
        with patch.dict("os.environ", BASE_ENV, clear=True):
            response = await github_oauth.github_oauth(request_body, mock_request)
        
        mock_service.get_auth_url.assert_called_once()
        assert response.auth_url is not None

    @pytest.mark.asyncio
    async def test_exchange_code_validates_state(self, mock_service, mock_request):
        """Test that exchange_code action validates state via service."""
        from api.routes.github_oauth import GithubOAuthRequest
        
        request_body = GithubOAuthRequest(
            action="exchange_code",
            code="test-code",
            redirect_uri="https://example.com/callback",
            state="test-state",
        )
        
        with patch.dict("os.environ", BASE_ENV, clear=True):
            await github_oauth.github_oauth(request_body, mock_request)
        
        mock_service.validate_oauth_state.assert_called_once()
