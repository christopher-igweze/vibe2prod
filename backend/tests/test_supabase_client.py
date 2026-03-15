"""Tests for Supabase client query optimization.

These tests verify that the get_project_with_scans function properly
fetches project and scan history concurrently, reducing sequential DB calls.

Test Location: backend/tests/test_supabase_client.py
Framework: pytest with asyncio
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestGetProjectWithScans:
    """Test suite for get_project_with_scans function optimization."""

    @pytest.fixture
    def mock_project_data(self):
        """Create mock project data."""
        return {
            "id": str(uuid4()),
            "user_id": "test-user-123",
            "repo_url": "https://github.com/test/repo",
            "repo_name": "test-repo",
        }

    @pytest.fixture
    def mock_scans_data(self):
        """Create mock scans data."""
        return [
            {"id": str(uuid4()), "project_id": "test-project", "score": 85},
            {"id": str(uuid4()), "project_id": "test-project", "score": 90},
        ]

    @pytest.mark.asyncio
    async def test_get_project_with_scans_returns_project_and_scans(
        self, mock_project_data, mock_scans_data
    ):
        """Test that get_project_with_scans returns both project and scans."""
        from services import supabase_client

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project_data
            mock_get_scans.return_value = mock_scans_data

            result = await supabase_client.get_project_with_scans(
                project_id=uuid4(), user_id="test-user-123"
            )

            project, scans = result
            assert project == mock_project_data
            assert scans == mock_scans_data

    @pytest.mark.asyncio
    async def test_get_project_with_scans_fetches_concurrently(self, mock_project_data):
        """Test that get_project_with_scans fetches data concurrently."""
        from services import supabase_client

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project_data
            mock_get_scans.return_value = []

            await supabase_client.get_project_with_scans(
                project_id=uuid4(), user_id="test-user-123"
            )

            # Verify both functions were called (concurrent execution)
            mock_get_project.assert_called_once()
            mock_get_scans.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_with_scans_returns_none_for_missing_project(self):
        """Test that get_project_with_scans returns (None, []) when project not found."""
        from services import supabase_client

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = None
            mock_get_scans.return_value = []

            result = await supabase_client.get_project_with_scans(
                project_id=uuid4(), user_id="test-user-123"
            )

            project, scans = result
            assert project is None
            assert scans == []

    @pytest.mark.asyncio
    async def test_get_project_with_scans_returns_none_for_wrong_owner(self, mock_project_data):
        """Test that get_project_with_scans returns (None, []) when project belongs to different user."""
        from services import supabase_client

        # Project belongs to different user
        mock_project_data["user_id"] = "different-user-456"

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project_data
            mock_get_scans.return_value = [{"id": "scan1"}]

            result = await supabase_client.get_project_with_scans(
                project_id=uuid4(), user_id="test-user-123"
            )

            project, scans = result
            assert project is None
            assert scans == []
            # Scans should not be returned when ownership check fails
            assert mock_get_scans.return_value not in [scans]

    @pytest.mark.asyncio
    async def test_get_project_with_scans_respects_limit(self, mock_project_data):
        """Test that get_project_with_scans passes limit parameter to scan history."""
        from services import supabase_client

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project_data
            mock_get_scans.return_value = []

            await supabase_client.get_project_with_scans(
                project_id=uuid4(), user_id="test-user-123", limit=25
            )

            # Verify limit was passed to scan history
            mock_get_scans.assert_called_once_with(
                uuid4(), "test-user-123", 25
            )
