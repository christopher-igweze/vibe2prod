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

# Import using relative path based on project structure
try:
    from services.fix_service import FixService
    from services import fix_service
except ImportError:
    try:
        from fix_service import FixService, fix_service
    except ImportError:
        import sys
        from pathlib import Path
        services_path = Path(__file__).parent.parent / "backend" / "services"
        if services_path.exists():
            sys.path.insert(0, str(services_path.parent))
            from services.fix_service import FixService, fix_service
        else:
            raise ImportError("Could not import fix_service from any known path")


class TestFixServiceImport:
    """Test suite for FixService import and instantiation."""

    def test_fix_service_module_exists(self):
        """Test that fix_service module can be imported."""
        assert fix_service is not None

    def test_fix_service_has_run_forge_fix_method(self):
        """Test that FixService has the run_forge_fix method."""
        assert hasattr(fix_service, 'run_forge_fix')
        assert callable(fix_service.run_forge_fix)


class TestFixServiceRunForgeFix:
    """Test suite for FixService.run_forge_fix method."""

    @pytest.mark.asyncio
    async def test_run_forge_fix_delegates_correctly(self):
        """Test that run_forge_fix properly handles the FORGE remediation flow."""
        fix_attempt_id = uuid4()
        action_item_id = uuid4()
        repo_url = "https://github.com/test/repo"
        scan_findings = [{"id": "test-finding", "severity": "high"}]
        github_token = "test_token"

        # Mock the database operations and forge_bridge
        with patch('services.supabase_client') as mock_db, \
             patch('services.fix_service.trigger_forge_remediate') as mock_trigger, \
             patch('services.fix_service.db', mock_db):
            
            # Setup mock for trigger_forge_remediate
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.pr_url = "https://github.com/test/repo/pull/1"
            mock_result.forge_run_id = "forge-123"
            mock_result.execution_id = "exec-456"
            mock_result.summary = "Fixed 5 findings"
            mock_result.total_findings = 10
            mock_result.findings_fixed = 5
            mock_result.findings_deferred = 2
            mock_result.readiness_score = 85
            mock_result.readiness_report = {}
            mock_result.agent_invocations = 3
            mock_result.cost_usd = 0.15
            mock_result.duration_seconds = 120
            mock_trigger.return_value = mock_result

            # Setup mock for db operations
            mock_db.update_fix_attempt = AsyncMock()
            mock_db.update_action_item_fix_status = AsyncMock()

            # Call the service method
            await fix_service.run_forge_fix(
                fix_attempt_id=fix_attempt_id,
                action_item_id=action_item_id,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

            # Verify the trigger was called with correct arguments
            mock_trigger.assert_called_once_with(
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

            # Verify database was updated on success
            mock_db.update_fix_attempt.assert_called()
            mock_db.update_action_item_fix_status.assert_called_with(
                action_item_id, "fixed"
            )

    @pytest.mark.asyncio
    async def test_run_forge_fix_handles_failure(self):
        """Test that run_forge_fix properly handles FORGE remediation failure."""
        fix_attempt_id = uuid4()
        action_item_id = uuid4()
        repo_url = "https://github.com/test/repo"
        scan_findings = None
        github_token = "test_token"

        with patch('services.supabase_client') as mock_db, \
             patch('services.fix_service.trigger_forge_remediate') as mock_trigger, \
             patch('services.fix_service.db', mock_db):
            
            # Setup mock for failed result
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.pr_url = None
            mock_result.forge_run_id = "forge-123"
            mock_result.execution_id = "exec-456"
            mock_result.error = "Authentication failed"
            mock_result.status = "failed"
            mock_result.summary = "Failed to authenticate"
            mock_result.total_findings = 5
            mock_result.findings_fixed = 0
            mock_result.findings_deferred = 0
            mock_trigger.return_value = mock_result

            mock_db.update_fix_attempt = AsyncMock()
            mock_db.update_action_item_fix_status = AsyncMock()

            await fix_service.run_forge_fix(
                fix_attempt_id=fix_attempt_id,
                action_item_id=action_item_id,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

            # Verify database was updated with failed status
            mock_db.update_fix_attempt.assert_called()
            call_args = mock_db.update_fix_attempt.call_args
            # Check that status is 'failed'
            assert call_args[1].get('status') == 'failed' or call_args[0][1] == 'failed'
            mock_db.update_action_item_fix_status.assert_called_with(
                action_item_id, "open"
            )

    @pytest.mark.asyncio
    async def test_run_forge_fix_handles_exception(self):
        """Test that run_forge_fix properly handles exceptions."""
        fix_attempt_id = uuid4()
        action_item_id = uuid4()
        repo_url = "https://github.com/test/repo"
        scan_findings = None
        github_token = "test_token"

        with patch('services.supabase_client') as mock_db, \
             patch('services.fix_service.trigger_forge_remediate') as mock_trigger, \
             patch('services.fix_service.db', mock_db), \
             patch('logging.getLogger') as mock_logger:
            
            mock_trigger.side_effect = Exception("Forge service unavailable")
            mock_db.update_fix_attempt = AsyncMock()
            mock_db.update_action_item_fix_status = AsyncMock()
            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            await fix_service.run_forge_fix(
                fix_attempt_id=fix_attempt_id,
                action_item_id=action_item_id,
                repo_url=repo_url,
                scan_findings=scan_findings,
                github_token=github_token,
            )

            # Verify exception was logged
            mock_log.exception.assert_called()
            # Verify database was updated to failed on exception
            mock_db.update_fix_attempt.assert_called()
            mock_db.update_action_item_fix_status.assert_called_with(
                action_item_id, "open"
            )


class TestFixRouteDelegation:
    """Test suite verifying fix.py route delegates to FixService."""

    def test_fix_route_imports_fix_service(self):
        """Test that the fix route imports fix_service."""
        # This tests the architectural pattern - that the route uses service
        import sys
        from pathlib import Path
        
        # Try to read the fix.py to verify it imports fix_service
        backend_path = Path(__file__).parent.parent / "backend"
        fix_route_path = backend_path / "api" / "routes" / "fix.py"
        
        if fix_route_path.exists():
            content = fix_route_path.read_text()
            # Verify the route imports the service
            assert "from services.fix_service import fix_service" in content or \
                   "fix_service" in content
        else:
            # If path doesn't exist from test location, check alternative
            fix_route_alt = Path(__file__).parent.parent / "api" / "routes" / "fix.py"
            if fix_route_alt.exists():
                content = fix_route_alt.read_text()
                assert "from services.fix_service import fix_service" in content or \
                       "fix_service" in content
