"""Tests for user routes error handling improvements.

These tests verify that the user route endpoints properly handle database
errors by catching exceptions and returning appropriate HTTPException responses.

Test Location: tests/test_user_routes_error_handling.py
Project: backend/api/routes/user.py
Framework: pytest
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import UUID
from fastapi import HTTPException

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from api.routes import user
except ImportError:
    try:
        from routes import user
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.routes import user
        else:
            # Try adding parent directory directly
            parent_path = Path(__file__).parent.parent
            sys.path.insert(0, str(parent_path))
            from api.routes import user


class TestGetMeErrorHandling:
    """Test suite for get_me error handling in user routes."""

    def test_get_me_handles_database_error(self):
        """Test that get_me handles database exceptions and returns 500 error."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.get_user_profile.side_effect = Exception("Database connection failed")

            # The endpoint should catch the exception and raise HTTPException
            try:
                user.get_me(mock_request)
                pytest.fail("Expected HTTPException to be raised")
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "Failed to retrieve user profile" in exc.detail

    def test_get_me_success_case(self):
        """Test that get_me returns profile data on successful database query."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"
        expected_profile = {
            "user_id": "test-user-123",
            "role": "user",
            "onboarding_complete": True,
            "lifetime_scans_used": 5,
            "lifetime_scan_cap": 10,
            "scan_credits": 3,
            "balance_usd": 15.0
        }

        with patch('api.routes.user.db') as mock_db:
            mock_db.get_user_profile.return_value = expected_profile

            result = user.get_me(mock_request)

            assert result == expected_profile
            mock_db.get_user_profile.assert_called_once_with("test-user-123")


class TestListScansErrorHandling:
    """Test suite for list_scans error handling in user routes."""

    @pytest.mark.asyncio
    async def test_list_scans_handles_database_error(self):
        """Test that list_scans handles database exceptions and returns 500 error."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.list_user_scans.side_effect = Exception("Database query failed")

            try:
                await user.list_scans(mock_request)
                pytest.fail("Expected HTTPException to be raised")
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "Failed to retrieve scans" in exc.detail

    @pytest.mark.asyncio
    async def test_list_scans_handles_project_batch_error(self):
        """Test that list_scans handles project batch fetch error gracefully."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"
        
        mock_scans = [
            {"scan_id": "scan-1", "project_id": str(UUID("12345678-1234-1234-1234-123456789abc"))},
            {"scan_id": "scan-2", "project_id": str(UUID("87654321-4321-4321-4321-cba987654321"))}
        ]

        with patch('api.routes.user.db') as mock_db:
            mock_db.list_user_scans.return_value = mock_scans
            mock_db.get_projects_batch.side_effect = Exception("Project batch query failed")

            # Should NOT raise exception - error is caught and logged, but continues
            result = await user.list_scans(mock_request)
            
            # Returns scans without enrichment
            assert len(result) == 2
            mock_db.list_user_scans.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_scans_success_case(self):
        """Test that list_scans returns scans on successful database query."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"
        
        mock_scans = [
            {"scan_id": "scan-1", "project_id": str(UUID("12345678-1234-1234-1234-123456789abc"))}
        ]
        mock_projects = {
            UUID("12345678-1234-1234-1234-123456789abc"): {
                "repo_url": "https://github.com/owner/repo",
                "repo_name": "repo"
            }
        }

        with patch('api.routes.user.db') as mock_db:
            mock_db.list_user_scans.return_value = mock_scans
            mock_db.get_projects_batch.return_value = mock_projects

            result = await user.list_scans(mock_request)

            assert len(result) == 1
            mock_db.list_user_scans.assert_called_once_with("test-user-123")


class TestGetScanDetailErrorHandling:
    """Test suite for get_scan_detail error handling in user routes."""

    @pytest.mark.asyncio
    async def test_get_scan_detail_handles_database_error(self):
        """Test that get_scan_detail handles database exceptions and returns 500 error."""
        scan_id = UUID("12345678-1234-1234-1234-123456789abc")
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.get_scan_report.side_effect = Exception("Database query failed")

            try:
                await user.get_scan_detail(scan_id, mock_request)
                pytest.fail("Expected HTTPException to be raised")
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "Failed to retrieve scan" in exc.detail

    @pytest.mark.asyncio
    async def test_get_scan_detail_handles_project_fetch_error(self):
        """Test that get_scan_detail handles project fetch error gracefully."""
        scan_id = UUID("12345678-1234-1234-1234-123456789abc")
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"
        
        mock_scan = {
            "scan_id": str(scan_id),
            "project_id": str(UUID("87654321-4321-4321-4321-cba987654321"))
        }

        with patch('api.routes.user.db') as mock_db:
            mock_db.get_scan_report.return_value = mock_scan
            mock_db.get_project.side_effect = Exception("Project fetch failed")

            # Should NOT raise exception - error is caught and returns scan without enrichment
            result = await user.get_scan_detail(scan_id, mock_request)
            
            assert result["scan_id"] == str(scan_id)
            assert "repo_url" not in result or result.get("repo_url") == ""

    @pytest.mark.asyncio
    async def test_get_scan_detail_success_case(self):
        """Test that get_scan_detail returns scan data on successful query."""
        scan_id = UUID("12345678-1234-1234-1234-123456789abc")
        project_id = UUID("87654321-4321-4321-4321-cba987654321")
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"
        
        mock_scan = {
            "scan_id": str(scan_id),
            "project_id": str(project_id)
        }
        mock_project = {
            "repo_url": "https://github.com/owner/repo",
            "repo_name": "repo"
        }

        with patch('api.routes.user.db') as mock_db:
            mock_db.get_scan_report.return_value = mock_scan
            mock_db.get_project.return_value = mock_project

            result = await user.get_scan_detail(scan_id, mock_request)

            assert result["scan_id"] == str(scan_id)
            assert result["repo_url"] == "https://github.com/owner/repo"


class TestDeleteScanErrorHandling:
    """Test suite for delete_scan error handling in user routes."""

    @pytest.mark.asyncio
    async def test_delete_scan_handles_database_error(self):
        """Test that delete_scan handles database exceptions and returns 500 error."""
        scan_id = UUID("12345678-1234-1234-1234-123456789abc")
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.delete_scan_report.side_effect = Exception("Database delete failed")

            try:
                await user.delete_scan(scan_id, mock_request)
                pytest.fail("Expected HTTPException to be raised")
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "Failed to delete scan" in exc.detail

    @pytest.mark.asyncio
    async def test_delete_scan_success_case(self):
        """Test that delete_scan returns 204 on successful deletion."""
        scan_id = UUID("12345678-1234-1234-1234-123456789abc")
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.delete_scan_report.return_value = True

            result = await user.delete_scan(scan_id, mock_request)

            assert result.status_code == 204
            mock_db.delete_scan_report.assert_called_once_with(scan_id, "test-user-123")


class TestCompleteTourErrorHandling:
    """Test suite for complete_tour error handling in user routes."""

    @pytest.mark.asyncio
    async def test_complete_tour_handles_database_error(self):
        """Test that complete_tour handles database exceptions and returns 500 error."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.mark_tour_completed.side_effect = Exception("Database update failed")

            try:
                await user.complete_tour(mock_request)
                pytest.fail("Expected HTTPException to be raised")
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "Failed to complete tour" in exc.detail

    @pytest.mark.asyncio
    async def test_complete_tour_success_case(self):
        """Test that complete_tour returns ok=True on successful update."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.mark_tour_completed.return_value = None

            result = await user.complete_tour(mock_request)

            assert result == {"ok": True}
            mock_db.mark_tour_completed.assert_called_once_with("test-user-123")


class TestResetTourErrorHandling:
    """Test suite for reset_tour error handling in user routes."""

    @pytest.mark.asyncio
    async def test_reset_tour_handles_database_error(self):
        """Test that reset_tour handles database exceptions and returns 500 error."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.reset_tour.side_effect = Exception("Database update failed")

            try:
                await user.reset_tour(mock_request)
                pytest.fail("Expected HTTPException to be raised")
            except HTTPException as exc:
                assert exc.status_code == 500
                assert "Failed to reset tour" in exc.detail

    @pytest.mark.asyncio
    async def test_reset_tour_success_case(self):
        """Test that reset_tour returns ok=True on successful update."""
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-123"

        with patch('api.routes.user.db') as mock_db:
            mock_db.reset_tour.return_value = None

            result = await user.reset_tour(mock_request)

            assert result == {"ok": True}
            mock_db.reset_tour.assert_called_once_with("test-user-123")
