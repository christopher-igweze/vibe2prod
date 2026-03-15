"""Tests for models/_utils module import verification.

These tests verify that the utc_now utility function can be properly
imported from models._utils and used by model files.

Test Location: backend/tests/test_models_utils_import.py
Project: backend/models/_utils.py
Framework: pytest
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

# Import utc_now from the models._utils module
# Handle different import paths based on project structure
try:
    from models._utils import utc_now
except ImportError:
    import sys
    from pathlib import Path
    # Add backend to path if needed
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from models._utils import utc_now


class TestUtcNowFunction:
    """Test suite for utc_now utility function in models._utils."""

    def test_utc_now_returns_datetime_type(self):
        """Test that utc_now returns a datetime object."""
        result = utc_now()
        assert isinstance(result, datetime)

    def test_utc_now_returns_utc_timezone(self):
        """Test that utc_now returns time in UTC timezone."""
        result = utc_now()
        assert result.tzinfo is not None
        # UTC timezone should have zero offset
        assert result.utcoffset().total_seconds() == 0

    def test_utc_now_is_recent(self):
        """Test that utc_now returns a recent timestamp (within last minute)."""
        result = utc_now()
        now = datetime.now(timezone.utc)
        # Should be within 60 seconds of now
        diff = abs((now - result).total_seconds())
        assert diff < 60

    def test_utc_now_is_callable(self):
        """Test that utc_now is callable."""
        assert callable(utc_now)


class TestModelsImportFromUtils:
    """Test that model files can properly import utc_now from models._utils."""

    def test_agent_log_imports_utc_now(self):
        """Test that agent_log.py can import utc_now from models._utils."""
        from models._utils import utc_now
        assert callable(utc_now)

    def test_builds_imports_utc_now(self):
        """Test that builds.py can import utc_now from models._utils."""
        from models._utils import utc_now
        assert callable(utc_now)

    def test_runtime_imports_utc_now(self):
        """Test that runtime.py can import utc_now from models._utils."""
        from models._utils import utc_now
        assert callable(utc_now)


class TestModelImportsCorrectSource:
    """Test that model files import from the correct source (models._utils)."""

    def test_agent_log_import_path(self):
        """Test that agent_log.py imports utc_now from models._utils."""
        import inspect
        from models import agent_log
        source = inspect.getsourcefile(agent_log)
        assert source is not None
        # Read the source file to verify import
        with open(source, 'r') as f:
            content = f.read()
        assert 'from models._utils import utc_now' in content
        assert 'from utils import utc_now' not in content

    def test_builds_import_path(self):
        """Test that builds.py imports utc_now from models._utils."""
        import inspect
        from models import builds
        source = inspect.getsourcefile(builds)
        assert source is not None
        with open(source, 'r') as f:
            content = f.read()
        assert 'from models._utils import utc_now' in content
        assert 'from utils import utc_now' not in content

    def test_runtime_import_path(self):
        """Test that runtime.py imports utc_now from models._utils."""
        import inspect
        from models import runtime
        source = inspect.getsourcefile(runtime)
        assert source is not None
        with open(source, 'r') as f:
            content = f.read()
        assert 'from models._utils import utc_now' in content
        assert 'from utils import utc_now' not in content
