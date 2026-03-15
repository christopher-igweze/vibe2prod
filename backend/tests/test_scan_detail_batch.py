"""Tests for scan detail batch operation fix.

These tests verify that get_scan_detail uses the batch method get_projects_batch
instead of individual get_project calls, consistent with list_scans pattern.

Test Location: backend/tests/test_scan_detail_batch.py
Project: backend/api/routes/user.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID
from fastapi import HTTPException

# Import the function to test - handle different project layouts
try:
    from api.routes.user import get_scan_detail
except ImportError:
    try:
        from backend.api.routes.user import get_scan_detail
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        if str(backend_path).endswith('backend'):
            sys.path.insert(0, str(backend_path.parent))
            from api.routes.user import get_scan_detail
        else:
            # Try adding backend directly
            backend_path = backend_path / 'backend'
            if backend_path.exists():
                sys.path.insert(0, str(backend_path.parent))
                from api.routes.user import get_scan_detail
            else:
                raise ImportError("Could not import get_scan_detail from any known path")


class TestScanDetailBatchOperation:
    """Test suite for get_scan_detail batch method usage."""

    @pytest.mark.asyncio
    async def test_get_scan_detail_uses_batch_method(self):
        """Test that get_scan_detail uses get_projects_batch instead of get_project."""
        scan_id = UUID("12345678-1234-5678-1234-567812345678")
        project_id = UUID("87654321-4321-8765-4321-876543218765")
        
        # Mock scan data
        mock_scan = {
            "id": str(scan_id),
            "project_id": str(project_id),
            "repo_url": "",
            "repo_name": ""
        }
        
        # Mock project data that would be returned by batch method
        # Note: get_projects_batch returns dict with UUID keys
        mock_project_data = {
            project_id: {
                "repo_url": "https://github.com/test/repo",
                "repo_name": "test-repo"
            }
        }
        
        # Create mock request with user_id
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-id"
        
        with patch('services.supabase_client.get_scan') as mock_get_scan, \
             patch('services.supabase_client.get_projects_batch') as mock_batch:
            
            mock_get_scan.return_value = mock_scan
            mock_batch.return_value = mock_project_data
            
            # Call the function
            result = await get_scan_detail(scan_id, mock_request)
            
            # Verify batch method was called (not individual get_project)
            mock_batch.assert_called_once()
            mock_batch.assert_called_with([project_id])
            
            # Verify the result contains project info
            assert result["repo_url"] == "https://github.com/test/repo"
            assert result["repo_name"] == "test-repo"

    @pytest.mark.asyncio
    async def test_get_scan_detail_project_not_found_returns_empty(self):
        """Test that get_scan_detail handles missing project gracefully."""
        scan_id = UUID("12345678-1234-5678-1234-567812345678")
        project_id = UUID("87654321-4321-8765-4321-876543218765")
        
        mock_scan = {
            "id": str(scan_id),
            "project_id": str(project_id),
            "repo_url": "",
            "repo_name": ""
        }
        
        # Empty cache (project not found)
        mock_project_cache = {}
        
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-id"
        
        with patch('services.supabase_client.get_scan') as mock_get_scan, \
             patch('services.supabase_client.get_projects_batch') as mock_batch:
            
            mock_get_scan.return_value = mock_scan
            mock_batch.return_value = mock_project_cache
            
            result = await get_scan_detail(scan_id, mock_request)
            
            # Should have empty strings when project not found
            assert result["repo_url"] == ""
            assert result["repo_name"] == ""

    @pytest.mark.asyncio
    async def test_get_scan_detail_batch_exception_handling(self):
        """Test that get_scan_detail handles batch method exceptions gracefully."""
        scan_id = UUID("12345678-1234-5678-1234-567812345678")
        project_id = UUID("87654321-4321-8765-4321-876543218765")
        
        mock_scan = {
            "id": str(scan_id),
            "project_id": str(project_id),
            "repo_url": "",
            "repo_name": ""
        }
        
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-id"
        
        with patch('services.supabase_client.get_scan') as mock_get_scan, \
             patch('services.supabase_client.get_projects_batch') as mock_batch:
            
            mock_get_scan.return_value = mock_scan
            # Simulate exception from batch method
            mock_batch.side_effect = Exception("Database connection error")
            
            # Should not raise, just return scan without project info
            result = await get_scan_detail(scan_id, mock_request)
            
            assert result["repo_url"] == ""
            assert result["repo_name"] == ""

    @pytest.mark.asyncio
    async def test_get_scan_detail_no_project_id(self):
        """Test that get_scan_detail works when scan has no project_id."""
        scan_id = UUID("12345678-1234-5678-1234-567812345678")
        
        # Scan without project_id
        mock_scan = {
            "id": str(scan_id),
            "project_id": None,
            "repo_url": "",
            "repo_name": ""
        }
        
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-id"
        
        with patch('services.supabase_client.get_scan') as mock_get_scan, \
             patch('services.supabase_client.get_projects_batch') as mock_batch:
            
            mock_get_scan.return_value = mock_scan
            
            result = await get_scan_detail(scan_id, mock_request)
            
            # Batch should not be called when there's no project_id
            mock_batch.assert_not_called()
            
            assert result["repo_url"] == ""
            assert result["repo_name"] == ""

    @pytest.mark.asyncio
    async def test_get_scan_detail_scan_not_found(self):
        """Test that get_scan_detail raises 404 when scan not found."""
        scan_id = UUID("12345678-1234-5678-1234-567812345678")
        
        mock_request = MagicMock()
        mock_request.state.user_id = "test-user-id"
        
        with patch('services.supabase_client.get_scan') as mock_get_scan:
            
            # Scan not found
            mock_get_scan.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await get_scan_detail(scan_id, mock_request)
            
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Scan not found"
