"""Tests for GitHub service error handling.

These tests verify that the GitHub API functions (get_repo_info,
create_pull_request, get_head_sha) properly handle various network
failures and API errors by raising appropriate HTTPExceptions.

Test Location: backend/tests/test_github_error_handling.py
Project: backend
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from fastapi import HTTPException

from backend.services.github import get_repo_info, create_pull_request, get_head_sha


class TestGetRepoInfoErrorHandling:
    """Test suite for get_repo_info error handling."""

    @pytest.mark.asyncio
    async def test_get_repo_info_handles_timeout_exception(self):
        """Test that get_repo_info handles httpx.TimeoutException gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await get_repo_info("owner", "repo")

            assert exc_info.value.status_code == 504
            assert exc_info.value.detail["code"] == "github_timeout"

    @pytest.mark.asyncio
    async def test_get_repo_info_handles_connect_error(self):
        """Test that get_repo_info handles httpx.ConnectError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await get_repo_info("owner", "repo")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_unreachable"

    @pytest.mark.asyncio
    async def test_get_repo_info_handles_404_not_found(self):
        """Test that get_repo_info handles 404 Not Found error."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"message": "Not Found"}
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=mock_response
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_repo_info("owner", "repo")

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["code"] == "repo_not_found"

    @pytest.mark.asyncio
    async def test_get_repo_info_handles_403_rate_limit(self):
        """Test that get_repo_info handles 403 rate limit error."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.json.return_value = {"message": "Rate limit exceeded"}
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "403 Forbidden", request=MagicMock(), response=mock_response
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_repo_info("owner", "repo")

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["code"] == "github_rate_limited"

    @pytest.mark.asyncio
    async def test_get_repo_info_handles_request_error(self):
        """Test that get_repo_info handles httpx.RequestError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Request failed")

            with pytest.raises(HTTPException) as exc_info:
                await get_repo_info("owner", "repo")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_request_error"

    @pytest.mark.asyncio
    async def test_get_repo_info_success(self):
        """Test that get_repo_info returns RepoInfo on success."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "owner": {"login": "owner"},
                "name": "repo",
                "full_name": "owner/repo",
                "default_branch": "main",
                "clone_url": "https://github.com/owner/repo.git",
                "private": False,
            }
            mock_client.get.return_value = mock_response

            result = await get_repo_info("owner", "repo")

            assert result.owner == "owner"
            assert result.name == "repo"
            assert result.full_name == "owner/repo"


class TestCreatePullRequestErrorHandling:
    """Test suite for create_pull_request error handling."""

    @pytest.mark.asyncio
    async def test_create_pull_request_handles_timeout_exception(self):
        """Test that create_pull_request handles httpx.TimeoutException gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await create_pull_request("owner", "repo", "title", "body", "head", "base", "token")

            assert exc_info.value.status_code == 504
            assert exc_info.value.detail["code"] == "github_timeout"

    @pytest.mark.asyncio
    async def test_create_pull_request_handles_connect_error(self):
        """Test that create_pull_request handles httpx.ConnectError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await create_pull_request("owner", "repo", "title", "body", "head", "base", "token")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_unreachable"

    @pytest.mark.asyncio
    async def test_create_pull_request_handles_http_status_error(self):
        """Test that create_pull_request handles httpx.HTTPStatusError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 502
            mock_response.json.return_value = {"message": "Bad Gateway"}
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "502 Bad Gateway", request=MagicMock(), response=mock_response
            )

            with pytest.raises(HTTPException) as exc_info:
                await create_pull_request("owner", "repo", "title", "body", "head", "base", "token")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_api_error"

    @pytest.mark.asyncio
    async def test_create_pull_request_handles_request_error(self):
        """Test that create_pull_request handles httpx.RequestError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Request failed")

            with pytest.raises(HTTPException) as exc_info:
                await create_pull_request("owner", "repo", "title", "body", "head", "base", "token")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_request_error"

    @pytest.mark.asyncio
    async def test_create_pull_request_success(self):
        """Test that create_pull_request returns URL on success."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"html_url": "https://github.com/owner/repo/pull/1"}
            mock_client.post.return_value = mock_response

            result = await create_pull_request("owner", "repo", "title", "body", "head", "base", "token")

            assert result == "https://github.com/owner/repo/pull/1"


class TestGetHeadShaErrorHandling:
    """Test suite for get_head_sha error handling."""

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_timeout_exception(self):
        """Test that get_head_sha handles httpx.TimeoutException gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(HTTPException) as exc_info:
                await get_head_sha("owner", "repo", "branch")

            assert exc_info.value.status_code == 504
            assert exc_info.value.detail["code"] == "github_timeout"

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_connect_error(self):
        """Test that get_head_sha handles httpx.ConnectError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await get_head_sha("owner", "repo", "branch")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_unreachable"

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_404_not_found(self):
        """Test that get_head_sha handles 404 Not Found error (branch not found)."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"message": "Not Found"}
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=MagicMock(), response=mock_response
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_head_sha("owner", "repo", "nonexistent-branch")

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail["code"] == "branch_not_found"

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_http_status_error(self):
        """Test that get_head_sha handles httpx.HTTPStatusError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 502
            mock_response.json.return_value = {"message": "Bad Gateway"}
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "502 Bad Gateway", request=MagicMock(), response=mock_response
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_head_sha("owner", "repo", "branch")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_api_error"

    @pytest.mark.asyncio
    async def test_get_head_sha_handles_request_error(self):
        """Test that get_head_sha handles httpx.RequestError gracefully."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Request failed")

            with pytest.raises(HTTPException) as exc_info:
                await get_head_sha("owner", "repo", "branch")

            assert exc_info.value.status_code == 502
            assert exc_info.value.detail["code"] == "github_request_error"

    @pytest.mark.asyncio
    async def test_get_head_sha_success(self):
        """Test that get_head_sha returns SHA on success."""
        with patch('backend.services.github.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"sha": "abc123def456"}
            mock_client.get.return_value = mock_response

            result = await get_head_sha("owner", "repo", "main")

            assert result == "abc123def456"
