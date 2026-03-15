"""Tests for error handling in user routes.

These tests verify that route handlers properly catch database exceptions,
log them with appropriate context using module-level logger, and return
meaningful error responses rather than generic 500 errors.

Test Location: tests/test_user_routes_error_handling.py
Project: backend/api/routes/user.py
Framework: pytest
"""

import pytest
import logging
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import UUID
from fastapi import HTTPException

try:
    from backend.api.routes.user import router, logger
except ImportError:
    try:
        from api.routes.user import router, logger
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.routes.user import router, logger
        else:
            raise ImportError("Could not import user routes from any known path")


class TestUserRoutesErrorHandling:
    """Test suite for error handling in user route handlers."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with authenticated user."""
        request = MagicMock()
        request.state.user_id = "test-user-123"
        return request

    def test_module_level_logger_exists(self):
        """Test that module-level logger is defined in user routes."""
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == "api.routes.user" or logger.name.endswith("user")

    def test_get_me_exception_logs_with_user_context(self, mock_request):
        """Test that get_me route logs exceptions with user context."""
        with patch('api.routes.user.db') as mock_db:
            mock_db.get_user_profile.side_effect = Exception("Database connection failed")
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import get_me
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(get_me(mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to retrieve user profile"
                # Verify logger.exception was called
                mock_log.assert_called_once()
                # Check that user_id is in the log call
                call_args = mock_log.call_args
                assert "test-user-123" in str(call_args)

    def test_list_scans_exception_logs_with_user_context(self, mock_request):
        """Test that list_scans route logs exceptions with user context."""
        with patch('api.routes.user.db') as mock_db:
            mock_db.list_user_scans = AsyncMock(side_effect=Exception("Database query failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import list_scans
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(list_scans(mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to retrieve scans"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "test-user-123" in str(call_args)

    def test_list_scans_batch_project_fetch_error_logs_context(self, mock_request):
        """Test that batch project fetch errors are logged with context but don't fail."""
        with patch('api.routes.user.db') as mock_db:
            scan1 = {
                "id": "scan-1",
                "project_id": str(UUID(int=1)),
                "status": "completed"
            }
            mock_db.list_user_scans = AsyncMock(return_value=[scan1])
            mock_db.get_projects_batch = AsyncMock(side_effect=Exception("Batch fetch failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import list_scans
                import asyncio
                result = asyncio.run(list_scans(mock_request))
                
                # Should return scans without project enrichment
                assert result == [scan1]
                # Should log the error
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "test-user-123" in str(call_args)
                assert "batch-fetch" in str(call_args).lower() or "batch" in str(call_args).lower()

    def test_get_scan_detail_exception_logs_with_scan_id(self, mock_request):
        """Test that get_scan_detail route logs exceptions with scan ID."""
        scan_id = UUID(int=123)
        with patch('api.routes.user.db') as mock_db:
            mock_db.get_scan_report = AsyncMock(side_effect=Exception("Database error"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import get_scan_detail
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(get_scan_detail(scan_id, mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to retrieve scan"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert str(scan_id) in str(call_args)

    def test_get_scan_detail_project_fetch_error_logs_context(self, mock_request):
        """Test that project fetch errors in get_scan_detail are logged with context."""
        scan_id = UUID(int=123)
        project_id = UUID(int=456)
        scan_data = {
            "id": str(scan_id),
            "project_id": str(project_id),
            "status": "completed"
        }
        with patch('api.routes.user.db') as mock_db:
            mock_db.get_scan_report = AsyncMock(return_value=scan_data)
            mock_db.get_project = AsyncMock(side_effect=Exception("Project fetch failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import get_scan_detail
                import asyncio
                result = asyncio.run(get_scan_detail(scan_id, mock_request))
                
                # Should return scan without project enrichment
                assert result["id"] == str(scan_id)
                # Should log the error
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert str(scan_id) in str(call_args)

    def test_delete_scan_exception_logs_with_context(self, mock_request):
        """Test that delete_scan route logs exceptions with user and scan context."""
        scan_id = UUID(int=789)
        with patch('api.routes.user.db') as mock_db:
            mock_db.delete_scan_report = AsyncMock(side_effect=Exception("Delete failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import delete_scan
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(delete_scan(scan_id, mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to delete scan"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert str(scan_id) in str(call_args)
                assert "test-user-123" in str(call_args)

    def test_complete_tour_exception_logs_with_user_context(self, mock_request):
        """Test that complete_tour route logs exceptions with user context."""
        with patch('api.routes.user.db') as mock_db:
            mock_db.mark_tour_completed = AsyncMock(side_effect=Exception("Update failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import complete_tour
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(complete_tour(mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to complete tour"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "test-user-123" in str(call_args)

    def test_reset_tour_exception_logs_with_user_context(self, mock_request):
        """Test that reset_tour route logs exceptions with user context."""
        with patch('api.routes.user.db') as mock_db:
            mock_db.reset_tour = AsyncMock(side_effect=Exception("Reset failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import reset_tour
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(reset_tour(mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to reset tour"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "test-user-123" in str(call_args)

    def test_list_projects_exception_logs_with_user_context(self, mock_request):
        """Test that list_projects route logs exceptions with user context."""
        with patch('api.routes.user.db') as mock_db:
            mock_db.list_user_projects = AsyncMock(side_effect=Exception("Query failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import list_projects
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(list_projects(mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to retrieve projects"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert "test-user-123" in str(call_args)

    def test_get_project_scans_exception_logs_with_project_context(self, mock_request):
        """Test that get_project_scans route logs exceptions with project context."""
        project_id = UUID(int=999)
        with patch('api.routes.user.db') as mock_db:
            mock_db.get_project = AsyncMock(return_value={"id": str(project_id)})
            mock_db.get_scans_for_project = AsyncMock(side_effect=Exception("Query failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import get_project_scans
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(get_project_scans(project_id, mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to retrieve project scans"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert str(project_id) in str(call_args)

    def test_get_project_intake_exception_logs_with_project_context(self, mock_request):
        """Test that get_project_intake route logs exceptions with project context."""
        project_id = UUID(int=555)
        with patch('api.routes.user.db') as mock_db:
            mock_db.get_project = AsyncMock(return_value={"id": str(project_id)})
            mock_db.get_intake = AsyncMock(side_effect=Exception("Intake fetch failed"))
            with patch.object(logger, 'exception') as mock_log:
                from api.routes.user import get_project_intake
                with pytest.raises(HTTPException) as exc_info:
                    import asyncio
                    asyncio.run(get_project_intake(project_id, mock_request))
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.detail == "Failed to retrieve project intake"
                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert str(project_id) in str(call_args)

    def test_logger_exception_captures_full_traceback(self):
        """Test that logger.exception() is used instead of logger.error() to capture traceback."""
        # This verifies the fix: exception() includes full traceback, error() does not
        import inspect
        try:
            from backend.api.routes import user
            module_source = inspect.getsource(user)
        except ImportError:
            from api.routes import user
            module_source = inspect.getsource(user)
        
        # Count logger.exception calls (should have many)
        exception_calls = module_source.count('logger.exception(')
        # Count logger.error calls (should be 0 after fix)
        error_calls = module_source.count('logger.error(')
        
        assert exception_calls > 0, "Module should use logger.exception() for error handling"
        assert error_calls == 0, "Module should not use logger.error() - use logger.exception() instead"
