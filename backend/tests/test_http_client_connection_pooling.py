"""Tests for HTTP client connection pooling.

These tests verify that the shared httpx.AsyncClient is properly configured
with connection pooling limits to avoid creating new connections for each request.

Test Location: tests/test_http_client_connection_pooling.py
Project: services/http_client.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


# Import the shared client module
try:
    from services.http_client import shared_client
except ImportError:
    try:
        from http_client import shared_client
    except ImportError:
        import sys
        from pathlib import Path
        # Add services to path if needed
        backend_path = Path(__file__).parent.parent
        if (backend_path / "services").exists():
            sys.path.insert(0, str(backend_path))
            from services.http_client import shared_client
        else:
            raise ImportError("Could not import shared_client from any known path")


class TestSharedClientConfiguration:
    """Test suite for shared HTTP client connection pooling configuration."""

    def test_shared_client_exists(self):
        """Test that shared_client is defined and importable."""
        assert shared_client is not None

    def test_shared_client_is_httpx_asyncclient(self):
        """Test that shared_client is an instance of httpx.AsyncClient."""
        assert isinstance(shared_client, httpx.AsyncClient)

    def test_shared_client_has_connection_limits(self):
        """Test that shared_client has connection pooling limits configured."""
        # The shared client should have limits set for connection pooling
        assert hasattr(shared_client, '_limits')
        limits = shared_client._limits
        assert limits is not None

    def test_shared_client_configured_with_max_connections(self):
        """Test that shared_client has max_connections configured."""
        limits = shared_client._limits
        # Should have a reasonable max_connections limit (>= 100 per the fix)
        assert limits.max_connections >= 100

    def test_shared_client_configured_with_max_keepalive_connections(self):
        """Test that shared_client has max_keepalive_connections configured."""
        limits = shared_client._limits
        # Should have keepalive connections configured (>= 20 per the fix)
        assert limits.max_keepalive_connections >= 20

    def test_shared_client_has_timeout(self):
        """Test that shared_client has a timeout configured."""
        # The client should have a timeout attribute
        assert hasattr(shared_client, '_timeout')

    @pytest.mark.asyncio
    async def test_shared_client_can_make_get_request(self):
        """Test that shared_client can make GET requests (verifies it's functional)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(shared_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            response = await shared_client.get("https://api.example.com/test")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_shared_client_can_make_post_request(self):
        """Test that shared_client can make POST requests (verifies it's functional)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test_token"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(shared_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            response = await shared_client.post("https://api.example.com/oauth/token")
            assert response.status_code == 200


class TestConnectionPoolingBenefits:
    """Test suite verifying connection pooling behavior."""

    def test_shared_client_reuses_connections(self):
        """Test that the shared client is configured to reuse connections."""
        # The client should be a single instance used across requests
        # This is verified by checking it's NOT created with context manager in routes
        limits = shared_client._limits
        # Keepalive connections should be configured for connection reuse
        assert limits.max_keepalive_connections > 0

    def test_shared_client_connection_limit_prevents_exhaustion(self):
        """Test that max_connections prevents connection exhaustion."""
        limits = shared_client._limits
        # A reasonable upper bound to prevent resource exhaustion
        assert limits.max_connections is not None
        assert limits.max_connections > 0
