"""Tests for /health endpoint exception handling.

These tests verify that the /health endpoint properly catches exceptions
raised by check_database_health() and returns a 503 status code instead
of allowing the exception to propagate as a 500 Internal Server Error.

Test Location: tests/test_health_endpoint_exception_handling.py
Project: backend/main.py, backend/services/supabase_client.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


# Import FastAPI app from main.py - try multiple import paths
try:
    from backend.main import app
except ImportError:
    try:
        from main import app
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from main import app
        else:
            raise ImportError("Could not import app from main.py")


class TestHealthEndpointExceptionHandling:
    """Test suite for /health endpoint exception handling.

    Verifies that when check_database_health raises an unexpected exception
    (rather than returning False), the endpoint returns 503 instead of 500.
    This prevents unhandled exceptions from leaking as 500 Internal Server Errors.
    """

    @pytest.fixture
    def client(self):
        """Create a TestClient for the FastAPI app.
        
        The /health endpoint is excluded from auth middleware, so no token needed.
        raise_server_exceptions=False allows us to capture 500 errors without them
        propagating as exceptions.
        """
        return TestClient(app, raise_server_exceptions=False)

    def test_health_returns_503_on_runtime_error(self, client):
        """Test that /health returns 503 when check_database_health raises RuntimeError."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected DB failure"),
        ):
            response = client.get("/health")

        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"
        assert "Unexpected DB failure" in body["message"]

    def test_health_returns_503_on_connection_error(self, client):
        """Test that /health returns 503 on low-level connection errors.
        
        Verifies that ConnectionError exceptions are properly caught and converted
        to 503 responses rather than 500 errors.
        """
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Network unreachable"),
        ):
            response = client.get("/health")

        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"
        assert "Network unreachable" in body["message"]

    def test_health_returns_503_on_timeout_error(self, client):
        """Test that /health returns 503 on timeout exceptions."""
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=TimeoutError("Database query timeout"),
        ):
            response = client.get("/health")

        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"
        assert "timeout" in body["message"].lower()

    def test_health_returns_503_on_generic_exception(self, client):
        """Test that /health returns 503 on any generic Exception.
        
        This ensures broad exception coverage - if check_database_health raises
        any exception type, it should be caught and result in 503, not 500.
        """
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=Exception("Some unexpected error"),
        ):
            response = client.get("/health")

        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "error"

    def test_health_returns_503_when_check_returns_false(self, client):
        """Test that /health returns 503 when check_database_health returns False.
        
        This is the normal unhealthy case (not an exception), should still return 503.
        """
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = client.get("/health")

        assert response.status_code == 503, f"Expected 503, got {response.status_code}"
        body = response.json()
        assert body["status"] == "unhealthy"
        assert body["database"] == "unavailable"

    def test_health_returns_200_when_database_healthy(self, client):
        """Test that /health returns 200 when check_database_health returns True.
        
        Verifies the happy path - database is healthy.
        """
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = client.get("/health")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        body = response.json()
        assert body["status"] == "healthy"
        assert body["database"] == "available"

    def test_health_response_contains_error_message_on_exception(self, client):
        """Test that error messages from exceptions are included in response.
        
        Ensures the error message is preserved in the response JSON for debugging.
        """
        error_msg = "Database connection pool exhausted"
        with patch(
            "services.supabase_client.check_database_health",
            new_callable=AsyncMock,
            side_effect=RuntimeError(error_msg),
        ):
            response = client.get("/health")

        body = response.json()
        assert body["message"] == error_msg

    def test_health_endpoint_never_returns_500_on_check_exception(self, client):
        """Test that /health never returns 500 when check_database_health raises.
        
        This is the core regression test - verifies the fix prevents 500 errors.
        Any exception should result in 503, not 500.
        """
        exception_types = [
            RuntimeError("DB error"),
            ConnectionError("Connection failed"),
            TimeoutError("Timeout"),
            ValueError("Invalid response"),
            OSError("OS error"),
        ]
        
        for exc in exception_types:
            with patch(
                "services.supabase_client.check_database_health",
                new_callable=AsyncMock,
                side_effect=exc,
            ):
                response = client.get("/health")
                assert response.status_code == 503, (
                    f"Expected 503 for {type(exc).__name__}, got {response.status_code}"
                )
                # Ensure it's not a 500
                assert response.status_code != 500
