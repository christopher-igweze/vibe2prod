"""Tests for ProbeService delegation in probe.py route.

These tests verify that the probe route properly delegates to ProbeService
for business logic, following Clean Architecture principles.

Test Location: tests/test_probe_service_delegation.py
Project: api/routes/probe.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4


class TestProbeServiceDelegation:
    """Test suite for ProbeService delegation in probe.py route."""

    @pytest.mark.asyncio
    async def test_run_probe_delegates_to_service(self):
        """Test that _run_probe delegates to probe_service.run_probe."""
        probe_id = "probe-123"
        target_url = "https://example.com"
        user_id = "user-456"
        probe_type = "full"
        config = {"timeout": 30}

        with patch('api.routes.probe.probe_service') as mock_probe_service:
            from api.routes.probe import _run_probe
            
            await _run_probe(
                probe_id=probe_id,
                target_url=target_url,
                user_id=user_id,
                probe_type=probe_type,
                config=config,
            )

            # Verify probe_service.run_probe was called with correct arguments
            mock_probe_service.run_probe.assert_called_once_with(
                probe_id=probe_id,
                target_url=target_url,
                user_id=user_id,
                probe_type=probe_type,
                config=config,
            )


class TestProbeRouteThinOrchestration:
    """Test that route handlers are thin and delegate to services."""

    def test_route_imports_probe_service(self):
        """Test that probe.py route imports probe_service module."""
        from api.routes import probe
        
        # Verify probe_service is imported in the route module
        assert hasattr(probe, 'probe_service')
        assert probe.probe_service is not None

    def test_route_background_task_uses_service_delegation(self):
        """Test that probe.py route's background task delegates to service."""
        from api.routes import probe
        
        import inspect
        source = inspect.getsource(probe._run_probe)
        
        # Should contain delegation to probe_service
        assert 'probe_service.run_probe' in source
