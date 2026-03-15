"""Tests for model imports after utils migration.

These tests verify that all model files that depend on utc_now
can properly import it from the utils module.

Test Location: tests/test_models_imports.py
Project: models/*.py
Framework: pytest
"""

import pytest
import sys
from pathlib import Path

# Setup path to import from backend
backend_path = Path(__file__).parent.parent / "backend"
if backend_path.exists():
    sys.path.insert(0, str(backend_path.parent))


class TestModelsImportUtcNow:
    """Test suite for model imports of utc_now from utils."""

    def test_agent_log_imports_utc_now(self):
        """Test that agent_log model can import utc_now from utils."""
        from models.agent_log import AgentLogEntry
        # Verify the model can be instantiated
        entry = AgentLogEntry(
            event_type="agent_log",
            agent="Agent_Primer",
            message="test message"
        )
        assert entry.timestamp is not None
        assert entry.timestamp.tzinfo is not None

    def test_builds_imports_utc_now(self):
        """Test that builds model can import utc_now from utils."""
        from models.builds import Build
        # Verify the model can be instantiated with default timestamp
        build = Build(
            id="test-id",
            status="running",
            program_id="prog-123"
        )
        assert build.created_at is not None
        assert build.created_at.tzinfo is not None

    def test_program_imports_utc_now(self):
        """Test that program model can import utc_now from utils."""
        from models.program import ValidationCampaign
        # Verify the model can be instantiated
        campaign = ValidationCampaign(
            id="campaign-123",
            name="test campaign"
        )
        assert campaign.created_at is not None
        assert campaign.created_at.tzinfo is not None

    def test_runtime_imports_utc_now(self):
        """Test that runtime model can import utc_now from utils."""
        from models.runtime import RuntimeSession
        # Verify the model can be instantiated with default timestamp
        session = RuntimeSession(
            id="session-123",
            program_id="prog-123"
        )
        assert session.started_at is not None
        assert session.started_at.tzinfo is not None
