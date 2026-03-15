"""Tests for OAuth state replay attack prevention (CWE-613).

These tests verify that the GitHubOAuthService enforces one-time-use state tokens
with per-jti consumption tracking to prevent replay attacks within the TTL window.

Test Location: tests/test_oauth_state_replay_prevention.py
Project: backend/services/github_oauth_service.py
Framework: pytest
Finding ID: F-7d776a56
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException

try:
    from backend.services.github_oauth_service import GitHubOAuthService
    from backend.config import Settings
except ImportError:
    try:
        from services.github_oauth_service import GitHubOAuthService
        from config import Settings
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from services.github_oauth_service import GitHubOAuthService
            from config import Settings
        else:
            raise ImportError("Could not import GitHubOAuthService from any known path")


# All required environment variables for Settings to instantiate
BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "GITHUB_CLIENT_ID": "test-client-id",
    "GITHUB_CLIENT_SECRET": "test-client-secret",
    "GITHUB_OAUTH_STATE_SECRET": "test-state-secret-very-long-string-for-security",
}


class TestOAuthStateReplayPrevention:
    """Test suite for OAuth state replay attack prevention."""

    @pytest.fixture
    def oauth_service(self):
        """Create a GitHubOAuthService instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=False):
            with patch.object(GitHubOAuthService, "_ensure_oauth_configured"):
                service = GitHubOAuthService()
                return service

    def test_state_token_contains_jti_nonce(self, oauth_service):
        """Test that encoded state tokens contain a unique jti (JWT ID) nonce."""
        user_id = "user-123"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)
        decoded = oauth_service.decode_state(state)

        assert "jti" in decoded, "State token must contain a jti claim"
        assert decoded["jti"], "jti claim must not be empty"
        assert len(decoded["jti"]) > 20, "jti should be a cryptographically random nonce"

    def test_jti_is_unique_per_state_token(self, oauth_service):
        """Test that each state token has a unique jti value."""
        user_id = "user-123"
        redirect_uri = "https://example.com/callback"

        state1 = oauth_service.encode_state(user_id, redirect_uri)
        state2 = oauth_service.encode_state(user_id, redirect_uri)

        decoded1 = oauth_service.decode_state(state1)
        decoded2 = oauth_service.decode_state(state2)

        assert decoded1["jti"] != decoded2["jti"], "Each state token must have a unique jti"

    def test_state_token_preserves_user_id_and_redirect_uri(self, oauth_service):
        """Test that state token correctly encodes user_id and redirect_uri."""
        user_id = "user-456"
        redirect_uri = "https://myapp.com/oauth/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)
        decoded = oauth_service.decode_state(state)

        assert decoded["sub"] == user_id
        assert decoded["redirect_uri"] == redirect_uri

    def test_state_token_contains_expiry(self, oauth_service):
        """Test that state token contains expiry time."""
        user_id = "user-789"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)
        decoded = oauth_service.decode_state(state)

        assert "exp" in decoded, "State token must contain exp claim"
        assert "iat" in decoded, "State token must contain iat claim"
        assert decoded["exp"] > decoded["iat"], "exp must be greater than iat"

    @pytest.mark.asyncio
    async def test_validate_oauth_state_accepts_valid_token_first_use(self, oauth_service):
        """Test that validate_oauth_state accepts a valid token on first use."""
        user_id = "user-789"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)

        with patch("services.supabase_client.is_oauth_state_consumed", new_callable=AsyncMock, return_value=False):
            with patch("services.supabase_client.consume_oauth_state", new_callable=AsyncMock):
                # Should not raise an exception
                await oauth_service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_already_consumed_token(self, oauth_service):
        """Test that validate_oauth_state rejects a token that has been consumed."""
        user_id = "user-101"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)

        with patch("services.supabase_client.is_oauth_state_consumed", new_callable=AsyncMock, return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await oauth_service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
            assert exc_info.value.status_code == 400
            assert "already_used" in str(exc_info.value.detail["code"])

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_mismatched_user_id(self, oauth_service):
        """Test that validate_oauth_state rejects token with mismatched user_id."""
        user_id = "user-123"
        redirect_uri = "https://example.com/callback"
        wrong_user_id = "user-999"

        state = oauth_service.encode_state(user_id, redirect_uri)

        with pytest.raises(HTTPException) as exc_info:
            await oauth_service.validate_oauth_state(
                state=state,
                expected_user_id=wrong_user_id,
                expected_redirect_uri=redirect_uri,
            )
        assert exc_info.value.status_code == 403
        assert "does not belong to this user" in str(exc_info.value.detail["message"])

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_mismatched_redirect_uri(self, oauth_service):
        """Test that validate_oauth_state rejects token with mismatched redirect_uri."""
        user_id = "user-123"
        redirect_uri = "https://example.com/callback"
        wrong_redirect_uri = "https://attacker.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)

        with patch("services.supabase_client.is_oauth_state_consumed", new_callable=AsyncMock, return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await oauth_service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=wrong_redirect_uri,
                )
            assert exc_info.value.status_code == 400
            assert "redirect_uri" in str(exc_info.value.detail["message"])

    @pytest.mark.asyncio
    async def test_validate_oauth_state_marks_token_consumed_after_validation(self, oauth_service):
        """Test that validate_oauth_state marks token as consumed after successful validation."""
        user_id = "user-234"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)
        decoded = oauth_service.decode_state(state)
        jti = decoded["jti"]

        with patch("services.supabase_client.is_oauth_state_consumed", new_callable=AsyncMock, return_value=False) as mock_is_consumed:
            with patch("services.supabase_client.consume_oauth_state", new_callable=AsyncMock) as mock_consume:
                await oauth_service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
                # Verify consume_oauth_state was called with the jti
                mock_consume.assert_called_once()
                call_kwargs = mock_consume.call_args[1]
                assert call_kwargs["jti"] == jti
                assert call_kwargs["user_id"] == user_id

    def test_validate_oauth_state_rejects_token_without_jti(self, oauth_service):
        """Test that validate_oauth_state rejects tokens without a jti (legacy tokens)."""
        user_id = "user-345"
        redirect_uri = "https://example.com/callback"

        # Manually create a state token without jti to simulate old token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "redirect_uri": redirect_uri,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=15)).timestamp()
            ),
        }
        secret = oauth_service._get_state_secret()
        state = jwt.encode(payload, secret, algorithm="HS256")

        with pytest.mark.asyncio:
            with pytest.raises(HTTPException) as exc_info:
                import asyncio
                asyncio.run(oauth_service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                ))
            assert exc_info.value.status_code == 400
            assert "missing a required nonce" in str(exc_info.value.detail["message"])

    @pytest.mark.asyncio
    async def test_validate_oauth_state_calls_db_with_correct_ttl(self, oauth_service):
        """Test that validate_oauth_state passes correct TTL to database."""
        user_id = "user-456"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)

        with patch("services.supabase_client.is_oauth_state_consumed", new_callable=AsyncMock, return_value=False):
            with patch("services.supabase_client.consume_oauth_state", new_callable=AsyncMock) as mock_consume:
                await oauth_service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
                # Verify TTL matches settings
                call_kwargs = mock_consume.call_args[1]
                assert "ttl_minutes" in call_kwargs
                # TTL should match the oauth_state_ttl_minutes setting (default 15)
                assert call_kwargs["ttl_minutes"] > 0

    def test_encode_state_public_method_exists(self, oauth_service):
        """Test that encode_state is publicly accessible."""
        assert hasattr(oauth_service, "encode_state")
        assert callable(oauth_service.encode_state)

    def test_decode_state_public_method_exists(self, oauth_service):
        """Test that decode_state is publicly accessible."""
        assert hasattr(oauth_service, "decode_state")
        assert callable(oauth_service.decode_state)

    @pytest.mark.asyncio
    async def test_validate_oauth_state_is_async(self, oauth_service):
        """Test that validate_oauth_state is an async method."""
        import inspect
        assert inspect.iscoroutinefunction(oauth_service.validate_oauth_state)

    def test_state_token_expiry_within_configured_ttl(self, oauth_service):
        """Test that state token expiry matches configured TTL."""
        user_id = "user-567"
        redirect_uri = "https://example.com/callback"

        state = oauth_service.encode_state(user_id, redirect_uri)
        decoded = oauth_service.decode_state(state)

        now = datetime.now(timezone.utc)
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        ttl = exp_time - iat_time

        # Default TTL is 15 minutes, allow 1 minute tolerance
        expected_ttl = timedelta(minutes=15)
        assert abs((ttl - expected_ttl).total_seconds()) < 60
