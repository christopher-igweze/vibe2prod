"""Tests for GitHub OAuth token encryption.

These tests verify that GitHub access tokens are properly encrypted
before storage and decrypted on retrieval, addressing CWE-312.

Test Location: tests/test_github_token_encryption.py
Framework: pytest
"""

import pytest
import base64
import secrets
from unittest.mock import patch, MagicMock, AsyncMock

try:
    from backend.services.token_encryption import encrypt_token, decrypt_token
except ImportError:
    try:
        from services.token_encryption import encrypt_token, decrypt_token
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from services.token_encryption import encrypt_token, decrypt_token
        else:
            raise ImportError("Could not import token_encryption from any known path")

try:
    from backend.config import Settings
except ImportError:
    try:
        from config import Settings
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
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


class TestTokenEncryption:
    """Test suite for GitHub token encryption and decryption."""

    def setup_method(self):
        """Generate a valid AES-256 encryption key for tests."""
        key_bytes = secrets.token_bytes(32)
        self.valid_key = base64.urlsafe_b64encode(key_bytes).decode()
        self.test_token = "ghu_test1234567890abcdefghijklmnopqrst"

    def test_encrypt_token_produces_ciphertext(self):
        """Test that encrypt_token returns non-empty ciphertext."""
        ciphertext = encrypt_token(self.test_token, self.valid_key)
        assert ciphertext is not None
        assert len(ciphertext) > 0
        assert ciphertext != self.test_token

    def test_decrypt_token_recovers_plaintext(self):
        """Test that decrypt_token recovers the original plaintext token."""
        ciphertext = encrypt_token(self.test_token, self.valid_key)
        decrypted = decrypt_token(ciphertext, self.valid_key)
        assert decrypted == self.test_token

    def test_encrypt_decrypt_roundtrip(self):
        """Test full encrypt-decrypt roundtrip for various tokens."""
        tokens = [
            "ghu_1234567890abcdefghijklmnop",
            "ghu_verylongtokenwithmanycharacters1234567890",
            "ghu_x",
        ]
        for token in tokens:
            encrypted = encrypt_token(token, self.valid_key)
            decrypted = decrypt_token(encrypted, self.valid_key)
            assert decrypted == token

    def test_decrypt_invalid_ciphertext_raises_error(self):
        """Test that decrypt_token raises error on tampered ciphertext."""
        from cryptography.exceptions import InvalidTag
        ciphertext = encrypt_token(self.test_token, self.valid_key)
        tampered = ciphertext[:-4] + "xxxx"
        with pytest.raises((InvalidTag, ValueError)):
            decrypt_token(tampered, self.valid_key)

    def test_decrypt_wrong_key_raises_error(self):
        """Test that decrypt_token raises error when using wrong key."""
        from cryptography.exceptions import InvalidTag
        ciphertext = encrypt_token(self.test_token, self.valid_key)
        wrong_key_bytes = secrets.token_bytes(32)
        wrong_key = base64.urlsafe_b64encode(wrong_key_bytes).decode()
        with pytest.raises((InvalidTag, ValueError)):
            decrypt_token(ciphertext, wrong_key)


class TestGitHubTokenEncryptionConfig:
    """Test suite for GitHub token encryption configuration."""

    def test_github_token_encryption_key_required_in_config(self):
        """Test that GITHUB_TOKEN_ENCRYPTION_KEY is required in Settings."""
        env = BASE_ENV.copy()
        del env["GITHUB_TOKEN_ENCRYPTION_KEY"]
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError):
                Settings()

    def test_github_token_encryption_key_loaded_from_env(self):
        """Test that github_token_encryption_key is loaded from environment."""
        env = BASE_ENV.copy()
        test_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = test_key
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.github_token_encryption_key == test_key

    def test_github_token_encryption_key_default_set_in_mock_config(self):
        """Test that conftest sets mock encryption key for testing."""
        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.github_token_encryption_key == "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


class TestSupabaseTokenEncryptionIntegration:
    """Test suite for Supabase integration with token encryption."""

    @pytest.mark.asyncio
    async def test_get_github_access_token_decrypts_stored_token(self):
        """Test that get_github_access_token properly decrypts stored tokens."""
        try:
            from backend.services.supabase_client import get_github_access_token
        except ImportError:
            try:
                from services.supabase_client import get_github_access_token
            except ImportError:
                pytest.skip("Could not import get_github_access_token")
        
        user_id = "test-user-123"
        plaintext_token = "ghu_test1234567890"
        test_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        encrypted_token = encrypt_token(plaintext_token, test_key)
        
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[{"github_access_token": encrypted_token}])
        
        with patch("services.supabase_client._client", return_value=mock_client):
            with patch("services.supabase_client.settings.github_token_encryption_key", test_key):
                result = await get_github_access_token(user_id)
                assert result == plaintext_token

    @pytest.mark.asyncio
    async def test_get_github_access_token_returns_none_on_decrypt_error(self):
        """Test that get_github_access_token returns None when decryption fails."""
        try:
            from backend.services.supabase_client import get_github_access_token
        except ImportError:
            try:
                from services.supabase_client import get_github_access_token
            except ImportError:
                pytest.skip("Could not import get_github_access_token")
        
        user_id = "test-user-123"
        tampered_ciphertext = "invalid_base64_ciphertext_data"
        test_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[{"github_access_token": tampered_ciphertext}])
        
        with patch("services.supabase_client._client", return_value=mock_client):
            with patch("services.supabase_client.settings.github_token_encryption_key", test_key):
                result = await get_github_access_token(user_id)
                assert result is None

    @pytest.mark.asyncio
    async def test_save_github_connection_encrypts_token(self):
        """Test that save_github_connection encrypts the access token before storage."""
        try:
            from backend.services.supabase_client import save_github_connection
        except ImportError:
            try:
                from services.supabase_client import save_github_connection
            except ImportError:
                pytest.skip("Could not import save_github_connection")
        
        user_id = "test-user-123"
        plaintext_token = "ghu_test1234567890"
        github_username = "testuser"
        avatar_url = "https://avatars.githubusercontent.com/u/12345"
        test_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_update = MagicMock()
        
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.execute.return_value = MagicMock()
        
        with patch("services.supabase_client._client", return_value=mock_client):
            with patch("services.supabase_client.settings.github_token_encryption_key", test_key):
                await save_github_connection(
                    user_id,
                    plaintext_token,
                    github_username,
                    avatar_url
                )
                
                # Verify that update was called with encrypted token
                mock_table.update.assert_called_once()
                call_args = mock_table.update.call_args[0][0]
                stored_token = call_args.get("github_access_token")
                
                # Token should be encrypted (different from plaintext)
                assert stored_token != plaintext_token
                assert stored_token is not None
                
                # Should be able to decrypt it back
                decrypted = decrypt_token(stored_token, test_key)
                assert decrypted == plaintext_token

    @pytest.mark.asyncio
    async def test_get_github_access_token_returns_none_when_not_connected(self):
        """Test that get_github_access_token returns None when user has no token."""
        try:
            from backend.services.supabase_client import get_github_access_token
        except ImportError:
            try:
                from services.supabase_client import get_github_access_token
            except ImportError:
                pytest.skip("Could not import get_github_access_token")
        
        user_id = "test-user-123"
        test_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[])
        
        with patch("services.supabase_client._client", return_value=mock_client):
            with patch("services.supabase_client.settings.github_token_encryption_key", test_key):
                result = await get_github_access_token(user_id)
                assert result is None
