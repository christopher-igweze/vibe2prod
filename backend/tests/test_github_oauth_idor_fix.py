"""Tests for GitHub OAuth IDOR vulnerability fix (F-1bd2cf47).

These tests verify that the list_github_repos endpoint properly filters
repositories using the affiliation parameter instead of type=all,
preventing IDOR attacks where users could access repos their token can
see but aren't linked to their Vibe2Prod account.

Test Location: tests/test_github_oauth_idor_fix.py
Project: api/routes/github_oauth.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import using relative path based on project structure
# Try multiple import paths to handle different project layouts
try:
    from api.routes.github_oauth import list_github_repos
except ImportError:
    try:
        from routes.github_oauth import list_github_repos
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        try:
            from api.routes.github_oauth import list_github_repos
        except ImportError:
            raise ImportError("Could not import list_github_repos from any known path")


class TestListGithubReposIdorFix:
    """Test suite for list_github_repos IDOR vulnerability fix."""

    @pytest.mark.asyncio
    async def test_list_github_repos_uses_affiliation_parameter(self):
        """Test that list_github_repos uses affiliation parameter instead of type=all.
        
        This verifies the fix for IDOR vulnerability where users could access
        all repositories their GitHub token has access to, not just those linked
        to their Vibe2Prod account.
        """
        with patch('api.routes.github_oauth.db.get_github_access_token') as mock_get_token, \
             patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
            
            # Setup mock token retrieval
            mock_get_token.return_value = "test_github_token"
            
            # Setup mock HTTP client
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Mock successful GitHub API response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {"id": 1, "name": "owned-repo", "full_name": "testuser/owned-repo"},
                {"id": 2, "name": "collaborator-repo", "full_name": "testuser/collaborator-repo"},
            ]
            mock_client.get.return_value = mock_response
            
            # Create mock request with user_id
            mock_request = MagicMock()
            mock_request.state.user_id = "test_user_id"
            
            # Call the function
            result = await list_github_repos(mock_request, page=1, per_page=30)
            
            # Verify the GitHub API was called with affiliation parameter
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            
            # Check that the URL contains affiliation parameter
            called_url = call_args[0][0] if call_args[0] else str(call_args)
            params = call_args[1].get('params', {}) if isinstance(call_args[1], dict) else {}
            
            # The fix: should use affiliation instead of type
            assert 'affiliation' in params, "Expected 'affiliation' parameter in GitHub API call"
            assert params['affiliation'] == 'owner,collaborator,organization_member', \
                f"Expected affiliation='owner,collaborator,organization_member', got '{params.get('affiliation')}'"
            # Ensure the old vulnerable parameter is not used
            assert params.get('type') != 'all', "Parameter 'type=all' should not be used (IDOR vulnerability)"
            
    @pytest.mark.asyncio
    async def test_list_github_repos_affiliation_value_correct(self):
        """Test that affiliation parameter contains all required values.
        
        The fix should filter to repos where user is owner, collaborator,
        or organization member - excluding non-linked repos.
        """
        with patch('api.routes.github_oauth.db.get_github_access_token') as mock_get_token, \
             patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
            
            mock_get_token.return_value = "test_github_token"
            
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response
            
            mock_request = MagicMock()
            mock_request.state.user_id = "test_user_id"
            
            await list_github_repos(mock_request, page=1, per_page=30)
            
            # Extract params from the call
            call_kwargs = mock_client.get.call_args[1]
            params = call_kwargs.get('params', {})
            
            # Verify the affiliation parameter contains all required affiliations
            affiliation_value = params.get('affiliation', '')
            assert 'owner' in affiliation_value, "affiliation must include 'owner'"
            assert 'collaborator' in affiliation_value, "affiliation must include 'collaborator'"
            assert 'organization_member' in affiliation_value, "affiliation must include 'organization_member'"
            
    @pytest.mark.asyncio
    async def test_list_github_repos_does_not_use_type_all(self):
        """Test that type=all parameter is not used (vulnerable to IDOR).
        
        The original vulnerable code used 'type': 'all' which allowed
        access to all repos the token could see, regardless of whether
        they were linked to the user's Vibe2Prod account.
        """
        with patch('api.routes.github_oauth.db.get_github_access_token') as mock_get_token, \
             patch('api.routes.github_oauth.httpx.AsyncClient') as mock_client_class:
            
            mock_get_token.return_value = "test_github_token"
            
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_client.get.return_value = mock_response
            
            mock_request = MagicMock()
            mock_request.state.user_id = "test_user_id"
            
            await list_github_repos(mock_request, page=1, per_page=30)
            
            # Get all params passed to the GitHub API
            call_kwargs = mock_client.get.call_args[1]
            params = call_kwargs.get('params', {})
            
            # The fix removes type=all to prevent IDOR
            assert params.get('type') != 'all', \
                "GitHub API should not be called with type='all' - this is the IDOR vulnerability"
