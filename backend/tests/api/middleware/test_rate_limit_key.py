"""Tests for the rate limit key function in rate_limit.py"""

from unittest.mock import MagicMock

import pytest

from api.middleware.rate_limit import _get_rate_limit_key


class TestGetRateLimitKey:
    """Test cases for _get_rate_limit_key function."""

    def test_returns_user_id_when_authenticated(self):
        """When user_id exists in request.state, it should be used as the key."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user_12345"
        
        result = _get_rate_limit_key(mock_request)
        
        assert result == "user_12345"

    def test_returns_ip_address_when_not_authenticated(self):
        """When user_id is not present, should fall back to IP address."""
        mock_request = MagicMock()
        mock_request.state.user_id = None
        
        result = _get_rate_limit_key(mock_request)
        
        # Should call get_remote_address with the request
        assert result == "127.0.0.1"

    def test_returns_ip_address_when_user_id_missing(self):
        """When user_id attribute doesn't exist on request.state."""
        mock_request = MagicMock()
        # Explicitly remove user_id from state
        del mock_request.state.user_id
        
        result = _get_rate_limit_key(mock_request)
        
        # Should fall back to IP address
        assert result == "127.0.0.1"

    def test_uses_get_remote_address_fallback(self):
        """Verify get_remote_address is called as fallback for unauthenticated requests."""
        from slowapi.util import get_remote_address
        
        mock_request = MagicMock()
        mock_request.state.user_id = None
        
        result = _get_rate_limit_key(mock_request)
        
        # The function should call get_remote_address(request)
        assert result == get_remote_address(mock_request)

    def test_user_id_type_string(self):
        """User ID should be returned as string."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        
        result = _get_rate_limit_key(mock_request)
        
        assert isinstance(result, str)
        assert result == "test_user"

    def test_getattr_with_default_none(self):
        """Verify getattr is used with default None for graceful handling."""
        mock_request = MagicMock(spec=["state"])
        # Create state without user_id attribute
        mock_request.state = MagicMock()
        
        # When user_id is not set, getattr should return None
        result = _get_rate_limit_key(mock_request)
        
        # Should fall back to IP address
        assert result == "127.0.0.1"
