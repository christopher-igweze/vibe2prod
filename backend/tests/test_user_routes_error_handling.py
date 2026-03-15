"""Tests for user route error handling improvements.

These tests verify that the list_projects, get_project_scans, and get_project_intake
endpoints properly handle database exceptions and return appropriate HTTP 500 responses.

Test Location: backend/tests/test_user_routes_error_handling.py
Project: backend
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import HTTPException

# Import using relative path based on project structure
try:
    from backend.api.routes import user
except ImportError:
    from api.routes import user


class TestListProjectsErrorHandling:
    """Test suite for list_projects error handling."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object with user_id."""
        request = MagicMock()
        request.state.user_id = "test-user-123"
        return request

    @pytest.mark.asyncio
    async def test_list_projects_returns_500_on_database_exception(self, mock_request):
        """Test that list_projects returns 500 when database raises an exception."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.list_user_projects = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await user.list_projects(mock_request)
            
            assert exc_info.value.status_code == 500
            assert "Failed to retrieve projects" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_list_projects_returns_projects_on_success(self, mock_request):
        """Test that list_projects returns projects when database succeeds."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.list_user_projects = AsyncMock(
                return_value=[
                    {"id": "proj-1", "name": "Project 1"},
                    {"id": "proj-2", "name": "Project 2"}
                ]
            )
            
            result = await user.list_projects(mock_request)
            
            assert len(result) == 2
            assert result[0]["id"] == "proj-1"


class TestGetProjectScansErrorHandling:
    """Test suite for get_project_scans error handling."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object with user_id."""
        request = MagicMock()
        request.state.user_id = "test-user-123"
        return request

    @pytest.fixture
    def project_id(self):
        """Create a test project UUID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_get_project_scans_returns_500_on_database_exception(self, mock_request, project_id):
        """Test that get_project_scans returns 500 when database raises an exception."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(
                return_value={"id": str(project_id), "user_id": "test-user-123"}
            )
            mock_db.get_project_scan_history = AsyncMock(
                side_effect=Exception("Database error")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_scans(project_id, mock_request)
            
            assert exc_info.value.status_code == 500
            assert "Failed to retrieve project scans" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_project_scans_returns_404_for_unauthorized_project(self, mock_request, project_id):
        """Test that get_project_scans returns 404 for unauthorized project."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(
                return_value={"id": str(project_id), "user_id": "different-user"}
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_scans(project_id, mock_request)
            
            assert exc_info.value.status_code == 404
            assert "Project not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_project_scans_returns_404_for_missing_project(self, mock_request, project_id):
        """Test that get_project_scans returns 404 when project doesn't exist."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_scans(project_id, mock_request)
            
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_scans_returns_data_on_success(self, mock_request, project_id):
        """Test that get_project_scans returns data when database succeeds."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(
                return_value={"id": str(project_id), "user_id": "test-user-123"}
            )
            mock_db.get_project_scan_history = AsyncMock(
                return_value=[{"id": "scan-1", "status": "completed"}]
            )
            
            result = await user.get_project_scans(project_id, mock_request)
            
            assert "project" in result
            assert "scans" in result
            assert len(result["scans"]) == 1


class TestGetProjectIntakeErrorHandling:
    """Test suite for get_project_intake error handling."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object with user_id."""
        request = MagicMock()
        request.state.user_id = "test-user-123"
        return request

    @pytest.fixture
    def project_id(self):
        """Create a test project UUID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_get_project_intake_returns_500_on_database_exception(self, mock_request, project_id):
        """Test that get_project_intake returns 500 when database raises an exception."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(
                return_value={"id": str(project_id), "user_id": "test-user-123"}
            )
            mock_db.get_latest_project_intake = AsyncMock(
                side_effect=Exception("Database error")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_intake(project_id, mock_request)
            
            assert exc_info.value.status_code == 500
            assert "Failed to retrieve project intake" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_project_intake_returns_404_for_unauthorized_project(self, mock_request, project_id):
        """Test that get_project_intake returns 404 for unauthorized project."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(
                return_value={"id": str(project_id), "user_id": "different-user"}
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_intake(project_id, mock_request)
            
            assert exc_info.value.status_code == 404
            assert "Project not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_project_intake_returns_404_for_missing_project(self, mock_request, project_id):
        """Test that get_project_intake returns 404 when project doesn't exist."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await user.get_project_intake(project_id, mock_request)
            
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_intake_returns_data_on_success(self, mock_request, project_id):
        """Test that get_project_intake returns data when database succeeds."""
        with patch("backend.api.routes.user.db") as mock_db:
            mock_db.get_project = AsyncMock(
                return_value={"id": str(project_id), "user_id": "test-user-123"}
            )
            mock_db.get_latest_project_intake = AsyncMock(
                return_value={"id": "intake-1", "project_id": str(project_id)}
            )
            
            result = await user.get_project_intake(project_id, mock_request)
            
            assert "project_intake" in result
            assert result["project_intake"]["id"] == "intake-1"
