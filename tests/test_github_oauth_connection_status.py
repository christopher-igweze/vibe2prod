"""Tests for GitHub OAuth connection status endpoint.

These tests verify that the /github/status endpoint correctly reports
connection status without making redundant API calls to GitHub.

Test Location: tests/test_github_oauth_connection_status.py
Project: backend
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import using relative path based on project structure
try:
    from api.routes import github_oauth
except ImportError:
    # Fallback for different project structures
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from api.routes import github_oauth


class TestGitHubConnectionStatus:
    """Test suite for GitHub connection status endpoint performance."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with GitHub OAuth config."""
        with patch('api.routes.github_oauth.settings') as mock_settings:
            mock_settings.GITHUB_CLIENT_ID = "test_client_id"
            mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"
            mock_settings.GITHUB_REDIRECT_URI = "http://localhost/callback"
            yield mock_settings

    @pytest.mark.asyncio
    async def test_status_no_api_call_when_token_exists(self, mock_settings):
        """Test that status endpoint does not make API call when token exists.
        
        This is the key performance fix - we should not make an extra HTTP
        request to verify the token when we only need to know if connected.
        The token existence check via get_github_access_token is sufficient.
        """
        # Mock the get_github_access_token to return a valid token
        with patch('api.routes.github_oauth.get_github_access_token', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "valid_token_12345"
            
            # Mock httpx.AsyncClient to track if any API calls are made
            with patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                # Call the status endpoint
                result = await github_oauth.status()
                
                # Verify connected is True when token exists
                assert result["connected"] is True
                
                # Verify NO API call was made to verify token validity
                # The client.get should NOT have been called
                mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_status_no_api_call_when_no_token(self, mock_settings):
        """Test that status endpoint does not make API call when no token exists."""
        # Mock the get_github_access_token to return None (no token)
        with patch('api.routes.github_oauth.get_github_access_token', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = None
            
            # Mock httpx.AsyncClient to track if any API calls are made
            with patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                # Call the status endpoint
                result = await github_oauth.status()
                
                # Verify connected is False when no token
                assert result["connected"] is False
                
                # Verify NO API call was made
                mock_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_status_returns_connected_true_with_token(self, mock_settings):
        """Test that status returns connected=True when token exists."""
        with patch('api.routes.github_oauth.get_github_access_token', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "some_valid_token"
            
            with patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                result = await github_oauth.status()
                
                assert result.get("connected") is True

    @pytest.mark.asyncio
    async def test_status_returns_connected_false_without_token(self, mock_settings):
        """Test that status returns connected=False when no token exists."""
        with patch('api.routes.github_oauth.get_github_access_token', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = None
            
            with patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                result = await github_oauth.status()
                
                assert result.get("connected") is False


class TestGitHubConnectionStatusRegression:
    """Regression tests to prevent the redundant API call from being re-introduced."""

    @pytest.mark.asyncio
    async def test_no_github_user_api_call_in_status(self):
        """Regression: Verify no GET /user API call is made for status check.
        
        This test ensures the performance fix is not reverted. Previously,
        the status endpoint was calling GitHub's /user API to verify token
        validity, which was unnecessary since token existence is sufficient.
        """
        with patch('api.routes.github_oauth.get_github_access_token', new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "token_exists"
            
            with patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value.__aenter__.return_value = mock_client
                
                await github_oauth.status()
                
                # Get all calls made to the mock client
                call_args_list = mock_client.get.call_args_list
                
                # Verify no calls were made to any GitHub API endpoints
                for call in call_args_list:
                    if call:
                        args, kwargs = call
                        url = args[0] if args else kwargs.get('url', '')
                        assert 'api.github.com' not in str(url), \
                            f"Redundant API call to {url} detected - this should not happen"
