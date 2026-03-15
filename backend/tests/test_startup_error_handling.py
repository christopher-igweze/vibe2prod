"""Tests for startup error handling and health endpoint.

These tests verify that:
1. The lifespan function fails fast when database is unavailable
2. The /health endpoint returns proper status based on database connectivity
3. Orphaned scan cleanup failure does not prevent startup

Test Location: tests/test_startup_error_handling.py
Project: main.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestStartupErrorHandling:
    """Test suite for startup error handling."""

    @pytest.mark.asyncio
    async def test_lifespan_fails_fast_when_database_unavailable(self):
        """Test that lifespan raises RuntimeError when database health check fails."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            mock_health.return_value = False  # Database unavailable
            
            # Re-create the app to test lifespan
            from main import lifespan
            app = FastAPI()
            
            # Lifespan should fail fast when database is unavailable
            with pytest.raises(RuntimeError) as exc_info:
                async with lifespan(app):
                    pass
            
            # Should raise specific error about database unavailability
            assert "database" in str(exc_info.value).lower() or "unavailable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_lifespan_succeeds_when_database_available(self):
        """Test that lifespan completes successfully when database is available."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True  # Database available
                mock_orphan.return_value = 0  # No orphaned scans
                
                from main import lifespan
                app = FastAPI()
                
                # Should not raise when database is available
                async with lifespan(app):
                    pass

    @pytest.mark.asyncio
    async def test_lifespan_continues_when_orphan_cleanup_fails(self):
        """Test that lifespan continues when orphaned scan cleanup fails."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True  # Database available
                mock_orphan.side_effect = Exception("Cleanup failed")
                
                from main import lifespan
                app = FastAPI()
                
                # Should NOT raise - cleanup failure is not critical
                # The lifespan should complete even if cleanup fails
                async with lifespan(app):
                    pass


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_endpoint_returns_healthy_when_database_available(self):
        """Test that /health returns 200 with healthy status when database is reachable."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            mock_health.return_value = True
            
            from main import app
            client = TestClient(app, raise_server_exceptions=False)
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data.get("database") == "available"

    def test_health_endpoint_returns_unhealthy_when_database_unavailable(self):
        """Test that /health returns 503 with unhealthy status when database is unreachable."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            mock_health.return_value = False
            
            from main import app
            client = TestClient(app, raise_server_exceptions=False)
            
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data.get("database") == "unavailable"

    def test_health_endpoint_returns_503_on_database_error(self):
        """Test that /health returns 503 when database health check raises exception."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            mock_health.side_effect = Exception("Database error")
            
            from main import app
            client = TestClient(app, raise_server_exceptions=False)
            
            response = client.get("/health")
            
            # Should return 503 service unavailable even on exception
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
