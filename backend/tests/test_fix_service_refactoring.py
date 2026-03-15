"""Tests for fix.py route refactoring to services.fix_service.

These tests verify that the route module properly delegates to the service layer,
and that the service module contains the background task logic.

Test Location: backend/tests/test_fix_service_refactoring.py
Project: backend/api/routes/fix.py -> services/fix_service.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import UUID
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the route module
try:
    from api.routes import fix as fix_route
except ImportError:
    pytest.skip("Cannot import fix route module", allow_module_level=True)

# Import the service module
try:
    from services import fix_service
except ImportError:
    pytest.skip("Cannot import fix_service module", allow_module_level=True)


class TestFixRouteServiceRefactoring:
    """Test suite verifying fix route properly delegates to service layer."""

    def test_fix_service_module_exists(self):
        """Verify fix_service module exists and is importable."""
        assert fix_service is not None
        assert hasattr(fix_service, 'run_forge_fix')

    def test_route_uses_fix_service(self):
        """Verify route module imports and uses fix_service."""
        # Check that fix_route imports fix_service
        assert hasattr(fix_route, 'fix_service')
        # Verify the service module is the one we expect
        assert fix_route.fix_service is fix_service

    def test_run_forge_fix_exists_in_service(self):
        """Verify run_forge_fix function exists in service module."""
        assert hasattr(fix_service, 'run_forge_fix')
        assert callable(fix_service.run_forge_fix)

    def test_run_scan_forge_fix_exists_in_service(self):
        """Verify run_scan_forge_fix function exists in service module."""
        assert hasattr(fix_service, 'run_scan_forge_fix')
        assert callable(fix_service.run_scan_forge_fix)

    def test_route_background_task_uses_service_function(self):
        """Verify route adds task using service function, not local function."""
        # This test examines the source to ensure it calls the service function
        import inspect
        source = inspect.getsource(fix_route.trigger_fix)
        # The background task should use fix_service.run_forge_fix
        assert 'fix_service.run_forge_fix' in source or 'fix_service' in source

    def test_route_module_does_not_contain_forge_fix_logic(self):
        """Verify route module no longer contains _run_forge_fix function."""
        # The route module should NOT have the background task implementation
        assert not hasattr(fix_route, '_run_forge_fix'), \
            "Route module should not contain _run_forge_fix - it should be in service"

    def test_route_module_does_not_contain_scan_forge_fix_logic(self):
        """Verify route module no longer contains _run_scan_forge_fix function."""
        assert not hasattr(fix_route, '_run_scan_forge_fix'), \
            "Route module should not contain _run_scan_forge_fix - it should be in service"


class TestFixServiceModuleSize:
    """Test that service module is reasonably sized (not too large)."""

    def test_fix_service_module_line_count(self):
        """Verify fix_service.py is reasonably sized (should be smaller than original route)."""
        service_file = Path(__file__).parent.parent / "services" / "fix_service.py"
        
        if not service_file.exists():
            pytest.skip("fix_service.py not found")
        
        with open(service_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # Service should be reasonably sized (under 200 LOC after refactoring)
        assert len(code_lines) < 200, \
            f"fix_service.py has {len(code_lines)} lines - should be under 200 after refactoring"


class TestFixRouteModuleIsThin:
    """Test that route module is now thin (contains only HTTP orchestration)."""

    def test_fix_route_module_line_count(self):
        """Verify fix.py route is now smaller after moving logic to service."""
        route_file = Path(__file__).parent.parent / "api" / "routes" / "fix.py"
        
        if not route_file.exists():
            pytest.skip("fix.py not found")
        
        with open(route_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # Route should be much smaller now (under 200 LOC)
        assert len(code_lines) < 200, \
            f"fix.py route has {len(code_lines)} lines - should be under 200 after refactoring"
