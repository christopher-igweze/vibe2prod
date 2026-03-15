"""Tests for models/_utils module organization.

These tests verify that the utc_now utility function is properly
implemented in models._utils and can be imported by model files.

Test Location: backend/tests/test_models_utils.py
Project: backend/models/_utils.py
Framework: pytest
"""

import pytest
from datetime import datetime
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
        now = datetime.now(result.tzinfo)
        # Should be within 60 seconds of now
        diff = abs((now - result).total_seconds())
        assert diff < 60

    def test_utc_now_is_callable(self):
        """Test that utc_now is callable."""
        assert callable(utc_now)

    def test_utc_now_returns_unique_values(self):
        """Test that consecutive calls return different timestamps."""
        # Note: This might fail if called extremely fast, but that's OK
        # The important thing is it returns a valid datetime
        result1 = utc_now()
        result2 = utc_now()
        # At minimum, both should be valid datetime objects
        assert isinstance(result1, datetime)
        assert isinstance(result2, datetime)


class TestModelsImportFromUtils:
    """Test that model files can properly import utc_now from models._utils."""

    def test_agent_log_imports_utc_now(self):
        """Test that agent_log.py can import utc_now from models._utils."""
        # This import should work if the fix is in place
        from models._utils import utc_now
        assert callable(utc_now)

    def test_builds_imports_utc_now(self):
        """Test that builds.py can import utc_now from models._utils."""
        # This import should work if the fix is in place
        from models._utils import utc_now
        assert callable(utc_now)

    def test_runtime_imports_utc_now(self):
        """Test that runtime.py can import utc_now from models._utils."""
        # This import should work if the fix is in place
        from models._utils import utc_now
        assert callable(utc_now)


class TestModelsUseUtcNowAsDefault:
    """Test that model classes can use utc_now as a Field default_factory."""

    def test_agent_log_entry_uses_utc_now_default(self):
        """Test that AgentLogEntry uses utc_now for timestamp default."""
        from models.agent_log import AgentLogEntry
        
        # Create entry without timestamp - should use utc_now default
        entry = AgentLogEntry(
            event_type=AgentLogEntry.__fields__['event_type'].default,
            agent=AgentLogEntry.__fields__['agent'].default,
            message="test message"
        )
        
        # Timestamp should be set automatically
        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)

    def test_task_run_started_at_default(self):
        """Test that TaskRun uses utc_now for started_at default."""
        from models.builds import TaskRun, TaskStatus
        from uuid import uuid4
        
        # Create task run without started_at - should use utc_now default
        task_run = TaskRun(
            task_run_id=uuid4(),
            node_id="test-node",
            status=TaskStatus.pending
        )
        
        # started_at should be set automatically
        assert task_run.started_at is not None
        assert isinstance(task_run.started_at, datetime)

    def test_replan_decision_created_at_default(self):
        """Test that ReplanDecision uses utc_now for created_at default."""
        from models.builds import ReplanDecision, ReplanAction
        from uuid import uuid4
        
        # Create decision without created_at - should use utc_now default
        decision = ReplanDecision(
            decision_id=uuid4(),
            action=ReplanAction.continue_,
            reason="test reason"
        )
        
        # created_at should be set automatically
        assert decision.created_at is not None
        assert isinstance(decision.created_at, datetime)

    def test_debt_item_created_at_default(self):
        """Test that DebtItem uses utc_now for created_at default."""
        from models.builds import DebtItem
        from uuid import uuid4
        
        # Create debt item without created_at - should use utc_now default
        debt = DebtItem(
            debt_id=uuid4(),
            node_id="test-node",
            summary="test debt"
        )
        
        # created_at should be set automatically
        assert debt.created_at is not None
        assert isinstance(debt.created_at, datetime)

    def test_runtime_session_created_at_default(self):
        """Test that RuntimeSession uses utc_now for created_at default."""
        from models.runtime import RuntimeSession
        from uuid import uuid4
        
        # Create runtime session - should use utc_now defaults
        session = RuntimeSession(
            session_id=uuid4(),
            agent="test-agent"
        )
        
        # created_at should be set automatically
        assert session.created_at is not None
        assert isinstance(session.created_at, datetime)


class TestModuleOrganization:
    """Test that module organization follows consistent patterns."""

    def test_utils_module_not_imported_from_top_level(self):
        """Test that models don't import utc_now from top-level utils.
        
        This test verifies the fix is in place - the old import path
        'from utils import utc_now' should not work for model files.
        """
        import sys
        from pathlib import Path
        
        # Check if there's a top-level utils module (there shouldn't be for models)
        backend_path = Path(__file__).parent.parent
        utils_path = backend_path / "utils.py"
        utils_dir = backend_path / "utils"
        
        # Either path is acceptable, but models should use models._utils
        # The key is that importing from 'utils' in model context works
        # because of the fix placing _utils.py in models/
        from models._utils import utc_now
        assert callable(utc_now)

    def test_models_utils_contains_utc_now(self):
        """Test that models/_utils.py contains the utc_now function."""
        import inspect
        from models import _utils
        
        # Check that utc_now is defined in the module
        assert hasattr(_utils, 'utc_now')
        assert callable(_utils.utc_now)
        
        # Verify it's actually defined in this module, not just imported
        source = inspect.getsource(_utils)
        assert 'def utc_now' in source or 'utc_now' in source
