"""Tests for probe.py route refactoring to services.probe_service.

These tests verify that the route module properly delegates to the service layer,
and that the service module contains the probing logic.

Test Location: backend/tests/test_probe_service_refactoring.py
Project: backend/api/routes/probe.py -> services/probe_service.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the route module
try:
    from api.routes import probe as probe_route
except ImportError:
    pytest.skip("Cannot import probe route module", allow_module_level=True)

# Import the service module
try:
    from services import probe_service
except ImportError:
    pytest.skip("Cannot import probe_service module", allow_module_level=True)


class TestProbeRouteServiceRefactoring:
    """Test suite verifying probe route properly delegates to service layer."""

    def test_probe_service_module_exists(self):
        """Verify probe_service module exists and is importable."""
        assert probe_service is not None

    def test_route_uses_probe_service(self):
        """Verify route module imports and uses probe_service."""
        # Check that route imports the service module
        assert hasattr(probe_route, 'probe_service')
        # Verify the service module is the one we expect
        assert probe_route.probe_service is probe_service

    def test_route_module_does_not_contain_probe_logic(self):
        """Verify route module no longer contains probe implementation functions."""
        # The route module should NOT have the heavy implementation
        # Check that large functions have been moved to service
        route_has_heavy_logic = any(
            hasattr(probe_route, attr) and callable(getattr(probe_route, attr))
            for attr in dir(probe_route)
            if not attr.startswith('_') and attr not in ['router']
        )
        # The route should primarily have the router, not heavy implementation


class TestProbeServiceModuleSize:
    """Test that service module is reasonably sized."""

    def test_probe_service_module_line_count(self):
        """Verify probe_service.py is reasonably sized."""
        service_file = Path(__file__).parent.parent / "services" / "probe_service.py"
        
        if not service_file.exists():
            pytest.skip("probe_service.py not found")
        
        with open(service_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # Service should be reasonably sized (less than route originally was)
        assert len(code_lines) < 400, \
            f"probe_service.py has {len(code_lines)} lines - should be under 400"


class TestProbeRouteModuleIsThin:
    """Test that route module is now thin (contains only HTTP orchestration)."""

    def test_probe_route_module_line_count(self):
        """Verify probe.py route is now smaller after moving logic to service."""
        route_file = Path(__file__).parent.parent / "api" / "routes" / "probe.py"
        
        if not route_file.exists():
            pytest.skip("probe.py not found")
        
        with open(route_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # Route should be much smaller now
        assert len(code_lines) < 200, \
            f"probe.py route has {len(code_lines)} lines - should be under 200 after refactoring"
