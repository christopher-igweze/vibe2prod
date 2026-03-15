"""Tests for FixService delegation in fix.py route.

These tests verify that the fix route properly delegates to FixService
for business logic, following Clean Architecture principles.

Test Location: tests/test_fix_service_delegation.py
Project: api/routes/fix.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestFixServiceDelegation:
    """Test suite for FixService delegation in fix.py route."""

    @pytest.mark.asyncio
    async def test_run_forge_fix_delegates_to_service(self):
        """Test that _run_forge_fix delegates to fix_service.run_forge_fix."""
        fix_attempt_id = uuid4()
        action_item_id = uuid4()
        repo_url = "https://github.com/test/repo"
        scan_findings = [{"id": "test-finding", "severity": "high"}]
        github_token = "test_token"

        with patch('api.routes.fix.fix_service') as mock_fix_service:
            # Import and call the route's background task function
            from api.routes.fix import _run_forge_fix
            
            await _run_forge_fix(
                fix_attempt_id=fix_attempt_id,
                action_item_id=action_item_id,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

            # Verify fix_service.run_forge_fix was called with correct arguments
            mock_fix_service.run_forge_fix.assert_called_once_with(
                fix_attempt_id=fix_attempt_id,
                action_item_id=action_item_id,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

    @pytest.mark.asyncio
    async def test_run_scan_forge_fix_delegates_to_service(self):
        """Test that _run_scan_forge_fix delegates to fix_service.run_forge_fix."""
        fix_attempt_id = uuid4()
        scan_id = uuid4()
        repo_url = "https://github.com/test/repo"
        scan_findings = [{"id": "finding-1"}, {"id": "finding-2"}]
        github_token = "test_token"

        with patch('api.routes.fix.fix_service') as mock_fix_service:
            from api.routes.fix import _run_scan_forge_fix
            
            await _run_scan_forge_fix(
                fix_attempt_id=fix_attempt_id,
                scan_id=scan_id,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

            # Verify fix_service.run_forge_fix was called with correct arguments
            mock_fix_service.run_forge_fix.assert_called_once_with(
                fix_attempt_id=fix_attempt_id,
                action_item_id=None,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )


class TestFixRouteThinOrchestration:
    """Test that route handlers are thin and delegate to services."""

    def test_route_imports_fix_service(self):
        """Test that fix.py route imports fix_service module."""
        from api.routes import fix
        
        # Verify fix_service is imported in the route module
        assert hasattr(fix, 'fix_service')
        assert fix.fix_service is not None

    def test_route_no_longer_imports_trigger_forge_remediate(self):
        """Test that fix.py route no longer directly imports forge_bridge."""
        from api.routes import fix
        
        # The route should NOT import trigger_forge_remediate directly
        # (it should be delegated to the service layer)
        # We verify this by checking the route's _run_forge_fix uses delegation
        import inspect
        source = inspect.getsource(fix._run_forge_fix)
        
        # Should contain delegation to fix_service, not trigger_forge_remediate
        assert 'fix_service.run_forge_fix' in source
        assert 'trigger_forge_remediate' not in source
