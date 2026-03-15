"""Tests for GitHub OAuth service.

These tests verify that the GitHubOAuthService properly handles
OAuth business logic including state management, token exchange,
and user disconnection.

Test Location: tests/test_github_oauth_service.py
Project: backend/services/github_oauth_service.py
Framework: pytest
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the service class
try:
    from services.github_oauth_service import GitHubOAuthService
except ImportError:
    try:
        from backend.services.github_oauth_service import GitHubOAuthService
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from services.github_oauth_service import GitHubOAuthService
        else:
            raise ImportError("Could not import GitHubOAuthService")


# Required environment variables for settings - must include ALL required fields
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


class TestGitHubOAuthServiceExists:
    """Test that the GitHubOAuthService class exists and can be instantiated."""

    def test_service_class_exists(self):
        """Test that GitHubOAuthService class exists."""
        assert GitHubOAuthService is not None

    def test_service_can_be_instantiated(self):
        """Test that service can be instantiated."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            service = GitHubOAuthService()
            assert service is not None


class TestGitHubOAuthServiceDisconnect:
    """Test suite for disconnect_user method."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            return GitHubOAuthService()

    @pytest.fixture
    def mock_db(self):
        """Mock the database client."""
        with patch("services.github_oauth_service.db") as mock:
            mock.clear_github_connection = AsyncMock()
            yield mock

    @pytest.mark.asyncio
    async def test_disconnect_user_calls_db(self, service, mock_db):
        """Test that disconnect_user calls the database clear method."""
        user_id = "test-user-123"
        await service.disconnect_user(user_id=user_id)
        mock_db.clear_github_connection.assert_called_once_with(user_id=user_id)


class TestGitHubOAuthServiceAuthUrl:
    """Test suite for get_auth_url method."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            return GitHubOAuthService()

    def test_get_auth_url_returns_valid_url(self, service):
        """Test that get_auth_url returns a valid GitHub OAuth URL."""
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        auth_url = service.get_auth_url(user_id=user_id, redirect_uri=redirect_uri)
        
        assert auth_url is not None
        assert "https://github.com/login/oauth/authorize" in auth_url
        assert "client_id=test-client-id" in auth_url
        assert "scope=" in auth_url
        assert "state=" in auth_url

    def test_get_auth_url_includes_redirect_uri(self, service):
        """Test that get_auth_url includes the redirect_uri in the query string."""
        redirect_uri = "https://example.com/callback"
        
        auth_url = service.get_auth_url(user_id="user-123", redirect_uri=redirect_uri)
        
        # URL-encoded redirect_uri should be in the URL
        assert "redirect_uri=" in auth_url


class TestGitHubOAuthServiceStateValidation:
    """Test suite for validate_oauth_state method."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            return GitHubOAuthService()

    def test_validate_oauth_state_success(self, service):
        """Test that validate_oauth_state passes for valid state."""
        # Create a valid state token
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        # Should not raise
        service.validate_oauth_state(
            state=state,
            expected_user_id=user_id,
            expected_redirect_uri=redirect_uri,
        )

    def test_validate_oauth_state_user_mismatch(self, service):
        """Test that validate_oauth_state raises for user mismatch."""
        from fastapi import HTTPException
        
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        with pytest.raises(HTTPException) as exc_info:
            service.validate_oauth_state(
                state=state,
                expected_user_id="different-user",
                expected_redirect_uri=redirect_uri,
            )
        assert exc_info.value.status_code == 403
        assert "oauth_state_user_mismatch" in exc_info.value.detail.get("code", "")

    def test_validate_oauth_state_redirect_mismatch(self, service):
        """Test that validate_oauth_state raises for redirect_uri mismatch."""
        from fastapi import HTTPException
        
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        with pytest.raises(HTTPException) as exc_info:
            service.validate_oauth_state(
                state=state,
                expected_user_id=user_id,
                expected_redirect_uri="https://different.com/callback",
            )
        assert exc_info.value.status_code == 400
        assert "oauth_state_redirect_mismatch" in exc_info.value.detail.get("code", "")
