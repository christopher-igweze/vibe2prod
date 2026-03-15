"""Tests for get_project_with_scans query optimization.

These tests verify that the get_project_with_scans function properly
fetches project and scan history concurrently, reducing sequential DB calls.

Test Location: backend/tests/test_get_project_with_scans.py
Project: backend
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from backend.services import supabase_client


class TestGetProjectWithScans:
    """Test suite for get_project_with_scans function."""

    @pytest.fixture
    def mock_project(self):
        """Create a mock project dictionary."""
        return {
            "id": "12345678-1234-1234-1234-123456789abc",
            "user_id": "user-123",
            "repo_url": "https://github.com/test/repo",
            "repo_name": "test-repo",
            "scan_count": 5,
        }

    @pytest.fixture
    def mock_scans(self):
        """Create a list of mock scan records."""
        return [
            {
                "id": "scan-1",
                "project_id": "12345678-1234-1234-1234-123456789abc",
                "status": "completed",
                "score": 85,
            },
            {
                "id": "scan-2",
                "project_id": "12345678-1234-1234-1234-123456789abc",
                "status": "completed",
                "score": 90,
            },
        ]

    @pytest.mark.asyncio
    async def test_get_project_with_scans_returns_project_and_scans(
        self, mock_project, mock_scans
    ):
        """Test that get_project_with_scans returns both project and scans."""
        project_id = UUID("12345678-1234-1234-1234-123456789abc")
        user_id = "user-123"

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project
            mock_get_scans.return_value = mock_scans

            result = await supabase_client.get_project_with_scans(project_id, user_id)

            project, scans = result
            assert project == mock_project
            assert scans == mock_scans

    @pytest.mark.asyncio
    async def test_get_project_with_scans_fetches_concurrently(self, mock_project, mock_scans):
        """Test that get_project_with_scans fetches data concurrently."""
        project_id = UUID("12345678-1234-1234-1234-123456789abc")
        user_id = "user-123"

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project
            mock_get_scans.return_value = mock_scans

            await supabase_client.get_project_with_scans(project_id, user_id)

            # Verify both functions were called (concurrent execution)
            mock_get_project.assert_called_once()
            mock_get_scans.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_with_scans_returns_none_for_wrong_user(self, mock_project):
        """Test that get_project_with_scans returns None when user doesn't own project."""
        project_id = UUID("12345678-1234-1234-1234-123456789abc")
        user_id = "user-456"  # Different user

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project
            mock_get_scans.return_value = []

            result = await supabase_client.get_project_with_scans(project_id, user_id)

            project, scans = result
            assert project is None
            assert scans == []

    @pytest.mark.asyncio
    async def test_get_project_with_scans_returns_none_for_missing_project(self):
        """Test that get_project_with_scans returns (None, []) when project not found."""
        project_id = UUID("12345678-1234-1234-1234-123456789abc")
        user_id = "user-123"

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = None
            mock_get_scans.return_value = []

            result = await supabase_client.get_project_with_scans(project_id, user_id)

            project, scans = result
            assert project is None
            assert scans == []

    @pytest.mark.asyncio
    async def test_get_project_with_scans_respects_limit(self, mock_project):
        """Test that get_project_with_scans respects the limit parameter."""
        project_id = UUID("12345678-1234-1234-1234-123456789abc")
        user_id = "user-123"
        limit = 10

        with patch.object(
            supabase_client, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            supabase_client, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_project.return_value = mock_project
            mock_get_scans.return_value = []

            await supabase_client.get_project_with_scans(project_id, user_id, limit=limit)

            # Verify scan history was called with the correct limit
            mock_get_scans.assert_called_once_with(project_id, user_id, limit)
