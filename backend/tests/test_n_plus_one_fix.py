"""Tests for N+1 query fix in list_scans endpoint.

This test verifies that list_scans uses batch fetching for projects
instead of making individual DB calls for each scan.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
import pytest


@pytest.fixture
def mock_db():
    """Create mock database client."""
    with patch('api.routes.user.db') as mock:
        yield mock


@pytest.fixture
def sample_scans():
    """Sample scan data returned from list_user_scans."""
    return [
        {
            "id": "scan-1",
            "project_id": "11111111-1111-1111-1111-111111111111",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "scan-2",
            "project_id": "22222222-2222-2222-2222-222222222222",
            "status": "completed",
            "created_at": "2024-01-02T00:00:00Z",
        },
        {
            "id": "scan-3",
            "project_id": "33333333-3333-3333-3333-333333333333",
            "status": "completed",
            "created_at": "2024-01-03T00:00:00Z",
        },
    ]


@pytest.fixture
def sample_projects():
    """Sample projects data returned from get_projects_batch."""
    return {
        UUID("11111111-1111-1111-1111-111111111111"): {
            "id": "11111111-1111-1111-1111-111111111111",
            "repo_url": "https://github.com/user/repo1",
            "repo_name": "repo1",
        },
        UUID("22222222-2222-2222-2222-222222222222"): {
            "id": "22222222-2222-2222-2222-222222222222",
            "repo_url": "https://github.com/user/repo2",
            "repo_name": "repo2",
        },
        UUID("33333333-3333-3333-3333-333333333333"): {
            "id": "33333333-3333-3333-3333-333333333333",
            "repo_url": "https://github.com/user/repo3",
            "repo_name": "repo3",
        },
    }


class TestListScansN1Fix:
    """Tests verifying that list_scans uses batch project fetching."""

    @pytest.mark.asyncio
    async def test_list_scans_uses_batch_fetch(self, mock_db, sample_scans, sample_projects):
        """Verify that get_projects_batch is called once, not get_project in a loop."""
        # Setup mocks
        mock_db.list_user_scans = AsyncMock(return_value=sample_scans)
        mock_db.get_projects_batch = AsyncMock(return_value=sample_projects)
        mock_db.get_project = AsyncMock()  # Should NOT be called

        # Import and call the endpoint logic
        from api.routes.user import list_scans

        # Create a mock request with user_id
        mock_request = MagicMock()
        mock_request.state.user_id = "user-123"

        result = await list_scans(mock_request)

        # Verify batch fetch was called
        mock_db.get_projects_batch.assert_called_once()

        # Verify get_project was NOT called (no N+1)
        mock_db.get_project.assert_not_called()

        # Verify results are enriched with repo info
        assert result[0]["repo_url"] == "https://github.com/user/repo1"
        assert result[0]["repo_name"] == "repo1"
        assert result[1]["repo_url"] == "https://github.com/user/repo2"
        assert result[1]["repo_name"] == "repo2"
        assert result[2]["repo_url"] == "https://github.com/user/repo3"
        assert result[2]["repo_name"] == "repo3"

    @pytest.mark.asyncio
    async def test_list_scans_empty_project_ids(self, mock_db):
        """Verify handling when scans have no project_id."""
        scans_without_project = [
            {"id": "scan-1", "project_id": None, "status": "completed"},
            {"id": "scan-2", "status": "completed"},
        ]

        mock_db.list_user_scans = AsyncMock(return_value=scans_without_project)
        mock_db.get_projects_batch = AsyncMock(return_value={})

        from api.routes.user import list_scans

        mock_request = MagicMock()
        mock_request.state.user_id = "user-123"

        result = await list_scans(mock_request)

        # get_projects_batch should be called with empty list
        mock_db.get_projects_batch.assert_called_once_with([])

        # Results should have empty repo_url and repo_name
        assert result[0]["repo_url"] == ""
        assert result[0]["repo_name"] == ""
        assert result[1]["repo_url"] == ""
        assert result[1]["repo_name"] == ""

    @pytest.mark.asyncio
    async def test_list_scans_no_scans(self, mock_db):
        """Verify handling when user has no scans."""
        mock_db.list_user_scans = AsyncMock(return_value=[])
        mock_db.get_projects_batch = AsyncMock(return_value={})

        from api.routes.user import list_scans

        mock_request = MagicMock()
        mock_request.state.user_id = "user-123"

        result = await list_scans(mock_request)

        # get_projects_batch should not be called when no scans
        mock_db.get_projects_batch.assert_not_called()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_scans_partial_project_lookup(self, mock_db, sample_scans):
        """Verify handling when some project_ids are not found in DB."""
        # Only return 2 projects for 3 scans
        partial_projects = {
            UUID("11111111-1111-1111-1111-111111111111"): {
                "id": "11111111-1111-1111-1111-111111111111",
                "repo_url": "https://github.com/user/repo1",
                "repo_name": "repo1",
            },
            UUID("22222222-2222-2222-2222-222222222222"): {
                "id": "22222222-2222-2222-2222-222222222222",
                "repo_url": "https://github.com/user/repo2",
                "repo_name": "repo2",
            },
        }

        mock_db.list_user_scans = AsyncMock(return_value=sample_scans)
        mock_db.get_projects_batch = AsyncMock(return_value=partial_projects)

        from api.routes.user import list_scans

        mock_request = MagicMock()
        mock_request.state.user_id = "user-123"

        result = await list_scans(mock_request)

        # Third scan should have empty repo info (project not found)
        assert result[0]["repo_url"] == "https://github.com/user/repo1"
        assert result[1]["repo_url"] == "https://github.com/user/repo2"
        assert result[2]["repo_url"] == ""  # Not found in batch result
        assert result[2]["repo_name"] == ""

    @pytest.mark.asyncio
    async def test_list_scans_single_scan(self, mock_db):
        """Verify batch fetch works with single scan."""
        single_scan = [
            {
                "id": "scan-1",
                "project_id": "11111111-1111-1111-1111-111111111111",
                "status": "completed",
            }
        ]

        projects = {
            UUID("11111111-1111-1111-1111-111111111111"): {
                "id": "11111111-1111-1111-1111-111111111111",
                "repo_url": "https://github.com/user/repo1",
                "repo_name": "repo1",
            }
        }

        mock_db.list_user_scans = AsyncMock(return_value=single_scan)
        mock_db.get_projects_batch = AsyncMock(return_value=projects)

        from api.routes.user import list_scans

        mock_request = MagicMock()
        mock_request.state.user_id = "user-123"

        result = await list_scans(mock_request)

        # Verify batch fetch was called with single ID
        mock_db.get_projects_batch.assert_called_once()
        called_ids = mock_db.get_projects_batch.call_args[0][0]
        assert len(called_ids) == 1
        assert called_ids[0] == UUID("11111111-1111-1111-1111-111111111111")

        assert result[0]["repo_url"] == "https://github.com/user/repo1"
