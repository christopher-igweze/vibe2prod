"""Route-level tests for GitHub OAuth lifecycle."""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure config.Settings can initialize during imports in test environments.
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-client")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GITHUB_OAUTH_STATE_SECRET", "test-state-secret")

from api.routes import github_oauth  # noqa: E402
from services.github_oauth_service import github_oauth_service  # noqa: E402


class GithubOAuthRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app = FastAPI()
        app.state.limiter = github_oauth.limiter

        @app.middleware("http")
        async def _inject_user(request, call_next):
            request.state.user_id = "user_test"
            return await call_next(request)

        app.include_router(github_oauth.router, prefix="/api")
        cls.client = TestClient(app)

        # Patch settings so OAuth checks pass
        cls._settings_patcher = patch("services.github_oauth_service.settings")
        mock_s = cls._settings_patcher.start()
        mock_s.github_client_id = "test-client"
        mock_s.github_client_secret = "test-secret"
        mock_s.github_oauth_state_secret = "test-state-secret"
        mock_s.github_token_encryption_key = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="

    @classmethod
    def tearDownClass(cls) -> None:
        cls._settings_patcher.stop()

    def test_get_auth_url_returns_stateful_redirect(self) -> None:
        resp = self.client.post(
                "/api/github-oauth",
                json={
                    "action": "get_auth_url",
                    "redirect_uri": "http://localhost:5173/settings",
                },
            )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["auth_url"].startswith("https://github.com/login/oauth/authorize?"))
        self.assertIn("state=", payload["auth_url"])

    def test_exchange_code_persists_connection(self) -> None:
        # First get auth URL to obtain a valid state token
        auth_resp = self.client.post(
            "/api/github-oauth",
            json={
                "action": "get_auth_url",
                "redirect_uri": "http://localhost:5173/settings",
            },
        )
        self.assertEqual(auth_resp.status_code, 200)
        state = auth_resp.json()["auth_url"].split("state=", 1)[1]

        # Mock the service methods that the route delegates to
        with patch.object(
            github_oauth_service, "validate_oauth_state", new=AsyncMock()
        ), patch.object(
            github_oauth_service, "exchange_code_for_token",
            new=AsyncMock(return_value="gho_test_token"),
        ), patch.object(
            github_oauth_service, "fetch_github_profile",
            new=AsyncMock(return_value=("octocat", "https://avatars.githubusercontent.com/u/1")),
        ), patch.object(
            github_oauth_service, "connect_user", new=AsyncMock()
        ) as mock_connect:
            resp = self.client.post(
                "/api/github-oauth",
                json={
                    "action": "exchange_code",
                    "code": "abc123",
                    "redirect_uri": "http://localhost:5173/settings",
                    "state": state,
                },
            )

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload["connected"])
        self.assertEqual(payload["github_username"], "octocat")
        mock_connect.assert_awaited_once()

    def test_disconnect_clears_connection(self) -> None:
        with patch.object(
            github_oauth_service, "disconnect_user", new=AsyncMock()
        ) as mock_disconnect:
            resp = self.client.post("/api/github-oauth", json={"action": "disconnect"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["connected"], False)
        mock_disconnect.assert_awaited_once_with(user_id="user_test")


if __name__ == "__main__":
    unittest.main()
