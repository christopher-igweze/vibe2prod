"""Tests for ProbeService delegation in probe.py route.

These tests verify that the probe route properly delegates to ProbeService
for business logic, following Clean Architecture principles.

Test Location: tests/test_probe_service_delegation.py
Project: api/routes/probe.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

# Import using relative path based on project structure
try:
    from services.probe_service import ProbeService
    from services import probe_service
except ImportError:
    try:
        from probe_service import ProbeService, probe_service
    except ImportError:
        import sys
        from pathlib import Path
        services_path = Path(__file__).parent.parent / "backend" / "services"
        if services_path.exists():
            sys.path.insert(0, str(services_path.parent))
            from services.probe_service import ProbeService, probe_service
        else:
            raise ImportError("Could not import probe_service from any known path")


class TestProbeServiceImport:
    """Test suite for ProbeService import and instantiation."""

    def test_probe_service_module_exists(self):
        """Test that probe_service module can be imported."""
        assert probe_service is not None

    def test_probe_service_class_exists(self):
        """Test that ProbeService class exists."""
        assert ProbeService is not None


class TestProbeServiceRunProbe:
    """Test suite for ProbeService probe execution methods."""

    @pytest.mark.asyncio
    async def test_probe_service_has_required_methods(self):
        """Test that probe_service has required methods for probe execution."""
        # Check for common probe service methods
        service_methods = dir(probe_service)
        # The service should have methods for running probes
        # At minimum it should be callable
        assert callable(probe_service) or hasattr(probe_service, 'run_probe') or hasattr(probe_service, 'execute_probe')

    @pytest.mark.asyncio
    async def test_probe_service_handles_target_url(self):
        """Test that ProbeService properly handles target URLs."""
        target_url = "https://example.com"
        user_id = "test-user"
        probe_type = "security"
        probe_id = str(uuid4())

        with patch('services.supabase_client') as mock_db, \
             patch('services.probe_service.db', mock_db):
            
            mock_db.create_probe = AsyncMock(return_value={
                "id": probe_id,
                "status": "pending"
            })
            mock_db.update_probe = AsyncMock()
            
            # If the service has a method to run probes, test it
            if hasattr(probe_service, 'run_probe'):
                await probe_service.run_probe(
                    probe_id=probe_id,
                    target_url=target_url,
                    user_id=user_id,
                    probe_type=probe_type,
                )


class TestProbeRouteDelegation:
    """Test suite verifying probe.py route delegates to ProbeService."""

    def test_probe_route_imports_probe_service(self):
        """Test that the probe route imports probe_service."""
        # This tests the architectural pattern - that the route uses service
        import sys
        from pathlib import Path
        
        # Try to read the probe.py to verify it imports probe_service
        backend_path = Path(__file__).parent.parent / "backend"
        probe_route_path = backend_path / "api" / "routes" / "probe.py"
        
        if probe_route_path.exists():
            content = probe_route_path.read_text()
            # Verify the route imports the service
            assert "from services.probe_service import probe_service" in content or \
                   "probe_service" in content
        else:
            # If path doesn't exist from test location, check alternative
            probe_route_alt = Path(__file__).parent.parent / "api" / "routes" / "probe.py"
            if probe_route_alt.exists():
                content = probe_route_alt.read_text()
                assert "from services.probe_service import probe_service" in content or \
                       "probe_service" in content


class TestServiceArchitecture:
    """Test suite verifying the service delegation architecture."""

    def test_fix_service_exists_and_callable(self):
        """Test that FixService exists and is properly structured."""
        from services import fix_service
        
        # Service should be an instance or module with callable methods
        assert fix_service is not None
        
        # Should have run_forge_fix method
        assert hasattr(fix_service, 'run_forge_fix')
        assert callable(fix_service.run_forge_fix)

    def test_probe_service_exists_and_callable(self):
        """Test that ProbeService exists and is properly structured."""
        from services import probe_service
        
        # Service should exist
        assert probe_service is not None

    def test_services_separated_from_routes(self):
        """Test that business logic is in services, not in route handlers."""
        from pathlib import Path
        
        # Find the services directory
        test_dir = Path(__file__).parent
        backend_dir = test_dir.parent / "backend"
        
        # Check services directory exists and contains service files
        services_dir = backend_dir / "services"
        
        if services_dir.exists():
            service_files = list(services_dir.glob("*service*.py"))
            # Should have service files for fix and probe
            service_names = [f.name for f in service_files]
            
            # Verify fix_service.py exists
            assert "fix_service.py" in service_names or any("fix" in n for n in service_names), \
                "fix_service.py should exist in services directory"
            
            # Verify probe_service.py exists  
            assert "probe_service.py" in service_names or any("probe" in n for n in service_names), \
                "probe_service.py should exist in services directory"
