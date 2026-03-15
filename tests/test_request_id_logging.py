"""Tests for request ID logging improvements.

These tests verify that the RequestIDMiddleware properly generates unique
request IDs and that the global exception handler includes request context
(user_id, request_id) in error logs for better traceability.

Test Location: tests/test_request_id_logging.py
Project: backend/main.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

# Import using relative path based on project structure
try:
    from backend.main import RequestIDMiddleware, global_exception_handler, handle_cancelled_error
except ImportError:
    import sys
    from pathlib import Path
    # Add parent to path if needed
    parent_path = Path(__file__).parent.parent
    if str(parent_path) not in sys.path:
        sys.path.insert(0, str(parent_path))
    from backend.main import RequestIDMiddleware, global_exception_handler, handle_cancelled_error


class TestRequestIDMiddleware:
    """Test suite for RequestIDMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_generates_request_id(self):
        """Test that middleware generates a unique request ID for each request."""
        # Create mock app for middleware
        mock_app = MagicMock()
        middleware = RequestIDMiddleware(app=mock_app)
        
        # Create mock request with state attribute
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.headers = MagicMock()
        
        # Mock call_next
        call_next = AsyncMock(return_value=mock_response)
        
        await middleware.dispatch(mock_request, call_next)
        
        # Verify request_id was set on request.state
        assert hasattr(mock_request.state, 'request_id')
        assert mock_request.state.request_id is not None
        assert len(mock_request.state.request_id) == 8

    @pytest.mark.asyncio
    async def test_middleware_adds_header_to_response(self):
        """Test that middleware adds X-Request-ID header to response."""
        mock_app = MagicMock()
        middleware = RequestIDMiddleware(app=mock_app)
        
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        
        # Track headers that are set
        header_dict = {}
        mock_response = MagicMock()
        mock_response.headers = MagicMock()
        mock_response.headers.__setitem__ = lambda k, v: header_dict.update({k: v})
        
        call_next = AsyncMock(return_value=mock_response)
        
        await middleware.dispatch(mock_request, call_next)
        
        # Verify X-Request-ID header was added
        assert "X-Request-ID" in header_dict
        assert len(header_dict["X-Request-ID"]) == 8

    @pytest.mark.asyncio
    async def test_middleware_generates_unique_ids(self):
        """Test that each request gets a unique ID."""
        mock_app = MagicMock()
        middleware = RequestIDMiddleware(app=mock_app)
        
        request_ids = set()
        
        for _ in range(10):
            mock_request = MagicMock()
            mock_request.state = MagicMock()
            mock_response = MagicMock()
            mock_response.headers = MagicMock()
            
            call_next = AsyncMock(return_value=mock_response)
            
            await middleware.dispatch(mock_request, call_next)
            request_ids.add(mock_request.state.request_id)
        
        # All request IDs should be unique
        assert len(request_ids) == 10


class TestGlobalExceptionHandler:
    """Test suite for global exception handler request context logging."""

    @pytest.mark.asyncio
    async def test_exception_handler_includes_request_id_in_log(self):
        """Test that exception handler includes request_id in log message."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.request_id = "test-1234"
        mock_request.state.user_id = None
        mock_request.method = "GET"
        mock_request.url = MagicMock()
        mock_request.url.__str__ = lambda self: "http://test.com/api"
        
        # Mock the _sanitize_url function
        with patch('backend.main._sanitize_url', return_value="http://test.com/api"):
            with patch('backend.main.logger') as mock_logger:
                exc = Exception("Test error")
                
                response = await global_exception_handler(mock_request, exc)
                
                # Verify the log was called with request_id
                mock_logger.exception.assert_called_once()
                call_args = mock_logger.exception.call_args[0]
                assert "request_id=test-1234" in call_args[0]
                
                # Verify response contains request_id
                assert response.status_code == 500
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                import json
                response_data = json.loads(body)
                assert "request_id" in response_data
                assert response_data["request_id"] == "test-1234"

    @pytest.mark.asyncio
    async def test_exception_handler_includes_user_id_in_log(self):
        """Test that exception handler includes user_id in log message when available."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.request_id = "test-5678"
        mock_request.state.user_id = "user-abc-123"
        mock_request.method = "POST"
        mock_request.url = MagicMock()
        mock_request.url.__str__ = lambda self: "http://test.com/api"
        
        with patch('backend.main._sanitize_url', return_value="http://test.com/api"):
            with patch('backend.main.logger') as mock_logger:
                exc = Exception("Test error")
                
                response = await global_exception_handler(mock_request, exc)
                
                # Verify the log was called with user_id
                mock_logger.exception.assert_called_once()
                call_args = mock_logger.exception.call_args[0]
                assert "user_id=user-abc-123" in call_args[0]

    @pytest.mark.asyncio
    async def test_exception_handler_handles_missing_request_id(self):
        """Test that exception handler handles missing request_id gracefully."""
        mock_request = MagicMock()
        # Don't set request_id on state
        mock_request.state = MagicMock()
        mock_request.method = "GET"
        mock_request.url = MagicMock()
        mock_request.url.__str__ = lambda self: "http://test.com/api"
        
        with patch('backend.main._sanitize_url', return_value="http://test.com/api"):
            with patch('backend.main.logger') as mock_logger:
                exc = Exception("Test error")
                
                response = await global_exception_handler(mock_request, exc)
                
                # Verify it uses "unknown" as fallback
                call_args = mock_logger.exception.call_args[0]
                assert "request_id=unknown" in call_args[0]


class TestHandleCancelledError:
    """Test suite for handle_cancelled_error request ID logging."""

    @pytest.mark.asyncio
    async def test_cancelled_error_includes_request_id_in_log(self):
        """Test that cancelled error handler includes request_id in log message."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.request_id = "cancel-1234"
        mock_request.method = "DELETE"
        mock_request.url = MagicMock()
        mock_request.url.__str__ = lambda self: "http://test.com/api/resource"
        
        exc = asyncio.CancelledError()
        
        with patch('backend.main._sanitize_url', return_value="http://test.com/api/resource"):
            with patch('backend.main.logger') as mock_logger:
                # Should re-raise the CancelledError
                with pytest.raises(asyncio.CancelledError):
                    await handle_cancelled_error(mock_request, exc)
                
                # Verify the log was called with request_id
                mock_logger.warning.assert_called_once()
                call_args = mock_logger.warning.call_args[0]
                assert "request_id=cancel-1234" in call_args[0]

    @pytest.mark.asyncio
    async def test_cancelled_error_handles_missing_request_id(self):
        """Test that cancelled error handler handles missing request_id gracefully."""
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        # Don't set request_id
        mock_request.method = "GET"
        mock_request.url = MagicMock()
        mock_request.url.__str__ = lambda self: "http://test.com/api"
        
        exc = asyncio.CancelledError()
        
        with patch('backend.main._sanitize_url', return_value="http://test.com/api"):
            with patch('backend.main.logger') as mock_logger:
                with pytest.raises(asyncio.CancelledError):
                    await handle_cancelled_error(mock_request, exc)
                
                # Verify it uses "unknown" as fallback
                call_args = mock_logger.warning.call_args[0]
                assert "request_id=unknown" in call_args[0]


import asyncio
