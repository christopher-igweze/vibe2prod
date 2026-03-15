"""Tests for GitHub OAuth service.

These tests verify that the GitHubOAuthService properly handles
OAuth business logic including state management, token exchange,
user disconnection, and replay-attack prevention (CWE-613).

Test Location: tests/test_github_oauth_service.py
Project: backend/services/github_oauth_service.py
Framework: pytest
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import the service class
try:
    from services.github_oauth_service import GitHubOAuthService
except ImportError:
    try:
        from backend.services.github_oauth_service import GitHubOAuthService
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from services.github_oauth_service import GitHubOAuthService
        else:
            raise ImportError("Could not import GitHubOAuthService")


# Required environment variables for settings - must include ALL required fields
BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "GITHUB_CLIENT_ID": "test-client-id",
    "GITHUB_CLIENT_SECRET": "test-client-secret",
    "GITHUB_OAUTH_STATE_SECRET": "test-state-secret",
}


class TestGitHubOAuthServiceExists:
    """Test that the GitHubOAuthService class exists and can be instantiated."""

    def test_service_class_exists(self):
        """Test that GitHubOAuthService class exists."""
        assert GitHubOAuthService is not None

    def test_service_can_be_instantiated(self):
        """Test that service can be instantiated."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            service = GitHubOAuthService()
            assert service is not None


class TestGitHubOAuthServiceDisconnect:
    """Test suite for disconnect_user method."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            return GitHubOAuthService()

    @pytest.fixture
    def mock_db(self):
        """Mock the database client."""
        with patch("services.github_oauth_service.db") as mock:
            mock.clear_github_connection = AsyncMock()
            yield mock

    @pytest.mark.asyncio
    async def test_disconnect_user_calls_db(self, service, mock_db):
        """Test that disconnect_user calls the database clear method."""
        user_id = "test-user-123"
        await service.disconnect_user(user_id=user_id)
        mock_db.clear_github_connection.assert_called_once_with(user_id=user_id)


class TestGitHubOAuthServiceAuthUrl:
    """Test suite for get_auth_url method."""

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            return GitHubOAuthService()

    def test_get_auth_url_returns_valid_url(self, service):
        """Test that get_auth_url returns a valid GitHub OAuth URL."""
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        auth_url = service.get_auth_url(user_id=user_id, redirect_uri=redirect_uri)
        
        assert auth_url is not None
        assert "https://github.com/login/oauth/authorize" in auth_url
        assert "client_id=test-client-id" in auth_url
        assert "scope=" in auth_url
        assert "state=" in auth_url

    def test_get_auth_url_includes_redirect_uri(self, service):
        """Test that get_auth_url includes the redirect_uri in the query string."""
        redirect_uri = "https://example.com/callback"
        
        auth_url = service.get_auth_url(user_id="user-123", redirect_uri=redirect_uri)
        
        # URL-encoded redirect_uri should be in the URL
        assert "redirect_uri=" in auth_url


class TestGitHubOAuthServiceStateValidation:
    """Test suite for validate_oauth_state method.

    validate_oauth_state is async and performs DB checks for replay prevention
    (CWE-613).  All tests in this class must be async and mock the DB layer.
    """

    @pytest.fixture
    def service(self):
        """Create a service instance for testing."""
        with patch.dict("os.environ", BASE_ENV, clear=True):
            return GitHubOAuthService()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _mock_db_not_consumed():
        """Return a patch context for db where no nonce has been consumed yet."""
        return patch(
            "services.github_oauth_service.db",
            **{
                "is_oauth_state_consumed": AsyncMock(return_value=False),
                "consume_oauth_state": AsyncMock(return_value=None),
            },
        )

    @staticmethod
    def _mock_db_already_consumed():
        """Return a patch context for db where the nonce was already consumed."""
        return patch(
            "services.github_oauth_service.db",
            **{
                "is_oauth_state_consumed": AsyncMock(return_value=True),
                "consume_oauth_state": AsyncMock(return_value=None),
            },
        )

    # ------------------------------------------------------------------
    # encode_state public API
    # ------------------------------------------------------------------

    def test_encode_state_public_method_exists(self, service):
        """encode_state is a public method accessible without underscore prefix."""
        assert hasattr(service, "encode_state")
        assert callable(service.encode_state)

    def test_encode_state_returns_string(self, service):
        """encode_state returns a non-empty JWT string."""
        token = service.encode_state(
            user_id="user-1", redirect_uri="https://example.com/cb"
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_encode_state_embeds_jti_nonce(self, service):
        """Each state token must contain a unique jti nonce for one-time-use tracking."""
        import jwt as _jwt

        secret = BASE_ENV["GITHUB_OAUTH_STATE_SECRET"]
        token = service.encode_state(
            user_id="user-1", redirect_uri="https://example.com/cb"
        )
        payload = _jwt.decode(token, secret, algorithms=["HS256"])
        assert "jti" in payload, "state token must contain a jti nonce"
        assert len(payload["jti"]) > 0

    def test_encode_state_jti_is_unique_per_token(self, service):
        """Two calls to encode_state must produce different jti values."""
        import jwt as _jwt

        secret = BASE_ENV["GITHUB_OAUTH_STATE_SECRET"]
        t1 = service.encode_state(user_id="u", redirect_uri="https://a.com/cb")
        t2 = service.encode_state(user_id="u", redirect_uri="https://a.com/cb")
        p1 = _jwt.decode(t1, secret, algorithms=["HS256"])
        p2 = _jwt.decode(t2, secret, algorithms=["HS256"])
        assert p1["jti"] != p2["jti"], "each state token must have a unique jti"

    # ------------------------------------------------------------------
    # validate_oauth_state — happy path
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_validate_oauth_state_success(self, service):
        """validate_oauth_state passes for a fresh, valid state token."""
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)

        with self._mock_db_not_consumed() as mock_db:
            # Should not raise
            await service.validate_oauth_state(
                state=state,
                expected_user_id=user_id,
                expected_redirect_uri=redirect_uri,
            )
            # DB helpers must each be called exactly once
            mock_db.is_oauth_state_consumed.assert_awaited_once()
            mock_db.consume_oauth_state.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_validate_oauth_state_consume_called_with_correct_args(self, service):
        """consume_oauth_state is called with jti, user_id, and ttl_minutes."""
        import jwt as _jwt

        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)
        secret = BASE_ENV["GITHUB_OAUTH_STATE_SECRET"]
        payload = _jwt.decode(state, secret, algorithms=["HS256"])
        expected_jti = payload["jti"]

        with self._mock_db_not_consumed() as mock_db:
            await service.validate_oauth_state(
                state=state,
                expected_user_id=user_id,
                expected_redirect_uri=redirect_uri,
            )
            mock_db.consume_oauth_state.assert_awaited_once_with(
                jti=expected_jti,
                user_id=user_id,
                ttl_minutes=mock_db.consume_oauth_state.call_args.kwargs.get(
                    "ttl_minutes", None
                ),
            )
            # ttl_minutes must be a positive integer
            called_ttl = mock_db.consume_oauth_state.call_args.kwargs["ttl_minutes"]
            assert isinstance(called_ttl, int)
            assert called_ttl > 0

    # ------------------------------------------------------------------
    # validate_oauth_state — field mismatches
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_validate_oauth_state_user_mismatch(self, service):
        """validate_oauth_state raises 403 when the user_id does not match."""
        from fastapi import HTTPException

        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)

        # DB should NOT be reached for a field-mismatch — no nonce burned.
        with self._mock_db_not_consumed() as mock_db:
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id="different-user",
                    expected_redirect_uri=redirect_uri,
                )
            assert exc_info.value.status_code == 403
            assert "oauth_state_user_mismatch" in exc_info.value.detail.get("code", "")
            # Nonce must NOT be consumed on a mismatch
            mock_db.consume_oauth_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_validate_oauth_state_redirect_mismatch(self, service):
        """validate_oauth_state raises 400 when the redirect_uri does not match."""
        from fastapi import HTTPException

        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)

        with self._mock_db_not_consumed() as mock_db:
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri="https://different.com/callback",
                )
            assert exc_info.value.status_code == 400
            assert "oauth_state_redirect_mismatch" in exc_info.value.detail.get("code", "")
            # Nonce must NOT be consumed on a mismatch
            mock_db.consume_oauth_state.assert_not_awaited()

    # ------------------------------------------------------------------
    # validate_oauth_state — replay-attack prevention (CWE-613)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_already_consumed_token(self, service):
        """Replaying a previously consumed state token raises 400 (CWE-613 fix)."""
        from fastapi import HTTPException

        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)

        with self._mock_db_already_consumed() as mock_db:
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail.get("code") == "oauth_state_already_used"
            # Consumption check must have been called
            mock_db.is_oauth_state_consumed.assert_awaited_once()
            # consume must NOT be called — token was already consumed
            mock_db.consume_oauth_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_validate_oauth_state_same_token_cannot_be_used_twice(self, service):
        """Simulate two sequential calls with the same token; second must be rejected."""
        from fastapi import HTTPException

        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)

        # Simulate first call succeeds (not consumed yet)
        consumed_store: set = set()

        async def fake_is_consumed(jti: str) -> bool:
            return jti in consumed_store

        async def fake_consume(*, jti: str, user_id: str, ttl_minutes: int) -> None:
            consumed_store.add(jti)

        with patch(
            "services.github_oauth_service.db",
            **{
                "is_oauth_state_consumed": AsyncMock(side_effect=fake_is_consumed),
                "consume_oauth_state": AsyncMock(side_effect=fake_consume),
            },
        ):
            # First call — must succeed
            await service.validate_oauth_state(
                state=state,
                expected_user_id=user_id,
                expected_redirect_uri=redirect_uri,
            )
            # Second call with same token — must be rejected
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail.get("code") == "oauth_state_already_used"

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_token_without_jti(self, service):
        """State tokens without a jti claim are rejected to enforce forward security."""
        from fastapi import HTTPException
        import jwt as _jwt
        from datetime import datetime, timezone, timedelta

        # Craft a legacy token without a jti claim
        secret = BASE_ENV["GITHUB_OAUTH_STATE_SECRET"]
        now = datetime.now(timezone.utc)
        legacy_payload = {
            "sub": "test-user-123",
            "redirect_uri": "https://example.com/callback",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            # deliberately omitting "jti"
        }
        legacy_token = _jwt.encode(legacy_payload, secret, algorithm="HS256")

        with self._mock_db_not_consumed():
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=legacy_token,
                    expected_user_id="test-user-123",
                    expected_redirect_uri="https://example.com/callback",
                )
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail.get("code") == "oauth_state_missing_nonce"

    @pytest.mark.asyncio
    async def test_validate_oauth_state_db_error_fails_secure(self, service):
        """If the DB check raises, validate_oauth_state propagates the error (fail-secure)."""
        from fastapi import HTTPException

        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        state = service.encode_state(user_id=user_id, redirect_uri=redirect_uri)

        db_exception = HTTPException(
            status_code=503,
            detail={
                "code": "oauth_state_check_failed",
                "message": "Unable to verify OAuth state. Please try again later.",
            },
        )

        with patch(
            "services.github_oauth_service.db",
            **{
                "is_oauth_state_consumed": AsyncMock(side_effect=db_exception),
                "consume_oauth_state": AsyncMock(return_value=None),
            },
        ) as mock_db:
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
            # Must propagate the 503 — never fail-open
            assert exc_info.value.status_code == 503
            mock_db.consume_oauth_state.assert_not_awaited()

    # ------------------------------------------------------------------
    # validate_oauth_state — JWT errors
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_validate_oauth_state_expired_token(self, service):
        """Expired JWT tokens are rejected with 400 oauth_state_expired."""
        from fastapi import HTTPException
        import jwt as _jwt
        from datetime import datetime, timezone, timedelta

        secret = BASE_ENV["GITHUB_OAUTH_STATE_SECRET"]
        now = datetime.now(timezone.utc)
        expired_payload = {
            "sub": "test-user-123",
            "redirect_uri": "https://example.com/callback",
            "jti": "some-nonce",
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),  # already expired
        }
        expired_token = _jwt.encode(expired_payload, secret, algorithm="HS256")

        with self._mock_db_not_consumed():
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=expired_token,
                    expected_user_id="test-user-123",
                    expected_redirect_uri="https://example.com/callback",
                )
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail.get("code") == "oauth_state_expired"

    @pytest.mark.asyncio
    async def test_validate_oauth_state_tampered_token(self, service):
        """Tokens with an invalid signature are rejected with 400 oauth_state_invalid."""
        from fastapi import HTTPException

        tampered = "invalid.jwt.token"

        with self._mock_db_not_consumed():
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=tampered,
                    expected_user_id="test-user-123",
                    expected_redirect_uri="https://example.com/callback",
                )
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail.get("code") == "oauth_state_invalid"
