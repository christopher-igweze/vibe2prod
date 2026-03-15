"""Tests for GitHub OAuth error handling."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

# Import the module being tested
from api.routes import github_oauth


class TestFetchGitHubProfileErrorHandling:
    """Test cases for _fetch_github_profile error handling."""

    @pytest.mark.asyncio
    async def test_http_status_error_404_provides_specific_message(self):
        """Test that HTTPStatusError with 404 provides specific error message."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=error)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name is None
            assert "404" in email or "not found" in email.lower() or "Not Found" in email

    @pytest.mark.asyncio
    async def test_http_status_error_403_provides_specific_message(self):
        """Test that HTTPStatusError with 403 provides specific error message."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        
        error = httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=error)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name is None
            assert "403" in email or "forbidden" in email.lower() or "Forbidden" in email

    @pytest.mark.asyncio
    async def test_http_status_error_500_provides_specific_message(self):
        """Test that HTTPStatusError with 500 provides specific error message."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        error = httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=error)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name is None
            assert "500" in email or "server error" in email.lower() or "Internal Server Error" in email

    @pytest.mark.asyncio
    async def test_request_error_provides_specific_message(self):
        """Test that RequestError provides specific error message."""
        error = httpx.RequestError("Request failed", request=MagicMock())
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=error)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name is None
            assert email is not None
            assert len(email) > 0

    @pytest.mark.asyncio
    async def test_timeout_exception_still_handled(self):
        """Test that TimeoutException is still handled (existing behavior)."""
        error = httpx.TimeoutException("Request timed out")
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=error)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name is None
            assert email is not None

    @pytest.mark.asyncio
    async def test_connect_error_still_handled(self):
        """Test that ConnectError is still handled (existing behavior)."""
        error = httpx.ConnectError("Connection failed")
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_client.get = AsyncMock(side_effect=error)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name is None
            assert email is not None

    @pytest.mark.asyncio
    async def test_successful_profile_fetch_returns_name_and_email(self):
        """Test that successful profile fetch returns name and email."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "login": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        with patch.object(github_oauth, 'client') as mock_client:
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            
            name, email = await github_oauth._fetch_github_profile("test_token")
            
            assert name == "Test User"
            assert email == "test@example.com"
