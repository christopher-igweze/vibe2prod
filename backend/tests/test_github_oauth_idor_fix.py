"""Tests for IDOR vulnerability fix in GitHub repository branch listing.

These tests verify that the list_repo_branches endpoint properly validates
repository ownership before allowing access to branch data.

Test Location: tests/test_github_oauth_idor_fix.py
Project: api/routes/github_oauth.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
import httpx

# Import the function using the same pattern as existing tests
try:
    from api.routes.github_oauth import list_repo_branches
except ImportError:
    try:
        from routes.github_oauth import list_repo_branches
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from api.routes.github_oauth import list_repo_branches
        else:
            raise ImportError("Could not import list_repo_branches from any known path")


class TestListRepoBranchesOwnershipValidation:
    """Test suite for repository ownership validation in list_repo_branches."""

    @pytest.mark.asyncio
    async def test_list_branches_rejects_unauthorized_repo(self):
        """Test that list_repo_branches rejects access to repos not owned by user.
        
        This verifies the IDOR fix: when a user tries to access branches of a repository
        that is NOT linked to their account, they should receive a 403 error.
        """
        # Mock the request object with user_id
        mock_request = MagicMock()
        mock_request.state.user_id = "user_123"
        
        # Mock project that will be returned as None (repo NOT linked to user)
        with patch('api.routes.github_oauth.db') as mock_db:
            mock_db.get_github_access_token = AsyncMock(return_value="gh_token_abc")
            
            # Mock db.get_project_by_repo_url to return None (repo NOT linked to user)
            mock_db.get_project_by_repo_url = AsyncMock(return_value=None)
            
            # Attempt to call the endpoint
            with pytest.raises(HTTPException) as exc_info:
                await list_repo_branches(
                    owner="some_other_user",
                    repo="their_private_repo",
                    request=mock_request
                )
            
            # Verify the 403 error is raised with correct error code
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["code"] == "repo_not_authorized"
            assert "don't have access" in exc_info.value.detail["message"].lower()
            
            # Verify db.get_project_by_repo_url was called with correct args
            mock_db.get_project_by_repo_url.assert_called_once()
            call_args = mock_db.get_project_by_repo_url.call_args
            assert call_args[0][0] == "user_123"  # user_id
            assert call_args[0][1] == "https://github.com/some_other_user/their_private_repo"
    
    @pytest.mark.asyncio
    async def test_list_branches_allows_authorized_repo(self):
        """Test that list_repo_branches allows access to repos linked to user's account.
        
        This verifies the fix doesn't break legitimate access: when a user tries to access
        branches of a repository that IS linked to their account, they should proceed
        to the GitHub API call.
        """
        # Mock the request object with user_id
        mock_request = MagicMock()
        mock_request.state.user_id = "user_123"
        
        # Mock project that would be returned for an authorized repo
        mock_project = MagicMock()
        mock_project.id = "project_456"
        mock_project.repo_url = "https://github.com/my_org/my_repo"
        
        with patch('api.routes.github_oauth.db') as mock_db, \
             patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
            mock_db.get_github_access_token = AsyncMock(return_value="gh_token_abc")
            
            # Mock db.get_project_by_repo_url to return a project (repo IS linked to user)
            mock_db.get_project_by_repo_url = AsyncMock(return_value=mock_project)
            
            # Mock httpx.AsyncClient to return branch data
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value.status_code = 200
            mock_client.get.return_value.json.return_value = [
                {"name": "main", "commit": {"sha": "abc123"}},
                {"name": "develop", "commit": {"sha": "def456"}}
            ]
            
            # Call the endpoint - should NOT raise 403
            result = await list_repo_branches(
                owner="my_org",
                repo="my_repo",
                request=mock_request
            )
            
            # Verify the result contains branch data
            assert result is not None
            assert len(result) == 2
            assert result[0]["name"] == "main"
            
            # Verify GitHub API was called
            mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_branches_requires_github_connection(self):
        """Test that list_repo_branches rejects users without GitHub connected.
        
        This is an existing check that should still work after the IDOR fix.
        """
        mock_request = MagicMock()
        mock_request.state.user_id = "user_123"
        
        with patch('api.routes.github_oauth.db') as mock_db:
            # User has no GitHub token connected
            mock_db.get_github_access_token = AsyncMock(return_value=None)
            
            with pytest.raises(HTTPException) as exc_info:
                await list_repo_branches(
                    owner="some_owner",
                    repo="some_repo",
                    request=mock_request
                )
            
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["code"] == "github_not_connected"
