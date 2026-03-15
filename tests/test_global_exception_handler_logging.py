"""Tests for global exception handler logging behavior.

These tests verify that the global_exception_handler in main.py properly
conditionally logs exceptions based on the debug setting (CWE-532).

In debug mode: logger.exception() is used (includes stack trace for debugging)
In production: logger.error() is used (sanitized, no stack trace)

Test Location: tests/test_global_exception_handler_logging.py
Project: backend/main.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from fastapi.responses import JSONResponse


# Import the global_exception_handler function from backend.main
# Try multiple import paths to handle different project layouts
try:
    from backend.main import global_exception_handler
except ImportError:
    try:
        from main import global_exception_handler
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from main import global_exception_handler
        else:
            raise ImportError("Could not import global_exception_handler from any known path")


class TestGlobalExceptionHandlerLogging:
    """Test suite for global exception handler logging behavior."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock Request object."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock()
        request.url.__str__ = lambda self: "http://test.com/api/test"
        request.state = MagicMock()
        request.state.request_id = "test-request-id"
        request.state.user_id = None
        return request

    @pytest.mark.asyncio
    async def test_debug_mode_uses_logger_exception(self, mock_request):
        """Test that logger.exception() is called in debug mode."""
        test_exception = ValueError("Test error message")
        
        with patch('backend.main.settings') as mock_settings, \
             patch('backend.main.logger') as mock_logger:
            
            mock_settings.debug = True
            
            # Call the exception handler
            response = await global_exception_handler(mock_request, test_exception)
            
            # Verify logger.exception was called (includes stack trace in debug)
            mock_logger.exception.assert_called_once()
            
            # Verify the call contains expected context
            call_args = mock_logger.exception.call_args
            assert "Unhandled exception" in call_args[0][0]
            assert mock_request.method in call_args[0]
            
            # Verify response is correct
            assert response.status_code == 500
            assert response.body is not None

    @pytest.mark.asyncio
    async def test_production_mode_uses_logger_error(self, mock_request):
        """Test that logger.error() is called in production (non-debug) mode."""
        test_exception = ValueError("Test error message")
        
        with patch('backend.main.settings') as mock_settings, \
             patch('backend.main.logger') as mock_logger:
            
            mock_settings.debug = False
            
            # Call the exception handler
            response = await global_exception_handler(mock_request, test_exception)
            
            # Verify logger.error was called (not exception - no stack trace in production)
            mock_logger.error.assert_called_once()
            
            # Verify the call contains expected context
            call_args = mock_logger.error.call_args
            assert "Unhandled exception" in call_args[0][0]
            assert mock_request.method in call_args[0]
            
            # Verify exception type and message are included (but NOT the stack trace)
            assert "ValueError" in call_args[0][0]
            assert "Test error message" in call_args[0][0]
            
            # Verify response is correct
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_production_mode_does_not_include_stack_trace(self, mock_request):
        """Test that production mode logging does NOT include stack trace."""
        test_exception = RuntimeError("Sensitive operation failed")
        
        with patch('backend.main.settings') as mock_settings, \
             patch('backend.main.logger') as mock_logger:
            
            mock_settings.debug = False
            
            # Call the exception handler
            await global_exception_handler(mock_request, test_exception)
            
            # Verify logger.error was called
            mock_logger.error.assert_called_once()
            
            # Verify logger.exception was NOT called (would include stack trace)
            mock_logger.exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_debug_mode_includes_full_context(self, mock_request):
        """Test that debug mode includes full context including stack trace."""
        test_exception = KeyError("missing_key")
        
        with patch('backend.main.settings') as mock_settings, \
             patch('backend.main.logger') as mock_logger:
            
            mock_settings.debug = True
            
            # Call the exception handler
            await global_exception_handler(mock_request, test_exception)
            
            # Verify logger.exception was called
            mock_logger.exception.assert_called_once()
            
            # Verify request context is included
            call_args = mock_logger.exception.call_args
            assert "GET" in call_args[0]
            assert "test-request-id" in call_args[0]
