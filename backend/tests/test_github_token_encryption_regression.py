"""Tests for GitHub token encryption functionality.

These tests verify that GitHub OAuth access tokens are properly encrypted
before storage and decrypted on retrieval, preventing plaintext storage
in the database (CWE-312, OWASP A02:2021).

Test Location: tests/test_github_token_encryption_regression.py
Project: backend/services/supabase_client.py
Framework: pytest
"""

import pytest
import base64
import secrets
from unittest.mock import patch, MagicMock, AsyncMock

try:
    from backend.config import Settings
except ImportError:
    try:
        from config import Settings
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from config import Settings
        else:
            raise ImportError("Could not import Settings from any known path")


BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "GITHUB_TOKEN_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
}


class TestGitHubTokenEncryptionSettings:
    """Test suite for GitHub token encryption settings configuration."""

    def test_github_token_encryption_key_required(self):
        """Test that github_token_encryption_key is a required field."""
        env = BASE_ENV.copy()
        del env["GITHUB_TOKEN_ENCRYPTION_KEY"]
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            error_str = str(exc_info.value)
            assert "github_token_encryption_key" in error_str.lower()

    def test_github_token_encryption_key_base64_valid(self):
        """Test that a valid base64-encoded 32-byte key is accepted."""
        valid_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = valid_key
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.github_token_encryption_key == valid_key

    def test_github_token_encryption_key_description_present(self):
        """Test that the field has proper description for documentation."""
        # Verify the field is defined with description
        field_info = Settings.model_fields.get("github_token_encryption_key")
        assert field_info is not None
        assert field_info.description is not None
        assert "encrypt" in field_info.description.lower()
        assert "GitHub" in field_info.description


class TestGetGitHubAccessTokenDecryption:
    """Test suite for decryption of GitHub access tokens on retrieval."""

    @pytest.fixture
    def valid_encryption_key(self):
        """Generate a valid 32-byte AES-256 key in URL-safe base64 format."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    @pytest.fixture
    def sample_token(self):
        """A sample GitHub OAuth access token."""
        return "ghu_16C7e42F292c6912E7710c838347Ae178B4a"

    def test_get_github_access_token_calls_decrypt(self, valid_encryption_key, sample_token):
        """Test that get_github_access_token decrypts the stored token."""
        from services.token_encryption import encrypt_token
        import asyncio

        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = valid_encryption_key
        
        encrypted = encrypt_token(sample_token, valid_encryption_key)
        
        with patch.dict("os.environ", env, clear=False):
            from services import supabase_client
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"github_access_token": encrypted}]
            mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                result = asyncio.run(supabase_client.get_github_access_token("test-user"))
                assert result == sample_token

    def test_get_github_access_token_returns_none_if_no_token(self):
        """Test that get_github_access_token returns None if no token stored."""
        import asyncio
        from services import supabase_client
        
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                result = asyncio.run(supabase_client.get_github_access_token("test-user"))
                assert result is None

    def test_get_github_access_token_returns_none_if_raw_is_empty(self):
        """Test that get_github_access_token returns None if stored value is empty/null."""
        import asyncio
        from services import supabase_client
        
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"github_access_token": None}]
            mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                result = asyncio.run(supabase_client.get_github_access_token("test-user"))
                assert result is None

    def test_get_github_access_token_handles_invalid_tag_exception(self, valid_encryption_key):
        """Test that get_github_access_token returns None on InvalidTag (wrong key or tampered data)."""
        import asyncio
        from services import supabase_client
        from cryptography.exceptions import InvalidTag
        
        env = BASE_ENV.copy()
        # Use different key for storage vs retrieval
        other_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = other_key
        
        with patch.dict("os.environ", env, clear=False):
            mock_client = MagicMock()
            mock_response = MagicMock()
            # Return some encrypted data (from different key)
            mock_response.data = [{"github_access_token": b"tampered_or_wrong_key_encrypted"}]
            mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                # Patch decrypt_token to raise InvalidTag
                with patch("services.supabase_client.decrypt_token", side_effect=InvalidTag()):
                    result = asyncio.run(supabase_client.get_github_access_token("test-user"))
                    assert result is None

    def test_get_github_access_token_handles_value_error(self):
        """Test that get_github_access_token returns None on ValueError (malformed ciphertext)."""
        import asyncio
        from services import supabase_client
        
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [{"github_access_token": b"malformed_data"}]
            mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                with patch("services.supabase_client.decrypt_token", side_effect=ValueError("Invalid padding")):
                    result = asyncio.run(supabase_client.get_github_access_token("test-user"))
                    assert result is None


class TestSaveGitHubConnectionEncryption:
    """Test suite for encryption of GitHub access tokens on save."""

    @pytest.fixture
    def valid_encryption_key(self):
        """Generate a valid 32-byte AES-256 key in URL-safe base64 format."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    @pytest.fixture
    def sample_token(self):
        """A sample GitHub OAuth access token."""
        return "ghu_16C7e42F292c6912E7710c838347Ae178B4a"

    def test_save_github_connection_encrypts_token(self, valid_encryption_key, sample_token):
        """Test that save_github_connection encrypts the access token before storing."""
        import asyncio
        from services import supabase_client
        from services.token_encryption import encrypt_token
        
        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = valid_encryption_key
        
        with patch.dict("os.environ", env, clear=False):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                asyncio.run(supabase_client.save_github_connection(
                    user_id="test-user",
                    access_token=sample_token,
                    github_username="testuser",
                    avatar_url="https://example.com/avatar.png"
                ))
                
                # Verify that update was called with encrypted token
                call_args = mock_client.table.return_value.update.call_args
                assert call_args is not None
                update_data = call_args[0][0]
                
                # The stored token should not be plaintext
                assert update_data["github_access_token"] != sample_token
                # It should be bytes (encrypted)
                assert isinstance(update_data["github_access_token"], bytes)
                # Other fields should be plaintext (not encrypted)
                assert update_data["github_username"] == "testuser"
                assert update_data["avatar_url"] == "https://example.com/avatar.png"

    def test_save_github_connection_plaintext_never_in_db(self, valid_encryption_key, sample_token):
        """Test that plaintext token is never passed to the database layer."""
        import asyncio
        from services import supabase_client
        
        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = valid_encryption_key
        
        with patch.dict("os.environ", env, clear=False):
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = []
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response
            
            with patch("services.supabase_client._client", return_value=mock_client):
                asyncio.run(supabase_client.save_github_connection(
                    user_id="test-user",
                    access_token=sample_token,
                    github_username="testuser",
                    avatar_url="https://example.com/avatar.png"
                ))
                
                # Verify plaintext token is not in any call arguments
                for call in mock_client.table.return_value.update.call_args_list:
                    args, kwargs = call
                    if args:
                        data = args[0]
                        assert sample_token not in str(data)
                        # Ensure it's not in the token field specifically
                        if "github_access_token" in data:
                            assert data["github_access_token"] != sample_token


class TestTokenEncryptionRoundTrip:
    """Test suite for end-to-end encryption/decryption roundtrip."""

    @pytest.fixture
    def valid_encryption_key(self):
        """Generate a valid 32-byte AES-256 key in URL-safe base64 format."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    @pytest.fixture
    def sample_token(self):
        """A sample GitHub OAuth access token."""
        return "ghu_16C7e42F292c6912E7710c838347Ae178B4a"

    def test_encryption_decryption_roundtrip(self, valid_encryption_key, sample_token):
        """Test that token encrypted and then decrypted recovers original plaintext."""
        from services.token_encryption import encrypt_token, decrypt_token
        
        encrypted = encrypt_token(sample_token, valid_encryption_key)
        decrypted = decrypt_token(encrypted, valid_encryption_key)
        
        assert decrypted == sample_token

    def test_encryption_produces_bytes(self, valid_encryption_key, sample_token):
        """Test that encrypt_token returns bytes (ciphertext), not string."""
        from services.token_encryption import encrypt_token
        
        encrypted = encrypt_token(sample_token, valid_encryption_key)
        
        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_encryption_ciphertext_differs_each_time(self, valid_encryption_key, sample_token):
        """Test that encrypting the same token twice produces different ciphertexts (due to IV/nonce)."""
        from services.token_encryption import encrypt_token
        
        encrypted1 = encrypt_token(sample_token, valid_encryption_key)
        encrypted2 = encrypt_token(sample_token, valid_encryption_key)
        
        # Different due to random IV in AES-GCM
        assert encrypted1 != encrypted2

    def test_decryption_with_wrong_key_fails(self, sample_token):
        """Test that decrypting with wrong key raises InvalidTag or ValueError."""
        from services.token_encryption import encrypt_token, decrypt_token
        from cryptography.exceptions import InvalidTag
        
        key1 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        key2 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        encrypted = encrypt_token(sample_token, key1)
        
        with pytest.raises((InvalidTag, ValueError)):
            decrypt_token(encrypted, key2)

    def test_decryption_of_tampered_ciphertext_fails(self, valid_encryption_key, sample_token):
        """Test that decrypting tampered ciphertext raises InvalidTag or ValueError."""
        from services.token_encryption import encrypt_token, decrypt_token
        from cryptography.exceptions import InvalidTag
        
        encrypted = encrypt_token(sample_token, valid_encryption_key)
        
        # Tamper with the ciphertext
        tampered = bytes([b ^ 0xFF for b in encrypted[:10]]) + encrypted[10:]
        
        with pytest.raises((InvalidTag, ValueError)):
            decrypt_token(tampered, valid_encryption_key)

    def test_encryption_different_tokens_produce_different_ciphertexts(self, valid_encryption_key):
        """Test that different tokens produce different ciphertexts."""
        from services.token_encryption import encrypt_token
        
        token1 = "ghu_16C7e42F292c6912E7710c838347Ae178B4a"
        token2 = "ghu_26C7e42F292c6912E7710c838347Ae178B4b"
        
        encrypted1 = encrypt_token(token1, valid_encryption_key)
        encrypted2 = encrypt_token(token2, valid_encryption_key)
        
        # Even though they're similar, they should produce different ciphertexts
        # (If they somehow produce the same, decryption should produce different results)
        assert encrypted1 != encrypted2
