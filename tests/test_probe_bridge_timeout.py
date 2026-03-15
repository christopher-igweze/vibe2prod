"""Tests for Probe bridge timeout handling.

These tests verify that the Probe bridge properly handles timeout
exceptions when making HTTP calls to external services.

Test Location: tests/test_probe_bridge_timeout.py
Project: backend/services/probe_bridge.py
Framework: pytest
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from backend.services.probe_bridge import ProbeBridge, ProbeServiceResult
except ImportError:
    try:
        import sys
        from pathlib import Path
        # Add backend to path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from backend.services.probe_bridge import ProbeBridge, ProbeServiceResult
        else:
            raise ImportError("Could not import from any known path")
    except ImportError:
        # Try services path
        try:
            from services.probe_bridge import ProbeBridge, ProbeServiceResult
        except ImportError:
            raise ImportError("Could not import ProbeBridge, ProbeServiceResult from any known path")


class TestProbeBridgeTimeoutHandling:
    """Test suite for timeout handling in Probe bridge."""

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_httpx_timeout_exception(self):
        """Test that trigger_scan handles httpx.TimeoutException gracefully.
        
        The fix adds handling for httpx.TimeoutException and asyncio.TimeoutError
        in the trigger_scan method.
        """
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await bridge.trigger_scan("https://target.com", {})
            
            # Should return ProbeServiceResult with status='error'
            assert isinstance(result, ProbeServiceResult)
            assert result.status == "error"
            assert "timed out" in result.error.lower() or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_trigger_scan_handles_asyncio_timeout_error(self):
        """Test that trigger_scan handles asyncio.TimeoutError gracefully."""
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Async timeout")
            
            result = await bridge.trigger_scan("https://target.com", {})
            
            # Should return ProbeServiceResult with status='error'
            assert isinstance(result, ProbeServiceResult)
            assert result.status == "error"
            assert "timed out" in result.error.lower() or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_get_scan_status_handles_httpx_timeout_exception(self):
        """Test that get_scan_status handles httpx.TimeoutException gracefully.
        
        The fix adds handling for httpx.TimeoutException and asyncio.TimeoutError
        in the get_scan_status method.
        """
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await bridge.get_scan_status("job-123")
            
            # Should return dict with status='error'
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_get_scan_status_handles_asyncio_timeout_error(self):
        """Test that get_scan_status handles asyncio.TimeoutError gracefully."""
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Async timeout")
            
            result = await bridge.get_scan_status("job-123")
            
            # Should return dict with status='error'
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_get_scan_results_handles_httpx_timeout_exception(self):
        """Test that get_scan_results handles httpx.TimeoutException gracefully.
        
        The fix adds handling for httpx.TimeoutException and asyncio.TimeoutError
        in the get_scan_results method.
        """
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await bridge.get_scan_results("job-123")
            
            # Should return dict with status='error'
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_get_scan_results_handles_asyncio_timeout_error(self):
        """Test that get_scan_results handles asyncio.TimeoutError gracefully."""
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = asyncio.TimeoutError("Async timeout")
            
            result = await bridge.get_scan_results("job-123")
            
            # Should return dict with status='error'
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_cancel_scan_handles_httpx_timeout_exception(self):
        """Test that cancel_scan handles httpx.TimeoutException gracefully.
        
        The fix adds handling for httpx.TimeoutException and asyncio.TimeoutError
        in the cancel_scan method.
        """
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = httpx.TimeoutException("Request timed out")
            
            result = await bridge.cancel_scan("job-123")
            
            # Should return dict with status='error'
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_cancel_scan_handles_asyncio_timeout_error(self):
        """Test that cancel_scan handles asyncio.TimeoutError gracefully."""
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        with patch.object(bridge, '_delete', new_callable=AsyncMock) as mock_delete:
            mock_delete.side_effect = asyncio.TimeoutError("Async timeout")
            
            result = await bridge.cancel_scan("job-123")
            
            # Should return dict with status='error'
            assert isinstance(result, dict)
            assert result.get("status") == "error"
            assert "timed out" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()

    def test_bridge_uses_httpx_timeout_object(self):
        """Test that ProbeBridge uses httpx.Timeout object for explicit timeout control.
        
        The fix changes timeout from int to httpx.Timeout object.
        """
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key", timeout=30.0)
        
        # Verify that timeout is an httpx.Timeout object
        assert isinstance(bridge.timeout, httpx.Timeout)
        # Verify timeout values are set correctly
        assert bridge.timeout.connect == 30.0
        assert bridge.timeout.read == 30.0
        assert bridge.timeout.write == 30.0
        assert bridge.timeout.pool == 30.0

    def test_bridge_default_timeout_value(self):
        """Test that ProbeBridge has correct default timeout value."""
        from backend.services.probe_bridge import DEFAULT_TIMEOUT
        
        bridge = ProbeBridge(service_url="https://probe.example.com", api_key="test-key")
        
        # Verify default timeout is used
        assert bridge.timeout.connect == DEFAULT_TIMEOUT
        assert bridge.timeout.read == DEFAULT_TIMEOUT
