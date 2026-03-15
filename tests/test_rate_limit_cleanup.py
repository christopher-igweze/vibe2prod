"""Tests for rate limit storage cleanup functionality.

These tests verify that the RateLimitStorage class properly clears expired
entries to prevent unbounded memory growth in long-running processes.

Test Location: tests/test_rate_limit_cleanup.py
Project: backend/api/middleware/rate_limit.py
Framework: pytest
"""

import pytest
from unittest.mock import patch, MagicMock
import random
import sys
import threading
from pathlib import Path

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from backend.api.middleware.rate_limit import RateLimitStorage, SlidingWindowCounter
except ImportError:
    try:
        from api.middleware.rate_limit import RateLimitStorage, SlidingWindowCounter
    except ImportError:
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.middleware.rate_limit import RateLimitStorage, SlidingWindowCounter
        else:
            raise ImportError("Could not import RateLimitStorage from any known path")


class TestRateLimitStorageCleanup:
    """Test suite for RateLimitStorage cleanup functionality."""

    def test_clear_expired_method_exists(self):
        """Test that RateLimitStorage has a clear_expired method."""
        storage = RateLimitStorage()
        assert hasattr(storage, 'clear_expired'), "RateLimitStorage should have clear_expired method"
        assert callable(getattr(storage, 'clear_expired')), "clear_expired should be callable"

    def test_check_rate_limit_calls_clear_expired_probabilistically(self):
        """Test that check_rate_limit calls clear_expired with ~10% probability."""
        storage = RateLimitStorage()
        
        # Mock random.random to always return 0.05 (less than 0.1) so cleanup is triggered
        with patch.object(random, 'random', return_value=0.05):
            with patch.object(storage, 'clear_expired') as mock_clear:
                # Call check_rate_limit
                storage.check_rate_limit("test_key", window_seconds=60, max_requests=10)
                
                # clear_expired should be called when random < 0.1
                mock_clear.assert_called_once()

    def test_check_rate_limit_does_not_call_clear_expired_above_threshold(self):
        """Test that check_rate_limit does NOT call clear_expired when random >= 0.1."""
        storage = RateLimitStorage()
        
        # Mock random.random to always return 0.5 (greater than 0.1) so cleanup is NOT triggered
        with patch.object(random, 'random', return_value=0.5):
            with patch.object(storage, 'clear_expired') as mock_clear:
                # Call check_rate_limit
                storage.check_rate_limit("test_key", window_seconds=60, max_requests=10)
                
                # clear_expired should NOT be called when random >= 0.1
                mock_clear.assert_not_called()

    def test_check_rate_limit_does_not_call_clear_expired_at_threshold(self):
        """Test that check_rate_limit does NOT call clear_expired when random == 0.1."""
        storage = RateLimitStorage()
        
        # Mock random.random to return exactly 0.1 (equal to threshold)
        with patch.object(random, 'random', return_value=0.1):
            with patch.object(storage, 'clear_expired') as mock_clear:
                # Call check_rate_limit
                storage.check_rate_limit("test_key", window_seconds=60, max_requests=10)
                
                # clear_expired should NOT be called when random == 0.1 (not less than)
                mock_clear.assert_not_called()

    def test_check_rate_limit_returns_correct_result_with_cleanup(self):
        """Test that check_rate_limit still returns correct result when cleanup runs."""
        storage = RateLimitStorage()
        
        # Mock random.random to trigger cleanup
        with patch.object(random, 'random', return_value=0.05):
            with patch.object(storage, 'clear_expired'):
                is_allowed, remaining, reset_time = storage.check_rate_limit(
                    "test_key", window_seconds=60, max_requests=10
                )
                
                # Should allow the request
                assert is_allowed is True
                # Should have 9 remaining (10 - 1)
                assert remaining == 9
                # reset_time should be a future timestamp
                assert reset_time > 0

    def test_check_rate_limit_returns_correct_result_without_cleanup(self):
        """Test that check_rate_limit returns correct result when cleanup doesn't run."""
        storage = RateLimitStorage()
        
        # Mock random.random to NOT trigger cleanup
        with patch.object(random, 'random', return_value=0.5):
            with patch.object(storage, 'clear_expired') as mock_clear:
                is_allowed, remaining, reset_time = storage.check_rate_limit(
                    "test_key", window_seconds=60, max_requests=10
                )
                
                # Should allow the request
                assert is_allowed is True
                # Should have 9 remaining (10 - 1)
                assert remaining == 9
                # reset_time should be a future timestamp
                assert reset_time > 0
                # Verify cleanup was not called
                mock_clear.assert_not_called()

    def test_random_import_exists(self):
        """Test that the random module is imported in the rate_limit module."""
        import backend.api.middleware.rate_limit as rate_limit_module
        
        # Check that random is in the module's globals
        assert 'random' in dir(rate_limit_module) or hasattr(rate_limit_module, 'random'), \
            "The random module should be imported in rate_limit.py"
