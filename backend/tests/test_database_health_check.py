"""Tests for database health check functionality.

These tests verify that the check_database_health function properly handles
database connectivity and returns appropriate boolean values.

Also tests the /health endpoint's exception handling to ensure that any
unexpected exception raised by check_database_health is caught and returns
a 503 response instead of a 500 Internal Server Error.

Test Location: tests/test_database_health_check.py
Project: services/supabase_client.py, main.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import os


# Import using relative path based on project structure
try:
    from services import supabase_client as db
except ImportError:
    try:
        from supabase_client import check_database_health
    except ImportError:
        import sys
        from pathlib import Path
        # Add services to path if needed
        services_path = Path(__file__).parent.parent / "services"
        if services_path.exists():
            sys.path.insert(0, str(services_path.parent))
            from services.supabase_client import check_database_health
        else:
            raise ImportError("Could not import check_database_health from any known path")


# All required environment variables for Settings to instantiate
BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
}


class TestCheckDatabaseHealth:
    """Test suite for check_database_health function."""

    @pytest.mark.asyncio
    async def test_check_database_health_returns_true_when_database_available(self):
        """Test that check_database_health returns True when database is reachable."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock the table().select().limit().execute() chain
            mock_execute = MagicMock()
            mock_execute.data = [{"id": "some-uuid"}]
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute = AsyncMock(return_value=mock_execute)
            mock_client_instance.table.return_value = mock_table
            
            # Import and call the function
            from services.supabase_client import check_database_health
            result = await check_database_health()
            
            # Should return True when execute succeeds
            assert result is True

    @pytest.mark.asyncio
    async def test_check_database_health_returns_false_when_database_unavailable(self):
        """Test that check_database_health returns False when database is unreachable."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock the table().select().limit().execute() chain to return empty data
            mock_execute = MagicMock()
            mock_execute.data = []
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute = AsyncMock(return_value=mock_execute)
            mock_client_instance.table.return_value = mock_table
            
            # Import and call the function
            from services.supabase_client import check_database_health
            result = await check_database_health()
            
            # Should return False when no data returned
            assert result is False

    @pytest.mark.asyncio
    async def test_check_database_health_returns_false_on_exception(self):
        """Test that check_database_health returns False when an exception is raised."""
        with patch('services.supabase_client._client') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance
            
            # Mock the table().select().limit().execute() to raise an exception
            mock_table = MagicMock()
            mock_table.select.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_instance.table.return_value = mock_table
            
            # Import and call the function
            from services.supabase_client import check_database_health
            result = await check_database_health()
            
            # Should return False when execute raises, not raise
            assert result is False


class TestHealthEndpointExceptionHandling:
    """Test suite for /health endpoint exception handling.

    Verifies that when check_database_health raises an unexpected exception
    (rather than returning False), the endpoint returns 503 instead of 500.
    """

    @pytest.fixture
    def client(self):
        """Create a TestClient for the FastAPI app with auth middleware bypassed."""
        with patch.dict("os.environ", BASE_ENV, clear=False):
            from main import app
            # The /health endpoint is excluded from auth middleware, so no token needed.
            return TestClient(app, raise_server_exceptions=False)

    def test_health_returns_503_when_check_raises_exception(self, client):
        """Test that /health returns 503 when check_database_health raises."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected DB failure"),
        ):
            response = client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"
        assert "Unexpected DB failure" in body["message"]

    def test_health_returns_503_when_check_raises_connection_error(self, client):
        """Test that /health returns 503 on low-level connection errors."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Network unreachable"),
        ):
            response = client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"

    def test_health_returns_503_when_check_returns_false(self, client):
        """Test that /health returns 503 when check_database_health returns False."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "unavailable"

    def test_health_returns_200_when_database_healthy(self, client):
        """Test that /health returns 200 when check_database_health returns True."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["database"] == "available"

    def test_health_returns_503_when_check_raises_timeout_error(self, client):
        """Test that /health returns 503 when check_database_health raises TimeoutError."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=TimeoutError("Database query timeout"),
        ):
            response = client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"
        assert "timeout" in body["message"].lower()

    def test_health_exception_message_preserved(self, client):
        """Test that /health includes exception message in response."""
        error_msg = "Database connection pool exhausted"
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=RuntimeError(error_msg),
        ):
            response = client.get("/health")

        assert response.status_code == 503
        body = response.json()
        assert body["message"] == error_msg
