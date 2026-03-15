"""Tests for FORGE bridge timeout handling.

These tests verify that the FORGE bridge properly handles timeout
exceptions when making HTTP calls to external services.

Test Location: tests/test_forge_bridge_timeout.py
Project: backend/services/forge_bridge.py
Framework: pytest
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from backend.services.forge_bridge import _poll_until_complete, _trigger_forge, ForgeRunResult
except ImportError:
    try:
        import sys
        from pathlib import Path
        # Add backend to path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from backend.services.forge_bridge import _poll_until_complete, _trigger_forge, ForgeRunResult
        else:
            raise ImportError("Could not import from any known path")
    except ImportError:
        # Try services path
        try:
            from services.forge_bridge import _poll_until_complete, _trigger_forge, ForgeRunResult
        except ImportError:
            raise ImportError("Could not import _poll_until_complete, _trigger_forge, ForgeRunResult from any known path")


class TestForgeBridgeTimeoutHandling:
    """Test suite for timeout handling in FORGE bridge."""

    @pytest.mark.asyncio
    async def test_poll_handles_asyncio_timeout_error(self):
        """Test that _poll_until_complete handles asyncio.TimeoutError gracefully.
        
        The fix adds a try/except block that catches asyncio.TimeoutError,
        logs a warning, and continues (retries) instead of failing.
        """
        with patch('backend.services.forge_bridge._http_get') as mock_get:
            # First call raises TimeoutError, second call returns valid result
            mock_get.side_effect = [
                asyncio.TimeoutError("Request timed out"),
                {"status": "completed", "result": "test"}
            ]
            
            result = await _poll_until_complete(
                agentfield_url="https://agentfield.example.com",
                execution_id="test-execution-123",
                api_key="test-key",
                timeout=60
            )
            
            # Should have retried after timeout and returned result on second attempt
            assert result is not None
            assert result.get("status") == "completed"

    @pytest.mark.asyncio
    async def test_poll_handles_multiple_timeout_errors(self):
        """Test that _poll_until_complete handles multiple consecutive timeout errors."""
        with patch('backend.services.forge_bridge._http_get') as mock_get:
            # First three calls raise TimeoutError, fourth returns valid result
            mock_get.side_effect = [
                asyncio.TimeoutError("Request timed out #1"),
                asyncio.TimeoutError("Request timed out #2"),
                asyncio.TimeoutError("Request timed out #3"),
                {"status": "completed", "result": "test"}
            ]
            
            result = await _poll_until_complete(
                agentfield_url="https://agentfield.example.com",
                execution_id="test-execution-123",
                api_key="test-key",
                timeout=60
            )
            
            # Should have retried after all timeouts and returned result
            assert result is not None
            assert result.get("status") == "completed"
            # Verify _http_get was called 4 times
            assert mock_get.call_count == 4

    @pytest.mark.asyncio
    async def test_trigger_forge_handles_timeout_on_trigger(self):
        """Test that _trigger_forge handles asyncio.TimeoutError during trigger HTTP POST.
        
        The fix returns a ForgeRunResult with status='error' and timeout message.
        """
        with patch('backend.services.forge_bridge._http_post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Timeout triggering FORGE")
            
            result = await _trigger_forge(
                agentfield_url="https://agentfield.example.com",
                repo_url="https://github.com/test/repo",
                scan_findings=[],
                api_key="test-key",
                timeout=60
            )
            
            # Should return ForgeRunResult with status='error' and timeout message
            assert isinstance(result, ForgeRunResult)
            assert result.status == "error"
            assert "Timeout" in result.error or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_trigger_forge_handles_timeout_during_poll(self):
        """Test that _trigger_forge handles asyncio.TimeoutError during polling phase.
        
        The fix catches timeout during polling and returns ForgeRunResult with status='timeout'.
        """
        with patch('backend.services.forge_bridge._http_post') as mock_post:
            # Mock successful trigger response
            mock_post.return_value = {
                "execution_id": "test-execution-123",
                "status": "started"
            }
            
            with patch('backend.services.forge_bridge._poll_until_complete') as mock_poll:
                mock_poll.side_effect = asyncio.TimeoutError("Polling timed out")
                
                result = await _trigger_forge(
                    agentfield_url="https://agentfield.example.com",
                    repo_url="https://github.com/test/repo",
                    scan_findings=[],
                    api_key="test-key",
                    timeout=60
                )
                
                # Should return ForgeRunResult with status='timeout'
                assert isinstance(result, ForgeRunResult)
                assert result.status == "timeout"
                assert "timeout" in result.error.lower() or "Polling" in result.error

    @pytest.mark.asyncio
    async def test_trigger_forge_success_after_timeout_then_success(self):
        """Test that trigger succeeds when first POST times out but retry succeeds."""
        with patch('backend.services.forge_bridge._http_post') as mock_post:
            # First call raises TimeoutError, second returns success
            mock_post.side_effect = [
                asyncio.TimeoutError("First request timed out"),
                {
                    "execution_id": "test-execution-123",
                    "status": "started"
                }
            ]
            
            with patch('backend.services.forge_bridge._poll_until_complete') as mock_poll:
                mock_poll.return_value = {
                    "status": "completed",
                    "result": {
                        "summary": "Success"
                    }
                }
                
                result = await _trigger_forge(
                    agentfield_url="https://agentfield.example.com",
                    repo_url="https://github.com/test/repo",
                    scan_findings=[],
                    api_key="test-key",
                    timeout=60
                )
                
                # Should succeed on retry
                assert result.status in ["completed", "success"]
