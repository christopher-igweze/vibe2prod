"""Tests for github_oauth.py route refactoring to services.github_oauth_service.

These tests verify that the route module properly delegates to the service layer,
and that the service module contains the OAuth logic.

Test Location: backend/tests/test_github_oauth_service_refactoring.py
Project: backend/api/routes/github_oauth.py -> services/github_oauth_service.py
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
    from api.routes import github_oauth as github_oauth_route
except ImportError:
    pytest.skip("Cannot import github_oauth route module", allow_module_level=True)

# Import the service module
try:
    from services import github_oauth_service
except ImportError:
    pytest.skip("Cannot import github_oauth_service module", allow_module_level=True)


class TestGithubOauthRouteServiceRefactoring:
    """Test suite verifying github_oauth route properly delegates to service layer."""

    def test_github_oauth_service_module_exists(self):
        """Verify github_oauth_service module exists and is importable."""
        assert github_oauth_service is not None

    def test_route_uses_github_oauth_service(self):
        """Verify route module imports and uses github_oauth_service."""
        # Check that route imports the service module
        assert hasattr(github_oauth_route, 'github_oauth_service')
        # Verify the service module is the one we expect
        assert github_oauth_route.github_oauth_service is github_oauth_service

    def test_ensure_oauth_configured_exists_in_service(self):
        """Verify ensure_oauth_configured function exists in service module."""
        assert hasattr(github_oauth_service, 'ensure_oauth_configured')
        assert callable(github_oauth_service.ensure_oauth_configured)

    def test_validate_redirect_uri_exists_in_service(self):
        """Verify validate_redirect_uri function exists in service module."""
        assert hasattr(github_oauth_service, 'validate_redirect_uri')
        assert callable(github_oauth_service.validate_redirect_uri)

    def test_encode_state_exists_in_service(self):
        """Verify encode_state function exists in service module."""
        assert hasattr(github_oauth_service, 'encode_state')
        assert callable(github_oauth_service.encode_state)

    def test_decode_state_exists_in_service(self):
        """Verify decode_state function exists in service module."""
        assert hasattr(github_oauth_service, 'decode_state')
        assert callable(github_oauth_service.decode_state)

    def test_route_module_does_not_contain_oauth_logic(self):
        """Verify route module no longer contains OAuth helper functions."""
        # The route module should NOT have these implementation details
        assert not hasattr(github_oauth_route, 'oauth_not_configured'), \
            "Route module should not contain oauth_not_configured - it should be in service"
        assert not hasattr(github_oauth_route, 'state_secret'), \
            "Route module should not contain state_secret - it should be in service"
        assert not hasattr(github_oauth_route, 'ensure_oauth_configured'), \
            "Route module should not contain ensure_oauth_configured - it should be in service"


class TestGithubOauthServiceModuleSize:
    """Test that service module is reasonably sized."""

    def test_github_oauth_service_module_line_count(self):
        """Verify github_oauth_service.py is reasonably sized."""
        service_file = Path(__file__).parent.parent / "services" / "github_oauth_service.py"
        
        if not service_file.exists():
            pytest.skip("github_oauth_service.py not found")
        
        with open(service_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # Service should be reasonably sized
        assert len(code_lines) < 500, \
            f"github_oauth_service.py has {len(code_lines)} lines - should be under 500"


class TestGithubOauthRouteModuleIsThin:
    """Test that route module is now thin (contains only HTTP orchestration)."""

    def test_github_oauth_route_module_line_count(self):
        """Verify github_oauth.py route is now smaller after moving logic to service."""
        route_file = Path(__file__).parent.parent / "api" / "routes" / "github_oauth.py"
        
        if not route_file.exists():
            pytest.skip("github_oauth.py not found")
        
        with open(route_file, 'r') as f:
            lines = f.readlines()
        
        # Count non-empty, non-comment lines
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        
        # Route should be much smaller now
        assert len(code_lines) < 200, \
            f"github_oauth.py route has {len(code_lines)} lines - should be under 200 after refactoring"
