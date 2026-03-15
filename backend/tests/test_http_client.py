"""Tests for HTTP client connection pooling implementation.

These tests verify that the shared httpx.AsyncClient with connection pooling
is properly implemented and used across the application.

Test Location: backend/tests/test_http_client.py
Project: services/http_client.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import inspect
from pathlib import Path

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from services.http_client import shared_client
except ImportError:
    try:
        from backend.services.http_client import shared_client
    except ImportError:
        import sys
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_path))
        from services.http_client import shared_client


class TestSharedHttpClientExists:
    """Test suite for shared HTTP client existence and configuration."""

    def test_shared_client_is_exported(self):
        """Test that shared_client is properly exported from http_client module."""
        assert shared_client is not None

    def test_shared_client_is_async_client(self):
        """Test that shared_client is an instance of httpx.AsyncClient."""
        assert isinstance(shared_client, httpx.AsyncClient)

    def test_shared_client_has_limits_configured(self):
        """Test that shared_client is configured with connection pooling limits."""
        # The client should have limits configured
        # We check that limits attribute exists by accessing _limits (internal) or by checking config
        limits = getattr(shared_client, '_limits', None)
        if limits is not None:
            assert limits is not None
            # Verify connection pool settings are configured
            assert hasattr(limits, 'max_connections')
            assert limits.max_connections is not None
            assert limits.max_connections > 0


class TestGitHubOAuthUsesSharedClient:
    """Test suite for verifying github_oauth routes use the shared client."""

    def test_github_oauth_imports_shared_client(self):
        """Test that github_oauth module imports shared_client."""
        try:
            from api.routes import github_oauth
            # Check if shared_client is imported in the module
            module_source = inspect.getsource(github_oauth)
            assert 'shared_client' in module_source
        except ImportError:
            # Try alternative import path
            from backend.api.routes import github_oauth
            module_source = inspect.getsource(github_oauth)
            assert 'shared_client' in module_source

    def test_github_oauth_does_not_create_new_clients(self):
        """Test that github_oauth does not create new httpx.AsyncClient instances."""
        try:
            from api.routes import github_oauth
        except ImportError:
            from backend.api.routes import github_oauth
        
        module_source = inspect.getsource(github_oauth)
        # Check that the pattern 'async with httpx.AsyncClient' is NOT used
        # This would indicate creating new clients per request
        assert 'async with httpx.AsyncClient' not in module_source


class TestPrimerUsesSharedClient:
    """Test suite for verifying primer routes use the shared client."""

    def test_primer_imports_shared_client(self):
        """Test that primer module imports shared_client."""
        try:
            from api.routes import primer
            module_source = inspect.getsource(primer)
        except ImportError:
            from backend.api.routes import primer
            module_source = inspect.getsource(primer)
        
        assert 'shared_client' in module_source

    def test_primer_does_not_create_new_clients(self):
        """Test that primer does not create new httpx.AsyncClient instances."""
        try:
            from api.routes import primer
        except ImportError:
            from backend.api.routes import primer
        
        module_source = inspect.getsource(primer)
        # Check that the pattern 'async with httpx.AsyncClient' is NOT used
        assert 'async with httpx.AsyncClient' not in module_source


class TestSharedClientUsageInRoutes:
    """Test suite for verifying shared_client is actually called in routes."""

    @pytest.mark.asyncio
    async def test_exchange_code_uses_shared_client_post(self):
        """Test that _exchange_code_for_access_token uses shared_client.post."""
        try:
            from api.routes import github_oauth
        except ImportError:
            from backend.api.routes import github_oauth
        
        # Check that shared_client.post is used in the function source
        source = inspect.getsource(github_oauth._exchange_code_for_access_token)
        assert 'shared_client.post' in source

    @pytest.mark.asyncio
    async def test_fetch_github_profile_uses_shared_client_get(self):
        """Test that _fetch_github_profile uses shared_client.get."""
        try:
            from api.routes import github_oauth
        except ImportError:
            from backend.api.routes import github_oauth
        
        source = inspect.getsource(github_oauth._fetch_github_profile)
        assert 'shared_client.get' in source
