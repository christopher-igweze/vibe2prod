"""Tests for rate limiting middleware improvements.

These tests verify that the rate_limit module provides meaningful rate limiting
functionality using a sliding window algorithm with support for different limits
per endpoint type.

Test Location: tests/test_rate_limit.py
Framework: pytest
"""

import pytest
import time
import sys
import os
from unittest.mock import MagicMock, patch

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from api.middleware.rate_limit import (
    SlidingWindowCounter,
    RateLimitStorage,
    _get_rate_limit_key,
    _get_endpoint_category,
    get_rate_limit_config,
    rate_limit_key_with_category,
    check_rate_limit,
)


class TestSlidingWindowCounter:
    """Test suite for SlidingWindowCounter class."""

    def test_is_allowed_first_request(self):
        """Test that first request within limit is allowed."""
        counter = SlidingWindowCounter()
        is_allowed, remaining, reset_time = counter.is_allowed(window_seconds=60, max_requests=10)
        
        assert is_allowed is True
        assert remaining == 9
        assert reset_time > 0

    def test_is_allowed_at_limit(self):
        """Test that requests at limit are still allowed."""
        counter = SlidingWindowCounter()
        
        # Make 10 requests (up to limit)
        for i in range(10):
            is_allowed, remaining, reset_time = counter.is_allowed(window_seconds=60, max_requests=10)
            assert is_allowed is True
        
        # 11th request should be denied
        is_allowed, remaining, reset_time = counter.is_allowed(window_seconds=60, max_requests=10)
        assert is_allowed is False
        assert remaining == 0

    def test_is_allowed_exceeds_limit(self):
        """Test that requests exceeding limit are denied."""
        counter = SlidingWindowCounter()
        
        # Fill up to limit
        for _ in range(10):
            counter.is_allowed(window_seconds=60, max_requests=10)
        
        # Exceed limit
        is_allowed, remaining, reset_time = counter.is_allowed(window_seconds=60, max_requests=10)
        
        assert is_allowed is False
        assert remaining == 0
        assert reset_time > int(time.time())

    def test_is_allowed_window_expiration(self):
        """Test that requests are allowed after window expires."""
        counter = SlidingWindowCounter()
        
        # Make request
        counter.is_allowed(window_seconds=1, max_requests=1)
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        is_allowed, remaining, reset_time = counter.is_allowed(window_seconds=1, max_requests=1)
        
        assert is_allowed is True

    def test_is_allowed_thread_safety(self):
        """Test that counter is thread-safe."""
        import threading
        counter = SlidingWindowCounter()
        results = []
        
        def make_request():
            is_allowed, _, _ = counter.is_allowed(window_seconds=60, max_requests=100)
            results.append(is_allowed)
        
        threads = [threading.Thread(target=make_request) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All requests should be counted correctly
        allowed_count = sum(1 for r in results if r)
        assert allowed_count == 50


class TestRateLimitStorage:
    """Test suite for RateLimitStorage class."""

    @pytest.fixture
    def storage(self):
        """Create a fresh RateLimitStorage instance."""
        return RateLimitStorage()

    def test_check_rate_limit_allows_first_request(self, storage):
        """Test that first request is allowed."""
        is_allowed, remaining, reset_time = storage.check_rate_limit("test_key", 60, 10)
        
        assert is_allowed is True
        assert remaining == 9

    def test_check_rate_limit_tracks_per_key(self, storage):
        """Test that rate limits are tracked per unique key."""
        # Fill up limit for key1
        for _ in range(10):
            is_allowed, _, _ = storage.check_rate_limit("key1", 60, 10)
        
        # key1 should be blocked
        is_allowed, _, _ = storage.check_rate_limit("key1", 60, 10)
        assert is_allowed is False
        
        # key2 should still be allowed (separate key)
        is_allowed, _, _ = storage.check_rate_limit("key2", 60, 10)
        assert is_allowed is True

    def test_check_rate_limit_different_configs(self, storage):
        """Test rate limits with different window and max requests."""
        # Use smaller limit
        for _ in range(5):
            storage.check_rate_limit("key", 60, 5)
        
        is_allowed, remaining, _ = storage.check_rate_limit("key", 60, 5)
        assert is_allowed is False
        assert remaining == 0


class TestGetRateLimitKey:
    """Test suite for _get_rate_limit_key function."""

    def test_returns_user_id_when_authenticated(self):
        """Test that user_id is returned when present in request state."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user_123"
        
        result = _get_rate_limit_key(mock_request)
        
        assert result == "user_123"

    def test_returns_ip_when_not_authenticated(self):
        """Test that IP address is returned when no user_id."""
        mock_request = MagicMock()
        mock_request.state.user_id = None
        mock_request.headers = {}
        
        result = _get_rate_limit_key(mock_request)
        
        assert result == "127.0.0.1"

    def test_returns_ip_for_empty_user_id(self):
        """Test that IP is returned when user_id is empty string."""
        mock_request = MagicMock()
        mock_request.state.user_id = ""
        mock_request.headers = {}
        
        result = _get_rate_limit_key(mock_request)
        
        assert result == "127.0.0.1"


class TestGetEndpointCategory:
    """Test suite for _get_endpoint_category function."""

    def test_category_auth_for_login(self):
        """Test that /login path returns 'auth' category."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.method = "POST"
        
        result = _get_endpoint_category(mock_request)
        
        assert result == "auth"

    def test_category_auth_for_oauth(self):
        """Test that /oauth path returns 'auth' category."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/oauth/token"
        mock_request.method = "POST"
        
        result = _get_endpoint_category(mock_request)
        
        assert result == "auth"

    def test_category_write_for_post(self):
        """Test that POST method returns 'write' category."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/items"
        mock_request.method = "POST"
        
        result = _get_endpoint_category(mock_request)
        
        assert result == "write"

    def test_category_write_for_put(self):
        """Test that PUT method returns 'write' category."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/items/1"
        mock_request.method = "PUT"
        
        result = _get_endpoint_category(mock_request)
        
        assert result == "write"

    def test_category_write_for_delete(self):
        """Test that DELETE method returns 'write' category."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/items/1"
        mock_request.method = "DELETE"
        
        result = _get_endpoint_category(mock_request)
        
        assert result == "write"

    def test_category_read_for_get(self):
        """Test that GET method returns 'read' category."""
        mock_request = MagicMock()
        mock_request.url.path = "/api/items"
        mock_request.method = "GET"
        
        result = _get_endpoint_category(mock_request)
        
        assert result == "read"


class TestGetRateLimitConfig:
    """Test suite for get_rate_limit_config function."""

    @patch('api.middleware.rate_limit.settings')
    def test_config_auth_endpoint_strict(self, mock_settings):
        """Test that auth endpoints have stricter limits."""
        mock_settings.rate_limit_per_minute = 100
        
        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.method = "POST"
        
        max_requests, window = get_rate_limit_config(mock_request)
        
        # Should be base_limit // 4 = 25, but max(5, 25) = 25
        assert max_requests == 25
        assert window == 60

    @patch('api.middleware.rate_limit.settings')
    def test_config_write_endpoint_moderate(self, mock_settings):
        """Test that write endpoints have moderate limits."""
        mock_settings.rate_limit_per_minute = 100
        
        mock_request = MagicMock()
        mock_request.url.path = "/api/items"
        mock_request.method = "POST"
        
        max_requests, window = get_rate_limit_config(mock_request)
        
        # Should be base_limit // 2 = 50, but max(10, 50) = 50
        assert max_requests == 50
        assert window == 60

    @patch('api.middleware.rate_limit.settings')
    def test_config_read_endpoint_higher(self, mock_settings):
        """Test that read endpoints have higher limits."""
        mock_settings.rate_limit_per_minute = 100
        
        mock_request = MagicMock()
        mock_request.url.path = "/api/items"
        mock_request.method = "GET"
        
        max_requests, window = get_rate_limit_config(mock_request)
        
        assert max_requests == 100
        assert window == 60


class TestRateLimitKeyWithCategory:
    """Test suite for rate_limit_key_with_category function."""

    @patch('api.middleware.rate_limit.settings')
    def test_key_includes_category(self, mock_settings):
        """Test that key includes endpoint category."""
        mock_settings.rate_limit_per_minute = 100
        
        mock_request = MagicMock()
        mock_request.state.user_id = "user_123"
        mock_request.url.path = "/api/items"
        mock_request.method = "GET"
        
        result = rate_limit_key_with_category(mock_request)
        
        assert result == "user_123:read"

    @patch('api.middleware.rate_limit.settings')
    def test_key_with_auth_category(self, mock_settings):
        """Test key with auth category."""
        mock_settings.rate_limit_per_minute = 100
        
        mock_request = MagicMock()
        mock_request.state.user_id = "user_123"
        mock_request.url.path = "/api/auth/login"
        mock_request.method = "POST"
        
        result = rate_limit_key_with_category(mock_request)
        
        assert result == "user_123:auth"


class TestCheckRateLimit:
    """Test suite for check_rate_limit function."""

    @patch('api.middleware.rate_limit.settings')
    def test_check_rate_limit_allows_request(self, mock_settings):
        """Test that check_rate_limit allows requests within limit."""
        mock_settings.rate_limit_per_minute = 60
        
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user"
        mock_request.url.path = "/api/items"
        mock_request.method = "GET"
        
        is_allowed, remaining, reset_time = check_rate_limit(mock_request)
        
        assert is_allowed is True
        assert remaining >= 0
        assert reset_time > 0

    @patch('api.middleware.rate_limit.settings')
    def test_check_rate_limit_blocks_excess(self, mock_settings):
        """Test that check_rate_limit blocks excess requests."""
        mock_settings.rate_limit_per_minute = 60
        
        mock_request = MagicMock()
        mock_request.state.user_id = "test_user_block"
        mock_request.url.path = "/api/items"
        mock_request.method = "GET"
        
        # Fill up the limit for this specific key+category combo
        for _ in range(60):
            check_rate_limit(mock_request)
        
        # Next request should be blocked
        is_allowed, remaining, reset_time = check_rate_limit(mock_request)
        
        assert is_allowed is False
        assert remaining == 0
