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
            "user_id": "user_test",
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
             patch("api.routes.fix.db.get_github_access_token", new=AsyncMock(return_value=None)), \
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
            "user_id": "user_test",
            "repo_url": "https://github.com/octocat/Hello-World",
        }

        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_action_item", new=AsyncMock(return_value=action_item)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=project)), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.get_github_access_token", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.create_fix_attempt", new=AsyncMock(return_value=fix_id)), \
             patch("api.routes.fix._run_forge_fix", new=AsyncMock()):
            resp = self.client.post(
                "/api/fix",
                json={"action_item_id": str(action_item_id)},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "pending")


class ScanFixRouteTests(unittest.TestCase):
    """Integration tests for POST /api/fix-scan/{scan_id} and GET /api/fix-scan/{scan_id}/status."""

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

    # -- POST /api/fix-scan/{scan_id} --

    def test_scan_fix_forge_disabled_returns_503(self) -> None:
        scan_id = uuid4()
        with patch.object(fix.settings, "forge_enabled", False):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["detail"]["code"], "forge_disabled")

    def test_scan_fix_scan_not_found_returns_404(self) -> None:
        scan_id = uuid4()
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=None)):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["code"], "scan_not_found")

    def test_scan_fix_not_completed_returns_400(self) -> None:
        scan_id = uuid4()
        scan = {"id": str(scan_id), "status": "scanning", "project_id": str(uuid4())}
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"]["code"], "scan_not_completed")

    def test_scan_fix_already_in_progress_returns_409(self) -> None:
        scan_id = uuid4()
        project_id = uuid4()
        scan = {"id": str(scan_id), "status": "completed", "project_id": str(project_id)}
        active_attempt = {"id": str(uuid4()), "status": "running"}
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_active_scan_fix_attempt", new=AsyncMock(return_value=active_attempt)):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "fix_already_in_progress")

    def test_scan_fix_project_not_found_returns_404(self) -> None:
        scan_id = uuid4()
        project_id = uuid4()
        scan = {"id": str(scan_id), "status": "completed", "project_id": str(project_id)}
        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_active_scan_fix_attempt", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=None)):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["code"], "project_not_found")

    def test_scan_fix_success_returns_pending(self) -> None:
        scan_id = uuid4()
        project_id = uuid4()
        fix_id = uuid4()
        scan = {
            "id": str(scan_id),
            "status": "completed",
            "project_id": str(project_id),
            "report_data": {"findings": [{"title": "Missing auth"}]},
        }
        project = {
            "id": str(project_id),
            "user_id": "user_test",
            "repo_url": "https://github.com/octocat/Hello-World",
        }

        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_active_scan_fix_attempt", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=project)), \
             patch("api.routes.fix.db.get_github_access_token", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.create_scan_fix_attempt", new=AsyncMock(return_value=fix_id)), \
             patch("api.routes.fix._run_scan_forge_fix", new=AsyncMock()):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["fix_attempt_id"], str(fix_id))
        self.assertEqual(body["message"], "Remediation started")

    def test_scan_fix_extracts_discovery_report_findings(self) -> None:
        """Findings nested under discovery_report should also be extracted."""
        scan_id = uuid4()
        project_id = uuid4()
        fix_id = uuid4()
        scan = {
            "id": str(scan_id),
            "status": "completed",
            "project_id": str(project_id),
            "report_data": {"discovery_report": {"findings": [{"title": "Nested"}]}},
        }
        project = {
            "id": str(project_id),
            "user_id": "user_test",
            "repo_url": "https://github.com/octocat/Hello-World",
        }

        with patch.object(fix.settings, "forge_enabled", True), \
             patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_active_scan_fix_attempt", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.get_project", new=AsyncMock(return_value=project)), \
             patch("api.routes.fix.db.get_github_access_token", new=AsyncMock(return_value=None)), \
             patch("api.routes.fix.db.create_scan_fix_attempt", new=AsyncMock(return_value=fix_id)), \
             patch("api.routes.fix._run_scan_forge_fix", new=AsyncMock()):
            resp = self.client.post(f"/api/fix-scan/{scan_id}")

        self.assertEqual(resp.status_code, 200)

    # -- GET /api/fix-scan/{scan_id}/status --

    def test_scan_fix_status_scan_not_found_returns_404(self) -> None:
        scan_id = uuid4()
        with patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=None)):
            resp = self.client.get(f"/api/fix-scan/{scan_id}/status")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["code"], "scan_not_found")

    def test_scan_fix_status_no_attempt_returns_404(self) -> None:
        scan_id = uuid4()
        scan = {"id": str(scan_id), "status": "completed", "project_id": str(uuid4())}
        with patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_latest_scan_fix_attempt", new=AsyncMock(return_value=None)):
            resp = self.client.get(f"/api/fix-scan/{scan_id}/status")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"]["code"], "no_fix_attempt")

    def test_scan_fix_status_returns_attempt_data(self) -> None:
        scan_id = uuid4()
        fix_id = uuid4()
        scan = {"id": str(scan_id), "status": "completed", "project_id": str(uuid4())}
        attempt = {
            "id": str(fix_id),
            "status": "success",
            "pr_url": "https://github.com/octocat/Hello-World/pull/42",
            "started_at": "2026-03-01T10:00:00+00:00",
            "completed_at": "2026-03-01T10:05:00+00:00",
            "agent_logs": {
                "findings_fixed": 5,
                "findings_deferred": 2,
                "readiness_score": 85,
                "summary": "Fixed 5 of 7 findings",
                "readiness_report": {"overall_score": 85, "category_scores": []},
                "agent_invocations": 42,
                "cost_usd": 1.23,
                "duration_seconds": 280.5,
            },
        }
        with patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_latest_scan_fix_attempt", new=AsyncMock(return_value=attempt)):
            resp = self.client.get(f"/api/fix-scan/{scan_id}/status")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["fix_attempt_id"], str(fix_id))
        self.assertEqual(body["scan_id"], str(scan_id))
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["findings_fixed"], 5)
        self.assertEqual(body["findings_deferred"], 2)
        self.assertEqual(body["readiness_score"], 85)
        self.assertEqual(body["pr_url"], "https://github.com/octocat/Hello-World/pull/42")
        self.assertEqual(body["summary"], "Fixed 5 of 7 findings")
        self.assertEqual(body["duration_seconds"], 280.5)
        self.assertEqual(body["readiness_report"], {"overall_score": 85, "category_scores": []})
        self.assertEqual(body["agent_invocations"], 42)
        self.assertEqual(body["cost_usd"], 1.23)
        self.assertIsNone(body["error"])

    def test_scan_fix_status_failed_returns_error(self) -> None:
        scan_id = uuid4()
        fix_id = uuid4()
        scan = {"id": str(scan_id), "status": "completed", "project_id": str(uuid4())}
        attempt = {
            "id": str(fix_id),
            "status": "failed",
            "pr_url": None,
            "started_at": "2026-03-01T10:00:00+00:00",
            "completed_at": "2026-03-01T10:02:00+00:00",
            "agent_logs": {
                "error": "FORGE remediation timed out",
                "status": "failed",
                "summary": "Remediation failed after 2 retries",
                "total_findings": 7,
                "findings_fixed": 0,
                "findings_deferred": 0,
            },
        }
        with patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_latest_scan_fix_attempt", new=AsyncMock(return_value=attempt)):
            resp = self.client.get(f"/api/fix-scan/{scan_id}/status")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["error"], "FORGE remediation timed out")
        self.assertEqual(body["summary"], "Remediation failed after 2 retries")
        self.assertEqual(body["findings_fixed"], 0)
        self.assertIsNone(body["readiness_report"])
        self.assertIsNone(body["agent_invocations"])

    def test_scan_fix_status_running_no_duration(self) -> None:
        scan_id = uuid4()
        fix_id = uuid4()
        scan = {"id": str(scan_id), "status": "completed", "project_id": str(uuid4())}
        attempt = {
            "id": str(fix_id),
            "status": "running",
            "pr_url": None,
            "started_at": "2026-03-01T10:00:00+00:00",
            "completed_at": None,
            "agent_logs": None,
        }
        with patch("api.routes.fix.db.get_scan_report", new=AsyncMock(return_value=scan)), \
             patch("api.routes.fix.db.get_latest_scan_fix_attempt", new=AsyncMock(return_value=attempt)):
            resp = self.client.get(f"/api/fix-scan/{scan_id}/status")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "running")
        self.assertIsNone(body["duration_seconds"])
        self.assertIsNone(body["findings_fixed"])


if __name__ == "__main__":
    unittest.main()
