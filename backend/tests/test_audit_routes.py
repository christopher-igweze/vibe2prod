"""Route-level tests for FORGE audit API behavior."""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure config.Settings can initialize during imports in test environments.
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")

# Avoid importing the deep orchestrator dependency tree (requires openhands).
if "agents.orchestrator" not in sys.modules:
    import types

    fake_orchestrator = types.ModuleType("agents.orchestrator")

    class _FakeAuditOrchestrator:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def run(self):
            raise RuntimeError("deep orchestrator should not be used in route tests")

    fake_orchestrator.AuditOrchestrator = _FakeAuditOrchestrator
    sys.modules["agents.orchestrator"] = fake_orchestrator

from api.routes import audit  # noqa: E402


class AuditRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app = FastAPI()
        app.state.limiter = audit.limiter

        @app.middleware("http")
        async def _inject_user(request, call_next):
            request.state.user_id = "user_test"
            return await call_next(request)

        app.include_router(audit.router, prefix="/api")
        cls.client = TestClient(app)

    @staticmethod
    def _payload() -> dict:
        return {
            "repo_url": "https://github.com/octocat/Hello-World",
            "project_intake": {
                "project_origin": "external",
                "product_summary": "Small demo application.",
                "target_users": "Developers",
                "sensitive_data": ["none"],
                "must_not_break_flows": ["Landing page load"],
                "deployment_target": "Vercel",
                "scale_expectation": "MVP / low traffic",
            },
        }

    def test_onboarding_incomplete_blocks_audit(self) -> None:
        with patch(
            "api.routes.audit.db.get_user_role", return_value="developer"
        ), patch(
            "api.routes.audit.db.get_github_access_token", new=AsyncMock(return_value=None)
        ), patch(
            "api.routes.audit.openrouter_key_manager.get_decrypted_key", new=AsyncMock(return_value=None)
        ), patch("api.routes.audit.db.is_onboarding_complete", new=AsyncMock(return_value=False)):
            resp = self.client.post("/api/audit", json=self._payload())

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"]["code"], "onboarding_required")

    def test_start_audit_dispatches_forge_scan(self) -> None:
        project_id = uuid4()
        repo_info = SimpleNamespace(
            full_name="octocat/Hello-World",
            default_branch="master",
            clone_url="https://github.com/octocat/Hello-World.git",
        )
        existing_project = {"id": str(project_id)}

        with patch(
            "api.routes.audit.db.get_user_role", return_value="developer"
        ), patch(
            "api.routes.audit._run_forge_audit", new=AsyncMock()
        ) as mock_forge, patch(
            "api.routes.audit.db.get_github_access_token", new=AsyncMock(return_value=None)
        ), patch(
            "api.routes.audit.openrouter_key_manager.get_decrypted_key", new=AsyncMock(return_value=None)
        ), patch("api.routes.audit.db.is_onboarding_complete", new=AsyncMock(return_value=True)), patch(
            "api.routes.audit.db.get_project_by_repo_url", new=AsyncMock(return_value=existing_project)
        ), patch(
            "api.routes.audit.parse_repo_url", new=AsyncMock(return_value=("octocat", "Hello-World"))
        ), patch("api.routes.audit.get_repo_info", new=AsyncMock(return_value=repo_info)), patch(
            "api.routes.audit.db.create_scan_report", new=AsyncMock(return_value=uuid4())
        ):
            resp = self.client.post("/api/audit", json=self._payload())

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["tier"], "forge")
        self.assertIn("scan_id", body)




if __name__ == "__main__":
    unittest.main()
