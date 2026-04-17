"""Tests for GitHub OAuth flow logic — state encoding, validation, redirect checks."""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")
os.environ.setdefault("GITHUB_TOKEN_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
os.environ.setdefault("GITHUB_CLIENT_ID", "test-client")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GITHUB_OAUTH_STATE_SECRET", "test-state-secret-min-length-32chars")
os.environ.setdefault("GITHUB_OAUTH_ALLOWED_REDIRECT_ORIGINS", "https://example.com,http://localhost:3000")

from services.github_oauth_flow import (  # noqa: E402
    encode_state,
    decode_state,
    validate_redirect_uri,
    build_auth_url,
)


class TestEncodeDecodeState(unittest.TestCase):
    """State JWT round-trip and validation."""

    def test_roundtrip(self):
        state = encode_state("user_123", "https://example.com/callback")
        payload = decode_state(state)
        self.assertEqual(payload["sub"], "user_123")
        self.assertEqual(payload["redirect_uri"], "https://example.com/callback")
        self.assertIn("jti", payload)
        self.assertIn("exp", payload)

    def test_decode_invalid_token_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            decode_state("not.a.valid.jwt")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_decode_expired_token_raises(self):
        import jwt as pyjwt
        from datetime import datetime, timezone
        from fastapi import HTTPException

        secret = os.environ["GITHUB_OAUTH_STATE_SECRET"]
        payload = {
            "sub": "user_1",
            "redirect_uri": "https://example.com/cb",
            "jti": "test-nonce",
            "iat": int(datetime(2020, 1, 1, tzinfo=timezone.utc).timestamp()),
            "exp": int(datetime(2020, 1, 2, tzinfo=timezone.utc).timestamp()),
        }
        expired_token = pyjwt.encode(payload, secret, algorithm="HS256")
        with self.assertRaises(HTTPException) as ctx:
            decode_state(expired_token)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("expired", ctx.exception.detail["code"])


class TestValidateRedirectUri(unittest.TestCase):
    """Redirect URI allowlist enforcement."""

    def test_allowed_https_origin_passes(self):
        # Should not raise
        validate_redirect_uri("https://example.com/callback")

    def test_allowed_localhost_http_passes(self):
        validate_redirect_uri("http://localhost:3000/settings")

    def test_disallowed_origin_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            validate_redirect_uri("https://evil.com/callback")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("not_allowed", ctx.exception.detail["code"])

    def test_http_non_localhost_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            validate_redirect_uri("http://example.com/callback")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("scheme", ctx.exception.detail["code"])

    def test_invalid_url_raises(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            validate_redirect_uri("not-a-url")
        self.assertEqual(ctx.exception.status_code, 400)


class TestBuildAuthUrl(unittest.TestCase):
    """Auth URL construction."""

    def test_contains_required_params(self):
        url = build_auth_url("https://example.com/cb", "state-token-123")
        self.assertIn("client_id=test-client", url)
        self.assertIn("state=state-token-123", url)
        self.assertIn("redirect_uri=", url)
        self.assertTrue(url.startswith("https://github.com/login/oauth/authorize?"))


class TestValidateOAuthState(unittest.TestCase):
    """Full state validation including DB consumption."""

    @patch("services.github_oauth_flow.db.consume_oauth_state_atomic", new_callable=AsyncMock, return_value=True)
    def test_valid_state_passes(self, mock_consume):
        import asyncio
        from services.github_oauth_flow import validate_oauth_state

        state = encode_state("user_1", "https://example.com/cb")
        asyncio.get_event_loop().run_until_complete(
            validate_oauth_state(state, "user_1", "https://example.com/cb")
        )
        mock_consume.assert_called_once()

    @patch("services.github_oauth_flow.db.consume_oauth_state_atomic", new_callable=AsyncMock, return_value=False)
    def test_replayed_state_raises(self, mock_consume):
        import asyncio
        from fastapi import HTTPException
        from services.github_oauth_flow import validate_oauth_state

        state = encode_state("user_1", "https://example.com/cb")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.get_event_loop().run_until_complete(
                validate_oauth_state(state, "user_1", "https://example.com/cb")
            )
        self.assertIn("already_used", ctx.exception.detail["code"])

    def test_mismatched_user_raises(self):
        import asyncio
        from fastapi import HTTPException
        from services.github_oauth_flow import validate_oauth_state

        state = encode_state("user_1", "https://example.com/cb")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.get_event_loop().run_until_complete(
                validate_oauth_state(state, "user_WRONG", "https://example.com/cb")
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
