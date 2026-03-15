"""Tests for user routes scan history optimization.

These tests verify that the get_project_scans endpoint uses the optimized
get_project_with_scans function for concurrent data fetching.

Test Location: backend/tests/test_user_routes.py
Framework: pytest with asyncio
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import HTTPException


class TestGetProjectScansEndpoint:
    """Test suite for get_project_scans endpoint optimization."""

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
    async def test_get_project_scans_returns_optimized_data(
        self, mock_project_data, mock_scans_data
    ):
        """Test that get_project_scans returns project and scans using optimized method."""
        from api.routes import user

        # Create mock request with user_id
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch.object(
            user.db, "get_project_with_scans", new_callable=AsyncMock
        ) as mock_get_with_scans:
            mock_get_with_scans.return_value = (mock_project_data, mock_scans_data)

            response = await user.get_project_scans(
                project_id=uuid4(), request=mock_request
            )

            assert "project" in response
            assert "scans" in response
            assert response["project"] == mock_project_data
            assert response["scans"] == mock_scans_data

    @pytest.mark.asyncio
    async def test_get_project_scans_returns_404_for_missing_project(self):
        """Test that get_project_scans returns 404 when project not found."""
        from api.routes import user

        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch.object(
            user.db, "get_project_with_scans", new_callable=AsyncMock
        ) as mock_get_with_scans:
            mock_get_with_scans.return_value = (None, [])

            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_scans(
                    project_id=uuid4(), request=mock_request
                )

            assert exc_info.value.status_code == 404
            assert "Project not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_project_scans_uses_concurrent_fetch(self, mock_project_data):
        """Test that endpoint uses get_project_with_scans for concurrent fetch."""
        from api.routes import user

        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch.object(
            user.db, "get_project_with_scans", new_callable=AsyncMock
        ) as mock_get_with_scans:
            mock_get_with_scans.return_value = (mock_project_data, [])

            await user.get_project_scans(
                project_id=uuid4(), request=mock_request
            )

            # Verify the optimized method is called
            mock_get_with_scans.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_scans_no_longer_uses_sequential_calls(
        self, mock_project_data
    ):
        """Test that endpoint no longer uses separate get_project and get_project_scan_history."""
        from api.routes import user

        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch.object(
            user.db, "get_project_with_scans", new_callable=AsyncMock
        ) as mock_get_with_scans, patch.object(
            user.db, "get_project", new_callable=AsyncMock
        ) as mock_get_project, patch.object(
            user.db, "get_project_scan_history", new_callable=AsyncMock
        ) as mock_get_scans:
            mock_get_with_scans.return_value = (mock_project_data, [])
            mock_get_project.return_value = mock_project_data
            mock_get_scans.return_value = []

            await user.get_project_scans(
                project_id=uuid4(), request=mock_request
            )

            # Verify the old sequential methods are NOT called
            mock_get_project.assert_not_called()
            mock_get_scans.assert_not_called()
            # Only the optimized method should be called
            mock_get_with_scans.assert_called_once()
