"""Route-level tests for /api/fix (FORGE integration)."""

from __future__ import annotations

import os
import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")

from api.routes import fix  # noqa: E402


class FixRouteTests(unittest.TestCase):
    """Integration tests for POST /api/fix."""

    @classmethod
    def setUpClass(cls) -> None:
        app = FastAPI()
        app.state.limiter = fix.limiter

        @app.middleware("http")
        async def _inject_user(request, call_next):
            request.state.user_id = "user_test"
            return await call_next(request)

        app.include_router(fix.router, prefix="/api")
        cls.client = TestClient(app)

    def test_forge_disabled_returns_503(self) -> None:
        with patch.object(fix.settings, "forge_enabled", False):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": str(uuid4())},
            )
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["detail"]["code"], "forge_disabled")

    def test_action_item_not_found_returns_404(self) -> None:
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_action_item", new=AsyncMock(return_value=None)):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": str(uuid4())},
            )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["code"], "action_item_not_found")

    def test_fix_already_in_progress_returns_409(self) -> None:
        action_item = {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "scan_report_id": str(uuid4()),
            "fix_status": "in_progress",
        }
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_action_item", new=AsyncMock(return_value=action_item)):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": action_item["id"]},
            )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "fix_already_in_progress")

    def test_project_not_found_returns_404(self) -> None:
        action_item = {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "scan_report_id": str(uuid4()),
            "fix_status": "open",
        }
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_action_item", new=AsyncMock(return_value=action_item)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=None)):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": action_item["id"]},
            )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["code"], "project_not_found")

    def test_successful_fix_request_returns_pending(self) -> None:
        action_item_id = uuid4()
        project_id = uuid4()
        scan_id = uuid4()
        fix_id = uuid4()

        action_item = {
            "id": str(action_item_id),
            "project_id": str(project_id),
            "scan_report_id": str(scan_id),
            "fix_status": "open",
        }
        project = {
            "id": str(project_id),
            "repo_url": "https://github.com/octocat/Hello-World",
        }
        scan_report = {
            "id": str(scan_id),
            "report_data": {"findings": [{"title": "Test finding"}]},
        }

        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_action_item", new=AsyncMock(return_value=action_item)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=project)), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan_report)), \
             patch("api.routes.fix.db.create_fix_attempt", new=AsyncMock(return_value=fix_id)), \
             patch("api.routes.fix._run_forge_fix", new=AsyncMock()):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": str(action_item_id)},
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["fix_attempt_id"], str(fix_id))
        self.assertIn("FORGE", body["message"])

    def test_no_scan_report_still_works(self) -> None:
        action_item_id = uuid4()
        project_id = uuid4()
        scan_id = uuid4()
        fix_id = uuid4()

        action_item = {
            "id": str(action_item_id),
            "project_id": str(project_id),
            "scan_report_id": str(scan_id),
            "fix_status": "open",
        }
        project = {
            "id": str(project_id),
            "repo_url": "https://github.com/octocat/Hello-World",
        }

        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_action_item", new=AsyncMock(return_value=action_item)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=project)), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.create_fix_attempt", new=AsyncMock(return_value=fix_id)), \
             patch("api.routes.fix._run_forge_fix", new=AsyncMock()):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": str(action_item_id)},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "pending")


if __name__ == "__main__":
    unittest.main()
