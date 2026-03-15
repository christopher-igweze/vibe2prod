"""Tests for ProbeBridge error handling improvements.

These tests verify that the trigger_scan method properly handles various
network failures (Timeout, DNS resolution, SSL errors) in addition to
ConnectionError.

Test Location: tests/test_probe_bridge_error_handling.py
Project: probe_bridge
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx

# Import using relative path based on project structure
# Try to import from the probe_bridge module directly
try:
    from probe_bridge import ProbeBridge, ProbeServiceResult
except ImportError:
    # Fallback for different project structures
    from probe_bridge.probe_bridge import ProbeBridge, ProbeServiceResult


class TestProbeBridgeErrorHandling:
    """Test suite for ProbeBridge error handling in trigger_scan method."""

    @pytest.fixture
    def probe_bridge(self):
        """Create a ProbeBridge instance for testing."""
        return ProbeBridge(base_url="http://test.example.com")

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_timeout_exception(self, probe_bridge):
        """Test that trigger_scan handles httpx.TimeoutException gracefully."""
        with patch.object(probe_bridge, '_post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await probe_bridge.trigger_scan("http://example.com", {})
            
            assert result.status == "error"
            assert "Timeout" in result.error or "timed out" in result.error.lower()
            assert result.job_id == ""

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_connect_error(self, probe_bridge):
        """Test that trigger_scan handles httpx.ConnectError gracefully."""
        with patch.object(probe_bridge, '_post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")
            
            result = await probe_bridge.trigger_scan("http://example.com", {})
            
            assert result.status == "error"
            assert "connect" in result.error.lower() or "connection" in result.error.lower()
            assert result.job_id == ""

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_request_error(self, probe_bridge):
        """Test that trigger_scan handles httpx.RequestError gracefully."""
        with patch.object(probe_bridge, '_post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Request failed")
            
            result = await probe_bridge.trigger_scan("http://example.com", {})
            
            assert result.status == "error"
            assert result.job_id == ""

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_dns_error(self, probe_bridge):
        """Test that trigger_scan handles DNS resolution errors gracefully."""
        with patch.object(probe_bridge, '_post', new_callable=AsyncMock) as mock_post:
            # DNS resolution errors typically manifest as ConnectError
            mock_post.side_effect = httpx.ConnectError("DNS resolution failed for example.com")
            
            result = await probe_bridge.trigger_scan("http://example.com", {})
            
            assert result.status == "error"
            assert result.job_id == ""

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_ssl_error(self, probe_bridge):
        """Test that trigger_scan handles SSL errors gracefully."""
        with patch.object(probe_bridge, '_post', new_callable=AsyncMock) as mock_post:
            # SSL errors are a subclass of RequestError in httpx
            mock_post.side_effect = httpx.RequestError("SSL verification failed")
            
            result = await probe_bridge.trigger_scan("http://example.com", {})
            
            assert result.status == "error"
            assert result.job_id == ""

    @pytest.mark.asyncio
    async def test_trigger_scan_success_case(self, probe_bridge):
        """Test that trigger_scan works correctly for successful requests."""
        with patch.object(probe_bridge, '_post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"job_id": "12345", "status": "submitted"}
            
            result = await probe_bridge.trigger_scan("http://example.com", {})
            
            assert result.status == "submitted"
            assert result.job_id == "12345"
            assert result.error is None or result.error == ""
