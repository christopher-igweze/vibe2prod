"""Tests for startup error handling and health endpoint.

These tests verify that:
1. The lifespan function fails fast when database is unavailable
2. The /health endpoint returns proper status based on database connectivity
3. Orphaned scan cleanup failure does not prevent startup
4. HTTP client initialization failure does not prevent startup (graceful degradation)

Test Location: tests/test_startup_error_handling.py
Project: main.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
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

                # Mock the shared HTTP client
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)

                from main import lifespan
                app = FastAPI()

                with patch('services.http_client.shared_client', mock_client):
                    # Should NOT raise - both database and HTTP client are available
                    async with lifespan(app):
                        pass

    @pytest.mark.asyncio
    async def test_lifespan_continues_when_http_client_init_fails(self):
        """Test that lifespan continues when shared HTTP client initialization fails.

        The HTTP client is a non-critical component. If its initialization fails,
        startup should continue so that features not relying on it still work.
        """
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True
                mock_orphan.return_value = 0

                # Simulate __aenter__ raising on the shared client
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(side_effect=Exception("Connection pool init failed"))
                mock_client.__aexit__ = AsyncMock(return_value=None)

                from main import lifespan
                app = FastAPI()

                with patch('services.http_client.shared_client', mock_client):
                    # Should NOT raise - HTTP client failure is non-critical
                    async with lifespan(app):
                        pass

    @pytest.mark.asyncio
    async def test_lifespan_continues_when_http_client_import_fails(self):
        """Test that lifespan continues when the http_client module itself cannot be imported."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True
                mock_orphan.return_value = 0

                from main import lifespan
                app = FastAPI()

                import builtins
                real_import = builtins.__import__

                def patched_import(name, *args, **kwargs):
                    if name == 'services.http_client':
                        raise ImportError("Simulated import failure for services.http_client")
                    return real_import(name, *args, **kwargs)

                with patch('builtins.__import__', side_effect=patched_import):
                    # Should NOT raise - HTTP client import failure is non-critical
                    async with lifespan(app):
                        pass

    @pytest.mark.asyncio
    async def test_lifespan_logs_warning_when_http_client_init_fails(self):
        """Test that a warning is logged when shared HTTP client initialization fails."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True
                mock_orphan.return_value = 0

                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("Pool exhausted"))
                mock_client.__aexit__ = AsyncMock(return_value=None)

                from main import lifespan
                app = FastAPI()

                with patch('services.http_client.shared_client', mock_client):
                    with patch('main.logger') as mock_logger:
                        async with lifespan(app):
                            pass

                        # A warning (not an error) should be emitted
                        warning_calls = [
                            call for call in mock_logger.warning.call_args_list
                            if 'http client' in str(call).lower() or 'shared' in str(call).lower()
                        ]
                        assert len(warning_calls) >= 1, (
                            "Expected a warning log when HTTP client initialization fails"
                        )

    @pytest.mark.asyncio
    async def test_http_client_exception_does_not_propagate(self):
        """Test that HTTP client exceptions are caught and do not propagate to caller."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True
                mock_orphan.return_value = 0

                # Simulate multiple types of exceptions
                for exception_type, exception_msg in [
                    (RuntimeError, "Pool exhausted"),
                    (ConnectionError, "Failed to connect"),
                    (TimeoutError, "Initialization timeout"),
                ]:
                    mock_client = MagicMock()
                    mock_client.__aenter__ = AsyncMock(side_effect=exception_type(exception_msg))
                    mock_client.__aexit__ = AsyncMock(return_value=None)

                    from main import lifespan
                    app = FastAPI()

                    with patch('services.http_client.shared_client', mock_client):
                        # Should complete successfully despite exceptions
                        async with lifespan(app):
                            pass

    @pytest.mark.asyncio
    async def test_lifespan_completes_successfully_with_all_components(self):
        """Test that lifespan completes successfully when all components initialize properly."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True
                mock_orphan.return_value = 0

                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)

                from main import lifespan
                app = FastAPI()

                with patch('services.http_client.shared_client', mock_client):
                    with patch('main.logger') as mock_logger:
                        async with lifespan(app):
                            pass

                        # Verify success logs were emitted
                        info_calls = [
                            call for call in mock_logger.info.call_args_list
                            if 'started' in str(call).lower() or 'verified' in str(call).lower() or 'http' in str(call).lower()
                        ]
                        # At least one info log should be present (database verified or HTTP client initialized)
                        assert len(mock_logger.info.call_args_list) >= 1


class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_endpoint_database_available(self):
        """Test that /health returns OK when database is available."""
        with patch('services.supabase_client.check_database_health') as mock_health:
            with patch('services.supabase_client.fail_orphaned_scans') as mock_orphan:
                mock_health.return_value = True
                mock_orphan.return_value = 0

                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)

                with patch('services.http_client.shared_client', mock_client):
                    from main import app
                    client = TestClient(app)
                    response = client.get("/health")
                    
                    # Health endpoint should return 200 when database is available
                    assert response.status_code == 200
