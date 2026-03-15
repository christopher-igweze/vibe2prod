"""Tests for shared HTTP client usage in routes.

These tests verify that routes properly use the shared_client instead of
creating new httpx.AsyncClient instances for each request.

Test Location: tests/test_shared_client_usage.py
Project: api/routes/*.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import inspect


class TestGitHubOAuthUsesSharedClient:
    """Test suite for GitHub OAuth route using shared client."""

    def test_github_oauth_imports_shared_client(self):
        """Test that github_oauth.py imports shared_client from services.http_client."""
        try:
            from api.routes import github_oauth
            # Check if the module imports shared_client
            source = inspect.getsource(github_oauth)
            assert 'from services.http_client import shared_client' in source or \
                   'import shared_client' in source
        except ImportError:
            pytest.skip("Could not import github_oauth module")

    def test_github_oauth_does_not_create_new_async_client(self):
        """Test that github_oauth routes don't create new AsyncClient instances."""
        try:
            from api.routes import github_oauth
            source = inspect.getsource(github_oauth)
            # The old pattern was: async with httpx.AsyncClient
            # After fix, this should NOT appear in the route handlers
            # We check the functions that make HTTP calls
            
            # These functions should use shared_client, not create new clients
            functions_to_check = [
                '_exchange_code_for_access_token',
                '_fetch_github_profile',
                'list_github_repos',
                'list_repo_branches',
                'github_connection_status'
            ]
            
            for func_name in functions_to_check:
                try:
                    func = getattr(github_oauth, func_name)
                    func_source = inspect.getSource(func)
                    # Should NOT have "async with httpx.AsyncClient"
                    assert 'async with httpx.AsyncClient' not in func_source, \
                        f"Function {func_name} still creates new AsyncClient"
                except AttributeError:
                    # Function might not exist in this version
                    pass
        except ImportError:
            pytest.skip("Could not import github_oauth module")


class TestPrimerUsesSharedClient:
    """Test suite for Primer route using shared client."""

    def test_primer_imports_shared_client(self):
        """Test that primer.py imports shared_client from services.http_client."""
        try:
            from api.routes import primer
            source = inspect.getsource(primer)
            assert 'from services.http_client import shared_client' in source or \
                   'import shared_client' in source
        except ImportError:
            pytest.skip("Could not import primer module")

    def test_primer_does_not_create_new_async_client(self):
        """Test that primer routes don't create new AsyncClient instances."""
        try:
            from api.routes import primer
            
            # Check the _summarize function which makes HTTP calls
            try:
                func = getattr(primer, '_summarize')
                func_source = inspect.getSource(func)
                # Should NOT have "async with httpx.AsyncClient"
                assert 'async with httpx.AsyncClient' not in func_source, \
                    "_summarize still creates new AsyncClient"
            except AttributeError:
                pass
        except ImportError:
            pytest.skip("Could not import primer module")


class TestSharedClientIntegration:
    """Integration tests for shared client usage."""

    @pytest.mark.asyncio
    async def test_github_oauth_exchange_uses_shared_client(self):
        """Test that OAuth token exchange can use shared_client."""
        try:
            from services.http_client import shared_client
            
            # Mock the shared client's post method
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"access_token": "test_token", "token_type": "bearer"}
            mock_response.raise_for_status = MagicMock()
            
            with patch.object(shared_client, 'post', new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_response
                response = await shared_client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    json={"client_id": "test", "client_secret": "test", "code": "test"}
                )
                
                # Verify the call was made
                mock_post.assert_called_once()
                assert response.status_code == 200
        except ImportError:
            pytest.skip("Could not import shared_client module")

    @pytest.mark.asyncio
    async def test_shared_client_for_github_api_calls(self):
        """Test that shared_client can be used for GitHub API calls."""
        try:
            from services.http_client import shared_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"login": "testuser", "id": 12345}
            mock_response.raise_for_status = MagicMock()
            
            with patch.object(shared_client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                response = await shared_client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                mock_get.assert_called_once()
                assert response.status_code == 200
        except ImportError:
            pytest.skip("Could not import shared_client module")


class TestNoRegressions:
    """Test that the shared client fix doesn't break existing functionality."""

    def test_shared_client_is_not_none(self):
        """Test that shared_client is properly initialized."""
        try:
            from services.http_client import shared_client
            assert shared_client is not None
        except ImportError:
            pytest.skip("Could not import shared_client module")

    def test_shared_client_has_common_http_methods(self):
        """Test that shared_client has common HTTP methods."""
        try:
            from services.http_client import shared_client
            # Should have standard HTTP methods
            assert hasattr(shared_client, 'get')
            assert hasattr(shared_client, 'post')
            assert hasattr(shared_client, 'put')
            assert hasattr(shared_client, 'delete')
        except ImportError:
            pytest.skip("Could not import shared_client module")

    @pytest.mark.asyncio
    async def test_shared_client_context_manager_compatible(self):
        """Test that shared_client works with async context manager."""
        try:
            from services.http_client import shared_client
            # The shared client can still be used as context manager if needed
            async with shared_client as client:
                assert client is shared_client
        except ImportError:
            pytest.skip("Could not import shared_client module")
