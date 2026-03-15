"""Tests for GitHub service error handling improvements.

These tests verify that the get_head_sha method properly handles various
network failures (Timeout, DNS resolution, SSL errors, connection errors).

Test Location: tests/test_github_error_handling.py
Project: services/github.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from services.github import get_head_sha
except ImportError:
    try:
        from github import get_head_sha
    except ImportError:
        import sys
        from pathlib import Path
        # Add services to path if needed
        services_path = Path(__file__).parent.parent / "services"
        if services_path.exists():
            sys.path.insert(0, str(services_path.parent))
            from github import get_head_sha
        else:
            raise ImportError("Could not import get_head_sha from any known path")


class TestGetHeadShaErrorHandling:
    """Test suite for get_head_sha error handling in GitHub service."""

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_timeout_exception(self):
        """Test that get_head_sha handles httpx.TimeoutException gracefully."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await get_head_sha("owner", "repo", "main", "token123")
            
            # Should return a dict with error information, not raise exception
            assert isinstance(result, dict)
            assert "error" in result or result.get("error") is not None

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_connect_error(self):
        """Test that get_head_sha handles httpx.ConnectError gracefully."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await get_head_sha("owner", "repo", "main", "token123")
            
            assert isinstance(result, dict)
            assert "error" in result or result.get("error") is not None

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_request_error(self):
        """Test that get_head_sha handles httpx.RequestError gracefully."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Request failed")
            
            result = await get_head_sha("owner", "repo", "main", "token123")
            
            assert isinstance(result, dict)
            assert "error" in result or result.get("error") is not None

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_dns_error(self):
        """Test that get_head_sha handles DNS resolution errors gracefully."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("DNS resolution failed")
            
            result = await get_head_sha("owner", "repo", "main", "token123")
            
            assert isinstance(result, dict)
            assert "error" in result or result.get("error") is not None

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_generic_exception(self):
        """Test that get_head_sha handles unexpected exceptions gracefully."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Unexpected error")
            
            result = await get_head_sha("owner", "repo", "main", "token123")
            
            assert isinstance(result, dict)
            assert "error" in result or result.get("error") is not None
