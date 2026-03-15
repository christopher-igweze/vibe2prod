"""Tests for GitHub repos endpoint pagination improvements.

These tests verify that the list_github_repos endpoint properly implements
cursor-based pagination and returns paginated responses when requested.

Test Location: tests/test_github_repos_pagination.py
Project: backend/api/routes/github_oauth.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import using relative path based on project structure
try:
    from backend.api.routes.github_oauth import list_github_repos, _parse_link_header
except ImportError:
    import sys
    from pathlib import Path
    # Add backend to path if needed
    backend_path = Path(__file__).parent.parent / "backend"
    if backend_path.exists():
        sys.path.insert(0, str(backend_path.parent))
        from api.routes.github_oauth import list_github_repos, _parse_link_header
    else:
        raise ImportError("Could not import list_github_repos from any known path")


class TestParseLinkHeader:
    """Test suite for the _parse_link_header helper function."""

    def test_parse_link_header_with_next(self):
        """Test parsing Link header with next page cursor."""
        link_header = '<https://api.github.com/user/repos?page=2&per_page=30>; rel="next"'
        result = _parse_link_header(link_header)
        assert result is None  # No cursor in page-based URL

    def test_parse_link_header_with_cursor_next(self):
        """Test parsing Link header with cursor-based next page."""
        link_header = '<https://api.github.com/user/repos?per_page=30&cursor=Y3Vyc29yOjEw>; rel="next"'
        result = _parse_link_header(link_header)
        assert result == "Y3Vyc29yOjEw"

    def test_parse_link_header_with_multiple_rels(self):
        """Test parsing Link header with multiple rel types."""
        link_header = '<https://api.github.com/user/repos?per_page=30&cursor=Y3Vyc29yOjEw>; rel="next", <https://api.github.com/user/repos?per_page=30&cursor=Y3Vyc29yOjIw>; rel="last"'
        result = _parse_link_header(link_header)
        assert result == "Y3Vyc29yOjEw"

    def test_parse_link_header_none_input(self):
        """Test parsing None Link header."""
        result = _parse_link_header(None)
        assert result is None

    def test_parse_link_header_empty_string(self):
        """Test parsing empty Link header."""
        result = _parse_link_header("")
        assert result is None

    def test_parse_link_header_no_next(self):
        """Test parsing Link header without next rel (last page)."""
        link_header = '<https://api.github.com/user/repos?per_page=30&cursor=Y3Vyc29yOjIw>; rel="last"'
        result = _parse_link_header(link_header)
        assert result is None


class TestListGithubReposPagination:
    """Test suite for list_github_repos endpoint pagination."""

    @pytest.mark.asyncio
    async def test_list_repos_with_cursor_parameter(self):
        """Test that cursor parameter is passed to GitHub API."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {
            "Link": '<https://api.github.com/user/repos?per_page=30&cursor=abc123>; rel="next"'
        }
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request, cursor="abc123")
            
            # Verify cursor was passed to API
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get('params', {})
            assert params.get("cursor") == "abc123"
            assert "page" not in params

    @pytest.mark.asyncio
    async def test_list_repos_falls_back_to_page_when_no_cursor(self):
        """Test that page parameter is used when cursor is not provided."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {}
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request, page=2)
            
            # Verify page was passed to API
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get('params', {})
            assert params.get("page") == 2
            assert "cursor" not in params

    @pytest.mark.asyncio
    async def test_list_repos_returns_paginated_format_with_paginated_flag(self):
        """Test that paginated=True returns dict with repos and pagination."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {
            "Link": '<https://api.github.com/user/repos?per_page=30&cursor=next123>; rel="next"'
        }
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request, paginated=True)
            
            # Should return paginated format
            assert isinstance(result, dict)
            assert "repos" in result
            assert "pagination" in result
            assert result["pagination"]["next_cursor"] == "next123"
            assert result["pagination"]["has_more"] is True

    @pytest.mark.asyncio
    async def test_list_repos_returns_paginated_format_with_cursor(self):
        """Test that providing cursor returns paginated format."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {
            "Link": '<https://api.github.com/user/repos?per_page=30&cursor=next123>; rel="next"'
        }
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request, cursor="abc123")
            
            # Should return paginated format when cursor is used
            assert isinstance(result, dict)
            assert "repos" in result
            assert "pagination" in result

    @pytest.mark.asyncio
    async def test_list_repos_backward_compatible_without_paginated_flag(self):
        """Test that without paginated flag, returns list for backward compatibility."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {}
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request)
            
            # Should return list for backward compatibility
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["full_name"] == "test/repo"

    @pytest.mark.asyncio
    async def test_list_repos_has_more_false_when_no_next_cursor(self):
        """Test that has_more is False when there's no next page."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {
            "Link": '<https://api.github.com/user/repos?per_page=30&cursor=last123>; rel="last"'
        }
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request, paginated=True)
            
            assert result["pagination"]["has_more"] is False
            assert result["pagination"]["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_list_repos_per_page_capped_at_100(self):
        """Test that per_page is capped at 100."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"
        
        mock_repo = {
            "full_name": "test/repo",
            "name": "repo",
            "private": False,
            "html_url": "https://github.com/test/repo",
            "default_branch": "main",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_repo]
        mock_response.headers = {}
        
        with patch('api.routes.github_oauth.db.get_github_access_token', new_callable=AsyncMock) as mock_token, \
             patch('api.routes.github_oauth.shared_client') as mock_client:
            mock_token.return_value = "fake_token"
            mock_client.get = AsyncMock(return_value=mock_response)
            
            result = await list_github_repos(mock_request, per_page=200)
            
            call_args = mock_client.get.call_args
            params = call_args.kwargs.get('params', {})
            assert params.get("per_page") == 100
