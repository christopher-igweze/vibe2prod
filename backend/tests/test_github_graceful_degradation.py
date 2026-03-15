"""Tests for GitHub OAuth graceful degradation when external services are unavailable.

These tests verify that the GitHub OAuth endpoints properly return 503 Service
Unavailable with Retry-After headers when GitHub API times out or is unreachable.

Test Location: backend/tests/test_github_graceful_degradation.py
Project: api/routes/github_oauth.py, services/github.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from fastapi import HTTPException

# Import using relative path based on project structure
try:
    from api.routes.github_oauth import _exchange_code_for_access_token, _fetch_github_profile, list_github_repos, list_repo_branches, github_connection_status
except ImportError:
    try:
        from routes.github_oauth import _exchange_code_for_access_token, _fetch_github_profile, list_github_repos, list_repo_branches, github_connection_status
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        from api.routes.github_oauth import _exchange_code_for_access_token, _fetch_github_profile, list_github_repos, list_repo_branches, github_connection_status


class TestGitHubOAuthTimeoutHandling:
    """Test suite for timeout error handling in GitHub OAuth routes."""

    @pytest.mark.asyncio
    async def test_exchange_code_timeout_returns_503_with_retry_after(self):
        """Test that code exchange timeout returns 503 with Retry-After header."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await _exchange_code_for_access_token(
                    code="test_code",
                    redirect_uri="https://example.com/callback",
                    state="test_state"
                )

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_timeout"
            assert "temporarily unavailable" in exc.detail["message"].lower()
            assert exc.detail["retry_after"] == 30
            assert exc.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_exchange_code_connect_error_returns_503_with_retry_after(self):
        """Test that code exchange connect error returns 503 with Retry-After header."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await _exchange_code_for_access_token(
                    code="test_code",
                    redirect_uri="https://example.com/callback",
                    state="test_state"
                )

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_unreachable"
            assert exc.detail["retry_after"] == 60
            assert exc.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_fetch_profile_timeout_returns_503_with_retry_after(self):
        """Test that profile fetch timeout returns 503 with Retry-After header."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await _fetch_github_profile(access_token="test_token")

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_timeout"
            assert "temporarily unavailable" in exc.detail["message"].lower()
            assert exc.detail["retry_after"] == 30
            assert exc.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_fetch_profile_connect_error_returns_503_with_retry_after(self):
        """Test that profile fetch connect error returns 503 with Retry-After header."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await _fetch_github_profile(access_token="test_token")

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_unreachable"
            assert exc.detail["retry_after"] == 60
            assert exc.headers["Retry-After"] == "60"


class TestGitHubReposTimeoutHandling:
    """Test suite for timeout error handling in GitHub repos endpoints."""

    @pytest.mark.asyncio
    async def test_list_repos_timeout_returns_503_with_retry_after(self):
        """Test that list repos timeout returns 503 with Retry-After header."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.app.state.supabase = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await list_github_repos(mock_request)

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_timeout"
            assert "temporarily unavailable" in exc.detail["message"].lower()
            assert exc.detail["retry_after"] == 30
            assert exc.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_list_repos_connect_error_returns_503_with_retry_after(self):
        """Test that list repos connect error returns 503 with Retry-After header."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.app.state.supabase = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await list_github_repos(mock_request)

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_unreachable"
            assert exc.detail["retry_after"] == 60
            assert exc.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_list_repo_branches_timeout_returns_503_with_retry_after(self):
        """Test that list repo branches timeout returns 503 with Retry-After header."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.app.state.supabase = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await list_repo_branches(mock_request, owner="test_owner", repo="test_repo")

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_timeout"
            assert "temporarily unavailable" in exc.detail["message"].lower()
            assert exc.detail["retry_after"] == 30
            assert exc.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_list_repo_branches_connect_error_returns_503_with_retry_after(self):
        """Test that list repo branches connect error returns 503 with Retry-After header."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.app.state.supabase = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await list_repo_branches(mock_request, owner="test_owner", repo="test_repo")

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_unreachable"
            assert exc.detail["retry_after"] == 60
            assert exc.headers["Retry-After"] == "60"


class TestGitHubConnectionStatusTimeoutHandling:
    """Test suite for timeout error handling in GitHub connection status endpoint."""

    @pytest.mark.asyncio
    async def test_github_connection_status_timeout_returns_503(self):
        """Test that connection status timeout returns 503."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.app.state.supabase = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await github_connection_status(mock_request)

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_timeout"
            assert exc.detail["retry_after"] == 30
            assert exc.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_github_connection_status_connect_error_returns_503(self):
        """Test that connection status connect error returns 503."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.app.state.supabase = MagicMock()

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await github_connection_status(mock_request)

            exc = exc_info.value
            assert exc.status_code == 503
            assert exc.detail["code"] == "github_unreachable"
            assert exc.detail["retry_after"] == 60
            assert exc.headers["Retry-After"] == "60"
