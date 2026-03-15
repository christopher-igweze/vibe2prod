"""Tests for OAuth state replay attack prevention (CWE-613).

These tests verify that the GitHubOAuthService implements one-time-use
enforcement for OAuth state tokens via the jti (JWT ID) nonce mechanism,
preventing replay attacks within the TTL window.

Test Location: tests/test_oauth_state_replay_prevention.py
Finding: F-7d776a56 - OAuth State Parameter Missing Strict Timing Validation
Framework: pytest
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
import secrets
import os

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
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
        else:
            sys.path.insert(0, str(Path(__file__).parent.parent))
        from services.github_oauth_service import GitHubOAuthService
        from config import Settings

try:
    from fastapi import HTTPException
except ImportError:
    HTTPException = Exception


# Base environment variables required for Settings
BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "GITHUB_CLIENT_ID": "test-client-id",
    "GITHUB_CLIENT_SECRET": "test-client-secret",
    "GITHUB_OAUTH_STATE_SECRET": "test-state-secret-key-for-signing",
    "GITHUB_OAUTH_STATE_TTL_MINUTES": "15",
}


class TestOAuthStateReplayPrevention:
    """Test suite for OAuth state one-time-use enforcement."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with required OAuth configuration."""
        settings_dict = BASE_ENV.copy()
        mock_settings = MagicMock()
        mock_settings.github_oauth_state_secret = "test-secret-key-for-signing"
        mock_settings.github_oauth_state_ttl_minutes = 15
        mock_settings.github_client_id = "test-client-id"
        mock_settings.github_client_secret = "test-client-secret"
        return mock_settings

    @pytest.fixture
    def oauth_service(self, mock_settings):
        """Create a GitHubOAuthService instance for testing."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            return service

    def test_encoded_state_includes_jti_nonce(self, mock_settings):
        """Test that _encode_state() includes a unique jti (JWT ID) nonce."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-123', 'http://localhost:3000/callback')
            decoded = jwt.decode(state, 'test-secret-key-for-signing', algorithms=['HS256'])
            
            assert 'jti' in decoded
            assert isinstance(decoded['jti'], str)
            assert len(decoded['jti']) > 0
            assert decoded['sub'] == 'user-123'
            assert decoded['redirect_uri'] == 'http://localhost:3000/callback'

    def test_each_encoded_state_has_unique_jti(self, mock_settings):
        """Test that each call to _encode_state() generates a different jti nonce."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state1 = service._encode_state('user-123', 'http://localhost:3000/callback')
            state2 = service._encode_state('user-123', 'http://localhost:3000/callback')
            
            decoded1 = jwt.decode(state1, 'test-secret-key-for-signing', algorithms=['HS256'])
            decoded2 = jwt.decode(state2, 'test-secret-key-for-signing', algorithms=['HS256'])
            
            assert decoded1['jti'] != decoded2['jti']
            assert decoded1['sub'] == decoded2['sub']
            assert decoded1['redirect_uri'] == decoded2['redirect_uri']

    def test_state_payload_contains_required_fields(self, mock_settings):
        """Test that encoded state contains all required fields for validation."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-456', 'http://example.com/auth')
            decoded = jwt.decode(state, 'test-secret-key-for-signing', algorithms=['HS256'])
            
            assert 'sub' in decoded
            assert 'redirect_uri' in decoded
            assert 'jti' in decoded
            assert 'iat' in decoded
            assert 'exp' in decoded
            assert decoded['sub'] == 'user-456'
            assert decoded['redirect_uri'] == 'http://example.com/auth'

    @pytest.mark.asyncio
    async def test_validate_oauth_state_missing_jti_raises_error(self, mock_settings):
        """Test that validate_oauth_state() rejects tokens without jti nonce."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            # Manually create a token without jti to simulate legacy/compromised tokens
            now = datetime.now(timezone.utc)
            payload = {
                'sub': 'user-123',
                'redirect_uri': 'http://localhost:3000/callback',
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(minutes=15)).timestamp())
            }
            legacy_state = jwt.encode(payload, 'test-secret-key-for-signing', algorithm='HS256')
            
            # Mock the db.is_oauth_state_consumed to return False (not consumed)
            with patch('services.github_oauth_service.db.is_oauth_state_consumed', new_callable=AsyncMock, return_value=False):
                with patch('services.github_oauth_service.db.consume_oauth_state', new_callable=AsyncMock):
                    with pytest.raises(HTTPException) as exc_info:
                        await service.validate_oauth_state(
                            state=legacy_state,
                            expected_user_id='user-123',
                            expected_redirect_uri='http://localhost:3000/callback'
                        )
                    
                    assert exc_info.value.status_code == 400
                    assert 'oauth_state_missing_nonce' in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_oauth_state_checks_consumption_status(self, mock_settings):
        """Test that validate_oauth_state() checks if state token has been consumed."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-123', 'http://localhost:3000/callback')
            
            # Mock db methods: is_oauth_state_consumed returns True (already used)
            with patch('services.github_oauth_service.db.is_oauth_state_consumed', new_callable=AsyncMock, return_value=True):
                with pytest.raises(HTTPException) as exc_info:
                    await service.validate_oauth_state(
                        state=state,
                        expected_user_id='user-123',
                        expected_redirect_uri='http://localhost:3000/callback'
                    )
                
                assert exc_info.value.status_code == 400
                assert 'oauth_state_already_used' in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_oauth_state_marks_token_as_consumed(self, mock_settings):
        """Test that validate_oauth_state() marks the state token as consumed after validation."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-123', 'http://localhost:3000/callback')
            
            # Mock db methods: token not yet consumed
            mock_is_consumed = AsyncMock(return_value=False)
            mock_consume = AsyncMock()
            
            with patch('services.github_oauth_service.db.is_oauth_state_consumed', mock_is_consumed):
                with patch('services.github_oauth_service.db.consume_oauth_state', mock_consume):
                    # Should succeed without raising
                    await service.validate_oauth_state(
                        state=state,
                        expected_user_id='user-123',
                        expected_redirect_uri='http://localhost:3000/callback'
                    )
                    
                    # Verify consume_oauth_state was called
                    mock_consume.assert_called_once()
                    call_kwargs = mock_consume.call_args[1]
                    assert 'jti' in call_kwargs
                    assert call_kwargs['user_id'] == 'user-123'
                    assert call_kwargs['ttl_minutes'] == 15

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_wrong_user_id(self, mock_settings):
        """Test that validate_oauth_state() rejects token with mismatched user_id."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-123', 'http://localhost:3000/callback')
            
            mock_is_consumed = AsyncMock(return_value=False)
            
            with patch('services.github_oauth_service.db.is_oauth_state_consumed', mock_is_consumed):
                with pytest.raises(HTTPException) as exc_info:
                    await service.validate_oauth_state(
                        state=state,
                        expected_user_id='user-456',  # Different user
                        expected_redirect_uri='http://localhost:3000/callback'
                    )
                
                assert exc_info.value.status_code == 403
                assert 'state_does_not_belong_to_user' in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_oauth_state_rejects_wrong_redirect_uri(self, mock_settings):
        """Test that validate_oauth_state() rejects token with mismatched redirect_uri."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-123', 'http://localhost:3000/callback')
            
            mock_is_consumed = AsyncMock(return_value=False)
            
            with patch('services.github_oauth_service.db.is_oauth_state_consumed', mock_is_consumed):
                with pytest.raises(HTTPException) as exc_info:
                    await service.validate_oauth_state(
                        state=state,
                        expected_user_id='user-123',
                        expected_redirect_uri='http://different.com/callback'  # Different URI
                    )
                
                assert exc_info.value.status_code == 400
                assert 'oauth_redirect_uri_mismatch' in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_oauth_state_expired_token_rejected(self, mock_settings):
        """Test that validate_oauth_state() rejects expired state tokens."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            # Create an expired token
            now = datetime.now(timezone.utc)
            payload = {
                'sub': 'user-123',
                'redirect_uri': 'http://localhost:3000/callback',
                'jti': secrets.token_urlsafe(32),
                'iat': int((now - timedelta(minutes=20)).timestamp()),
                'exp': int((now - timedelta(minutes=5)).timestamp())  # Expired 5 minutes ago
            }
            expired_state = jwt.encode(payload, 'test-secret-key-for-signing', algorithm='HS256')
            
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=expired_state,
                    expected_user_id='user-123',
                    expected_redirect_uri='http://localhost:3000/callback'
                )
            
            assert exc_info.value.status_code == 401
            assert 'oauth_state_expired' in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_validate_oauth_state_invalid_signature_rejected(self, mock_settings):
        """Test that validate_oauth_state() rejects tokens with invalid signature."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            # Create a token with wrong secret
            now = datetime.now(timezone.utc)
            payload = {
                'sub': 'user-123',
                'redirect_uri': 'http://localhost:3000/callback',
                'jti': secrets.token_urlsafe(32),
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(minutes=15)).timestamp())
            }
            wrong_sig_state = jwt.encode(payload, 'wrong-secret', algorithm='HS256')
            
            with pytest.raises(HTTPException) as exc_info:
                await service.validate_oauth_state(
                    state=wrong_sig_state,
                    expected_user_id='user-123',
                    expected_redirect_uri='http://localhost:3000/callback'
                )
            
            assert exc_info.value.status_code == 401
            assert 'oauth_state_invalid' in str(exc_info.value.detail)

    def test_state_nonce_is_cryptographically_random(self, mock_settings):
        """Test that jti nonce uses cryptographically random values."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            # Generate multiple states and extract nonces
            nonces = set()
            for _ in range(10):
                state = service._encode_state('user-123', 'http://localhost:3000/callback')
                decoded = jwt.decode(state, 'test-secret-key-for-signing', algorithms=['HS256'])
                nonces.add(decoded['jti'])
            
            # All nonces should be unique
            assert len(nonces) == 10

    @pytest.mark.asyncio
    async def test_replay_attack_prevention_workflow(self, mock_settings):
        """Test the complete replay attack prevention workflow."""
        with patch('services.github_oauth_service.settings', mock_settings):
            service = GitHubOAuthService()
            
            state = service._encode_state('user-123', 'http://localhost:3000/callback')
            decoded = jwt.decode(state, 'test-secret-key-for-signing', algorithms=['HS256'])
            jti = decoded['jti']
            
            # First validation attempt: token not yet consumed
            mock_is_consumed = AsyncMock(side_effect=[False, True])  # First False, then True
            mock_consume = AsyncMock()
            
            with patch('services.github_oauth_service.db.is_oauth_state_consumed', mock_is_consumed):
                with patch('services.github_oauth_service.db.consume_oauth_state', mock_consume):
                    # First call succeeds
                    await service.validate_oauth_state(
                        state=state,
                        expected_user_id='user-123',
                        expected_redirect_uri='http://localhost:3000/callback'
                    )
                    
                    mock_consume.assert_called_once()
                    
                    # Second call with same token should fail (already consumed)
                    with pytest.raises(HTTPException) as exc_info:
                        await service.validate_oauth_state(
                            state=state,
                            expected_user_id='user-123',
                            expected_redirect_uri='http://localhost:3000/callback'
                        )
                    
                    assert exc_info.value.status_code == 400
                    assert 'oauth_state_already_used' in str(exc_info.value.detail)
