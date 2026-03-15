"""Tests for GitHub OAuth service abstraction.

These tests verify that the GitHub OAuth routes properly delegate to the
github service module rather than making inline httpx calls.

Test Location: tests/test_github_oauth_service_abstraction.py
Project: api/routes/github_oauth.py + services/github.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from services import github as github_service
    from api.routes import github_oauth
except ImportError:
    import sys
    from pathlib import Path
    # Adjust path for different project layouts
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from services import github as github_service
    from api.routes import github_oauth


class TestGithubOAuthServiceAbstraction:
    """Test suite verifying GitHub OAuth operations use service abstraction."""

    def test_github_oauth_module_does_not_import_httpx(self):
        """Verify that github_oauth.py does not import httpx directly."""
        # Check that httpx is not in the module's global imports
        assert not hasattr(github_oauth, 'httpx'), \
            "github_oauth module should not import httpx directly"

    def test_github_oauth_module_does_not_import_shared_client(self):
        """Verify that github_oauth.py does not import shared_client directly."""
        # The old implementation imported shared_client from services.http_client
        assert not hasattr(github_oauth, 'shared_client'), \
            "github_oauth module should not import shared_client directly"

    def test_github_oauth_module_imports_github_service(self):
        """Verify that github_oauth.py imports the github service module."""
        assert hasattr(github_oauth, 'github_service'), \
            "github_oauth module should import github_service"

    def test_github_service_has_exchange_code_function(self):
        """Verify that github_service has exchange_code_for_access_token function."""
        assert hasattr(github_service, 'exchange_code_for_access_token'), \
            "github_service should have exchange_code_for_access_token function"
        assert callable(github_service.exchange_code_for_access_token), \
            "exchange_code_for_access_token should be callable"

    def test_github_service_has_fetch_profile_function(self):
        """Verify that github_service has fetch_github_profile function."""
        assert hasattr(github_service, 'fetch_github_profile'), \
            "github_service should have fetch_github_profile function"
        assert callable(github_service.fetch_github_profile), \
            "fetch_github_profile should be callable"

    @pytest.mark.asyncio
    async def test_exchange_code_for_access_token_returns_token(self):
        """Test that exchange_code_for_access_token returns access token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token_12345"}

        with patch('services.github.shared_client') as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await github_service.exchange_code_for_access_token(
                client_id="test_client_id",
                client_secret="test_client_secret",
                code="test_code",
                redirect_uri="http://localhost/callback",
                state="test_state",
            )

            assert result == "test_token_12345"

    @pytest.mark.asyncio
    async def test_exchange_code_for_access_token_handles_timeout(self):
        """Test that exchange_code_for_access_token handles timeout."""
        with patch('services.github.shared_client') as mock_client:
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await github_service.exchange_code_for_access_token(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    code="test_code",
                    redirect_uri="http://localhost/callback",
                    state="test_state",
                )

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["code"] == "github_timeout"

    @pytest.mark.asyncio
    async def test_exchange_code_for_access_token_handles_connect_error(self):
        """Test that exchange_code_for_access_token handles connection errors."""
        with patch('services.github.shared_client') as mock_client:
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await github_service.exchange_code_for_access_token(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    code="test_code",
                    redirect_uri="http://localhost/callback",
                    state="test_state",
                )

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["code"] == "github_unreachable"

    @pytest.mark.asyncio
    async def test_exchange_code_for_access_token_handles_http_error(self):
        """Test that exchange_code_for_access_token handles HTTP error status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch('services.github.shared_client') as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await github_service.exchange_code_for_access_token(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    code="test_code",
                    redirect_uri="http://localhost/callback",
                    state="test_state",
                )

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_token_exchange_failed"

    @pytest.mark.asyncio
    async def test_fetch_github_profile_returns_username_and_avatar(self):
        """Test that fetch_github_profile returns username and avatar URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345"
        }

        with patch('services.github.shared_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            username, avatar_url = await github_service.fetch_github_profile("test_token")

            assert username == "testuser"
            assert avatar_url == "https://avatars.githubusercontent.com/u/12345"

    @pytest.mark.asyncio
    async def test_fetch_github_profile_handles_timeout(self):
        """Test that fetch_github_profile handles timeout."""
        with patch('services.github.shared_client') as mock_client:
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await github_service.fetch_github_profile("test_token")

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["code"] == "github_timeout"

    @pytest.mark.asyncio
    async def test_fetch_github_profile_handles_connect_error(self):
        """Test that fetch_github_profile handles connection errors."""
        with patch('services.github.shared_client') as mock_client:
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await github_service.fetch_github_profile("test_token")

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail["code"] == "github_unreachable"

    @pytest.mark.asyncio
    async def test_fetch_github_profile_handles_http_error(self):
        """Test that fetch_github_profile handles HTTP error status codes."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch('services.github.shared_client') as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await github_service.fetch_github_profile("invalid_token")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_profile_fetch_failed"
