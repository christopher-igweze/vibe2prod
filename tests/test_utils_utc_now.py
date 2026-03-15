"""Tests for utc_now utility function migration from models/ to utils/.

These tests verify that the utc_now function is properly available
in the utils module and returns timezone-aware datetime objects.

Test Location: tests/test_utils_utc_now.py
Project: utils/__init__.py
Framework: pytest
"""

import pytest
from datetime import datetime, timezone

# Import utc_now from its new location in utils/
try:
    from utils import utc_now
except ImportError:
    try:
        from backend.utils import utc_now
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from utils import utc_now
        else:
            raise ImportError("Could not import utc_now from any known path")


class TestUtcNowFunction:
    """Test suite for utc_now utility function."""

    def test_utc_now_returns_datetime(self):
        """Test that utc_now returns a datetime object."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_utc_now_is_timezone_aware(self):
        """Test that utc_now returns a timezone-aware datetime."""
        result = utc_now()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_utc_now_returns_utc_timezone(self):
        """Test that utc_now returns datetime in UTC timezone."""
        result = utc_now()
        # Verify the timezone is UTC
        assert str(result.tzinfo) in ["UTC", "UTC+00:00"]

    def test_utc_now_is_recent(self):
        """Test that utc_now returns a recent timestamp."""
        result = utc_now()
        now = datetime.now(timezone.utc)
        # Allow 1 second tolerance for test execution time
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 1
