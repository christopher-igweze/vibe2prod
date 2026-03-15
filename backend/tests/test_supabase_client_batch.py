"""Tests for get_projects_batch function in supabase_client.

This tests the batch project fetching functionality that was added
to fix the N+1 query issue.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
import pytest


@pytest.fixture
def mock_supabase_client():
    """Create mock supabase client."""
    with patch('services.supabase_client._client') as mock:
        yield mock


class TestGetProjectsBatch:
    """Tests for the get_projects_batch function."""

    @pytest.mark.asyncio
    async def test_get_projects_batch_returns_dict(self, mock_supabase_client):
        """Verify get_projects_batch returns dict mapping UUID to project."""
        from services.supabase_client import get_projects_batch

        # Mock supabase response
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "repo_url": "https://github.com/user/repo1",
                "repo_name": "repo1",
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "repo_url": "https://github.com/user/repo2",
                "repo_name": "repo2",
            },
        ]
        mock_table.select.return_value = mock_select
        mock_select.in_.return_value = mock_execute
        mock_supabase_client.return_value.table.return_value = mock_table

        project_ids = [
            UUID("11111111-1111-1111-1111-111111111111"),
            UUID("22222222-2222-2222-2222-222222222222"),
        ]

        result = await get_projects_batch(project_ids)

        # Verify result is a dict
        assert isinstance(result, dict)
        assert len(result) == 2

        # Verify keys are UUIDs
        assert UUID("11111111-1111-1111-1111-111111111111") in result
        assert UUID("22222222-2222-2222-2222-222222222222") in result

        # Verify values are the project dicts
        assert result[UUID("11111111-1111-1111-1111-111111111111")]["repo_name"] == "repo1"
        assert result[UUID("22222222-2222-2222-2222-222222222222")]["repo_name"] == "repo2"

    @pytest.mark.asyncio
    async def test_get_projects_batch_empty_list(self, mock_supabase_client):
        """Verify get_projects_batch handles empty list."""
        from services.supabase_client import get_projects_batch

        result = await get_projects_batch([])

        assert result == {}
        # Should not call supabase client for empty list
        mock_supabase_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_projects_batch_single_id(self, mock_supabase_client):
        """Verify get_projects_batch works with single ID."""
        from services.supabase_client import get_projects_batch

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "repo_url": "https://github.com/user/repo1",
                "repo_name": "repo1",
            }
        ]
        mock_table.select.return_value = mock_select
        mock_select.in_.return_value = mock_execute
        mock_supabase_client.return_value.table.return_value = mock_table

        project_ids = [UUID("11111111-1111-1111-1111-111111111111")]

        result = await get_projects_batch(project_ids)

        assert len(result) == 1
        assert UUID("11111111-1111-1111-1111-111111111111") in result

    @pytest.mark.asyncio
    async def test_get_projects_batch_uses_in_clause(self, mock_supabase_client):
        """Verify get_projects_batch uses .in_() clause for efficient querying."""
        from services.supabase_client import get_projects_batch

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_execute = MagicMock()
        mock_execute.data = []
        mock_table.select.return_value = mock_select
        mock_select.in_.return_value = mock_execute
        mock_supabase_client.return_value.table.return_value = mock_table

        project_ids = [
            UUID("11111111-1111-1111-1111-111111111111"),
            UUID("22222222-2222-2222-2222-222222222222"),
            UUID("33333333-3333-3333-3333-333333333333"),
        ]

        await get_projects_batch(project_ids)

        # Verify .in_() was called with the string IDs
        mock_select.in_.assert_called_once()
        called_ids = mock_select.in_.call_args[0][1]
        assert len(called_ids) == 3
        assert "11111111-1111-1111-1111-111111111111" in called_ids
        assert "22222222-2222-2222-2222-222222222222" in called_ids
        assert "33333333-3333-3333-3333-333333333333" in called_ids

    @pytest.mark.asyncio
    async def test_get_projects_batch_project_not_found(self, mock_supabase_client):
        """Verify get_projects_batch handles projects that don't exist."""
        from services.supabase_client import get_projects_batch

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_execute = MagicMock()
        # Return fewer projects than requested (some not found)
        mock_execute.data = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "repo_url": "https://github.com/user/repo1",
                "repo_name": "repo1",
            }
        ]
        mock_table.select.return_value = mock_select
        mock_select.in_.return_value = mock_execute
        mock_supabase_client.return_value.table.return_value = mock_table

        project_ids = [
            UUID("11111111-1111-1111-1111-111111111111"),
            UUID("22222222-2222-2222-2222-222222222222"),  # Not in DB
        ]

        result = await get_projects_batch(project_ids)

        # Only the found project should be in result
        assert len(result) == 1
        assert UUID("11111111-1111-1111-1111-111111111111") in result
        assert UUID("22222222-2222-2222-2222-222222222222") not in result
