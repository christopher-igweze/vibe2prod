"""Integration tests for GitHub OAuth service with replay prevention.

These tests verify the complete OAuth flow with replay-attack prevention,
including the interaction between state encoding, validation, and consumption.

Test Location: tests/test_github_oauth_service_replay.py
Finding: F-7d776a56 - OAuth State Parameter Missing Strict Timing Validation
Framework: pytest
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
import jwt

try:
    from backend.services.github_oauth_service import GitHubOAuthService
    from backend.services import supabase_client as db
    from backend.config import settings
except ImportError:
    try:
        from services.github_oauth_service import GitHubOAuthService
        from services import supabase_client as db
        from config import settings
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from services.github_oauth_service import GitHubOAuthService
            from services import supabase_client as db
            from config import settings
        else:
            raise ImportError("Could not import GitHubOAuthService from any known path")

from fastapi import HTTPException


class TestGitHubOAuthServiceReplayPrevention:
    """Integration tests for replay prevention in OAuth flow."""

    def test_get_auth_url_generates_state_with_jti(self):
        """Test that get_auth_url() generates a state token with jti nonce."""
        service = GitHubOAuthService()
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        auth_url = service.get_auth_url(user_id=user_id, redirect_uri=redirect_uri)
        
        # Extract state from URL
        assert "state=" in auth_url
        state_start = auth_url.index("state=") + len("state=")
        state_end = auth_url.index("&", state_start) if "&" in auth_url[state_start:] else len(auth_url)
        state = auth_url[state_start:state_end]
        
        # Verify state contains jti
        payload = jwt.decode(state, options={"verify_signature": False})
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    @pytest.mark.asyncio
    async def test_complete_oauth_flow_with_replay_check(self):
        """Test complete OAuth flow with proper replay-attack prevention."""
        service = GitHubOAuthService()
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        # Step 1: Generate auth URL and extract state
        auth_url = service.get_auth_url(user_id=user_id, redirect_uri=redirect_uri)
        state_start = auth_url.index("state=") + len("state=")
        state_end = auth_url.index("&", state_start) if "&" in auth_url[state_start:] else len(auth_url)
        state = auth_url[state_start:state_end]
        
        # Step 2: First validation should succeed and consume the token
        with patch.object(db, "is_oauth_state_consumed", new_callable=AsyncMock, return_value=False):
            with patch.object(db, "consume_oauth_state", new_callable=AsyncMock) as mock_consume:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
                # Verify consumption was recorded
                assert mock_consume.called
        
        # Step 3: Replay attempt should fail
        with patch.object(db, "is_oauth_state_consumed", new_callable=AsyncMock, return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_validate_oauth_state_passes_ttl_to_database(self):
        """Test that validate_oauth_state() passes correct TTL to database consumption."""
        service = GitHubOAuthService()
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        state = service._encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        with patch.object(db, "is_oauth_state_consumed", new_callable=AsyncMock, return_value=False):
            with patch.object(db, "consume_oauth_state", new_callable=AsyncMock) as mock_consume:
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
                
                # Verify TTL matches settings
                call_kwargs = mock_consume.call_args[1]
                assert call_kwargs["ttl_minutes"] == settings.github_oauth_state_ttl_minutes

    @pytest.mark.asyncio
    async def test_validate_oauth_state_async_signature(self):
        """Test that validate_oauth_state() is properly async."""
        service = GitHubOAuthService()
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        state = service._encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        # The function should be a coroutine function
        import inspect
        assert inspect.iscoroutinefunction(service.validate_oauth_state)
        
        # It should be awaitable
        with patch.object(db, "is_oauth_state_consumed", new_callable=AsyncMock, return_value=False):
            with patch.object(db, "consume_oauth_state", new_callable=AsyncMock):
                coro = service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
                assert inspect.iscoroutine(coro)
                # Clean up the coroutine
                coro.close()

    @pytest.mark.asyncio
    async def test_jwt_expiry_and_consumption_layer_defense(self):
        """Test that both JWT expiry AND consumption check provide defense-in-depth."""
        service = GitHubOAuthService()
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        state = service._encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        # Verify JWT includes expiry
        payload = jwt.decode(state, options={"verify_signature": False})
        assert "exp" in payload
        
        # Verify consumption check is also performed
        call_sequence = []
        
        async def track_consumption(jti):
            call_sequence.append(("is_oauth_state_consumed", jti))
            return False
        
        async def track_consume(jti, user_id, ttl_minutes):
            call_sequence.append(("consume_oauth_state", jti))
        
        with patch.object(db, "is_oauth_state_consumed", new_callable=AsyncMock, side_effect=track_consumption):
            with patch.object(db, "consume_oauth_state", new_callable=AsyncMock, side_effect=track_consume):
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
        
        # Verify both checks were performed
        assert any(call[0] == "is_oauth_state_consumed" for call in call_sequence)
        assert any(call[0] == "consume_oauth_state" for call in call_sequence)

    @pytest.mark.asyncio
    async def test_attacker_cannot_link_different_account_with_old_state(self):
        """Test that an attacker cannot use replayed state to link a different account."""
        service = GitHubOAuthService()
        victim_user_id = "victim-user-123"
        attacker_user_id = "attacker-user-456"
        redirect_uri = "https://example.com/callback"
        
        # Attacker obtains victim's state token (e.g., via phishing)
        state = service._encode_state(user_id=victim_user_id, redirect_uri=redirect_uri)
        
        # Attacker tries to use it with their own user_id
        with pytest.raises(HTTPException) as exc_info:
            await service.validate_oauth_state(
                state=state,
                expected_user_id=attacker_user_id,
                expected_redirect_uri=redirect_uri,
            )
        
        # Validation should fail due to user_id mismatch
        assert exc_info.value.status_code == 403
        assert "does not belong to this user" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_valid_state_with_correct_fields_passes_consumption_check(self):
        """Test that a valid state with all correct fields reaches consumption check."""
        service = GitHubOAuthService()
        user_id = "test-user-123"
        redirect_uri = "https://example.com/callback"
        
        state = service._encode_state(user_id=user_id, redirect_uri=redirect_uri)
        
        consumed_check_called = False
        
        async def track_is_consumed(jti):
            nonlocal consumed_check_called
            consumed_check_called = True
            return False
        
        with patch.object(db, "is_oauth_state_consumed", new_callable=AsyncMock, side_effect=track_is_consumed):
            with patch.object(db, "consume_oauth_state", new_callable=AsyncMock):
                await service.validate_oauth_state(
                    state=state,
                    expected_user_id=user_id,
                    expected_redirect_uri=redirect_uri,
                )
        
        # Verify the consumption check was actually invoked
        assert consumed_check_called
