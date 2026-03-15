"""Tests for global exception handler security fixes.

These tests verify that the global_exception_handler in main.py properly
prevents information leakage to unauthenticated users by:
1. Not exposing request_id in error responses to clients
2. Not including user_id in logs when user is unauthenticated (None)
3. Properly logging exceptions with appropriate context

Test Location: tests/test_global_exception_handler_security.py
Project: backend/main.py
Framework: pytest
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.datastructures import URL

# Import the handler function - try multiple import paths
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
            raise ImportError("Could not import global_exception_handler")


def create_mock_request(request_id: str = "test-request-id", user_id: str = None) -> MagicMock:
    """Create a mock Request object with optional request_id and user_id."""
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url = URL("http://test.com/test")
    
    # Use a simple object to hold state attributes
    state = MagicMock()
    state.request_id = request_id
    state.user_id = user_id
    request.state = state
    
    return request


class TestGlobalExceptionHandlerSecurity:
    """Test suite for security fixes in global exception handler."""

    @pytest.mark.asyncio
    async def test_error_response_does_not_include_request_id(self):
        """Test that error response does not expose request_id to clients.
        
        This verifies the fix for CWE-209 (Information Exposure Through Error Message).
        The request_id is used internally for tracing but should not be exposed to clients.
        """
        request = create_mock_request(request_id="internal-trace-123")
        exc = Exception("Test error")
        
        response = await global_exception_handler(request, exc)
        
        # Response should be a JSONResponse with status 500
        assert response.status_code == 500
        
        # Load the response content
        import json
        content = json.loads(response.body)
        
        # request_id should NOT be in the response - this is the security fix
        assert "request_id" not in content, "request_id should not be exposed to clients"
        
        # Should still have the generic error message
        assert content.get("detail") == "Internal server error"

    @pytest.mark.asyncio
    async def test_error_response_does_not_include_user_id(self):
        """Test that error response does not expose user_id to clients."""
        request = create_mock_request(request_id="trace-456", user_id="user-789")
        exc = Exception("Test error for authenticated user")
        
        response = await global_exception_handler(request, exc)
        
        import json
        content = json.loads(response.body)
        
        # user_id should NOT be in the response
        assert "user_id" not in content, "user_id should not be exposed to clients"
        assert content.get("detail") == "Internal server error"

    @pytest.mark.asyncio
    async def test_http_exception_response_preserved(self):
        """Test that HTTPException responses are still handled properly."""
        request = create_mock_request()
        exc = HTTPException(status_code=404, detail="Not found")
        
        response = await global_exception_handler(request, exc)
        
        assert response.status_code == 404
        import json
        content = json.loads(response.body)
        assert content.get("detail") == "Not found"
        # HTTPException should not include request_id either
        assert "request_id" not in content

    @pytest.mark.asyncio
    async def test_base_exception_group_with_http_exception(self):
        """Test that BaseExceptionGroup wrapping HTTPException is handled properly."""
        request = create_mock_request()
        inner_exc = HTTPException(status_code=400, detail="Bad request")
        exc = BaseExceptionGroup("group", [inner_exc])
        
        response = await global_exception_handler(request, exc)
        
        assert response.status_code == 400
        import json
        content = json.loads(response.body)
        assert content.get("detail") == "Bad request"
        assert "request_id" not in content

    @pytest.mark.asyncio
    async def test_base_exception_group_with_generic_exception(self):
        """Test that BaseExceptionGroup with generic exception returns 500."""
        request = create_mock_request()
        inner_exc = ValueError("Some value error")
        exc = BaseExceptionGroup("group", [inner_exc])
        
        response = await global_exception_handler(request, exc)
        
        assert response.status_code == 500
        import json
        content = json.loads(response.body)
        assert content.get("detail") == "Internal server error"
        assert "request_id" not in content

    @pytest.mark.asyncio
    async def test_unauthenticated_user_logs_without_user_id(self):
        """Test that logging does not include user_id when user is None (unauthenticated)."""
        request = create_mock_request(request_id="trace-789", user_id=None)
        exc = Exception("Test error for unauthenticated user")
        
        with patch('main.logger') as mock_logger:
            await global_exception_handler(request, exc)
            
            # Verify logger was called
            assert mock_logger.error.called
            
            # Get the log message
            call_args = mock_logger.error.call_args
            log_message = call_args[0][0] if call_args[0] else str(call_args)
            
            # user_id should NOT appear in the log message when it's None
            # The fix uses: f" user_id={user_id}" if user_id else ""
            assert "user_id=None" not in log_message, "user_id should not be logged when None"
            assert "user_id=" not in log_message or "user_id=None" not in log_message

    @pytest.mark.asyncio
    async def test_authenticated_user_logs_include_user_id(self):
        """Test that logging includes user_id when user is authenticated (not None)."""
        request = create_mock_request(request_id="trace-101", user_id="user-123")
        exc = Exception("Test error for authenticated user")
        
        with patch('main.logger') as mock_logger:
            await global_exception_handler(request, exc)
            
            # Verify logger was called
            assert mock_logger.error.called
            
            # Get the log message
            call_args = mock_logger.error.call_args
            log_message = call_args[0][0] if call_args[0] else str(call_args)
            
            # user_id SHOULD appear in the log message when it's not None
            assert "user_id=user-123" in log_message, "user_id should be logged when authenticated"

    @pytest.mark.asyncio
    async def test_response_contains_only_detail(self):
        """Test that response contains only 'detail' key, nothing else."""
        request = create_mock_request(request_id="secret-trace-999", user_id="secret-user")
        exc = Exception("Sensitive error")
        
        response = await global_exception_handler(request, exc)
        
        import json
        content = json.loads(response.body)
        
        # Response should ONLY have 'detail' key - no internal tracking info
        assert list(content.keys()) == ["detail"], "Response should only contain 'detail' key"
        assert content.get("detail") == "Internal server error"
