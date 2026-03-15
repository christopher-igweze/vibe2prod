"""Tests for onboarding route error handling.

These tests verify that the save_org_onboarding endpoint properly handles
database errors by catching exceptions and returning a 503 Service Unavailable
response instead of letting FastAPI return a generic 500 error.

Test Location: tests/test_onboarding_error_handling.py
Framework: pytest
"""

import sys
import os

# Add backend directory to path for imports
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Mock the api module before importing the onboarding route
with patch.dict('sys.modules', {
    'api': MagicMock(),
    'api.middleware': MagicMock(),
    'api.middleware.rate_limit': MagicMock(limiter=MagicMock(), rate_limit_string=MagicMock(return_value='10/minute')),
}):
    from api.routes.onboarding import save_org_onboarding
    from models.onboarding import OrgOnboardingPayload


class TestOnboardingErrorHandling:
    """Test suite for onboarding route error handling."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object with user_id."""
        request = MagicMock()
        request.state.user_id = "test-user-123"
        return request

    @pytest.fixture
    def onboarding_payload(self):
        """Create a valid onboarding payload."""
        return OrgOnboardingPayload(
            org_name="Test Org",
            org_domain="test.com"
        )

    @pytest.mark.asyncio
    async def test_save_org_onboarding_handles_database_error(self, mock_request, onboarding_payload):
        """Test that save_org_onboarding returns 503 when database operation fails."""
        with patch('api.routes.onboarding.db.save_org_onboarding', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = Exception("Database connection failed")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await save_org_onboarding(onboarding_payload, mock_request)
            
            assert exc_info.value.status_code == 503
            assert "temporarily unavailable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_save_org_onboarding_handles_specific_db_exception(self, mock_request, onboarding_payload):
        """Test that save_org_onboarding handles specific database exceptions."""
        with patch('api.routes.onboarding.db.save_org_onboarding', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = ConnectionError("Failed to connect to database")
            
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await save_org_onboarding(onboarding_payload, mock_request)
            
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_save_org_onboarding_success_case(self, mock_request, onboarding_payload):
        """Test that save_org_onboarding returns success when database operation succeeds."""
        with patch('api.routes.onboarding.db.save_org_onboarding', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = None  # Successful DB operation
            
            response = await save_org_onboarding(onboarding_payload, mock_request)
            
            assert response.status == "ok"
            assert "saved" in response.message.lower()

    @pytest.mark.asyncio
    async def test_save_org_onboarding_logs_error_on_failure(self, mock_request, onboarding_payload):
        """Test that save_org_onboarding logs the error when database operation fails."""
        with patch('api.routes.onboarding.db.save_org_onboarding', new_callable=AsyncMock) as mock_save:
            with patch('api.routes.onboarding.logger') as mock_logger:
                mock_save.side_effect = Exception("Database error")
                
                from fastapi import HTTPException
                with pytest.raises(HTTPException):
                    await save_org_onboarding(onboarding_payload, mock_request)
                
                # Verify error was logged with user context
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args[0][0]
                assert "test-user-123" in call_args
                assert "Database error" in call_args
