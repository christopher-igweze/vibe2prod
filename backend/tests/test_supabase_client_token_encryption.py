"""Tests for Supabase client GitHub token encryption integration.

These tests verify that the Supabase client properly encrypts tokens
when saving and decrypts them when retrieving (F-76953061).

Test Location: backend/tests/test_supabase_client_token_encryption.py
Finding: F-76953061 - Unencrypted storage of GitHub OAuth tokens
"""

import pytest
import base64
import secrets
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

try:
    from backend.config import Settings
except ImportError:
    from config import Settings

try:
    from backend.services.supabase_client import (
        get_github_access_token,
        save_github_connection,
    )
except ImportError:
    from services.supabase_client import (
        get_github_access_token,
        save_github_connection,
    )

try:
    from backend.services.token_encryption import encrypt_token
except ImportError:
    from services.token_encryption import encrypt_token


BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
    "GITHUB_TOKEN_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
}


class TestSupabaseClientTokenEncryption:
    """Test suite for Supabase client token encryption."""

    @pytest.fixture
    def encryption_key(self):
        """Generate a valid 32-byte AES-256 key encoded as URL-safe base64."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    @pytest.fixture
    def github_token(self):
        """Sample GitHub OAuth access token."""
        return "gho_16C7e42F292c6912E7710c838347Ae178B4a"

    @pytest.fixture
    def user_id(self):
        """Sample user ID."""
        return str(uuid4())

    @patch("services.supabase_client._client")
    def test_save_github_connection_encrypts_token(
        self, mock_client_factory, encryption_key, github_token, user_id
    ):
        """Test that save_github_connection encrypts the access token before storage."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])
        mock_client_factory.return_value = mock_client

        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = encryption_key

        with patch.dict("os.environ", env, clear=False):
            with patch("services.supabase_client.settings") as mock_settings:
                mock_settings.github_token_encryption_key = encryption_key
                save_github_connection(
                    user_id=user_id,
                    access_token=github_token,
                    github_username="testuser",
                    avatar_url="https://example.com/avatar.jpg",
                )

                # Verify that update was called
                mock_table.update.assert_called_once()
                call_args = mock_table.update.call_args
                update_data = call_args[0][0]

                # The stored token should be encrypted, not plaintext
                stored_token = update_data["github_access_token"]
                assert stored_token != github_token
                assert isinstance(stored_token, str)

    @patch("services.supabase_client._client")
    def test_get_github_access_token_decrypts_token(
        self, mock_client_factory, encryption_key, github_token, user_id
    ):
        """Test that get_github_access_token decrypts the stored token."""
        encrypted_token = encrypt_token(github_token, encryption_key)

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data=[{"github_access_token": encrypted_token}]
        )
        mock_client_factory.return_value = mock_client

        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = encryption_key

        with patch.dict("os.environ", env, clear=False):
            with patch("services.supabase_client.settings") as mock_settings:
                mock_settings.github_token_encryption_key = encryption_key
                result = get_github_access_token(user_id)
                assert result == github_token

    @patch("services.supabase_client._client")
    def test_get_github_access_token_returns_none_if_no_token(
        self, mock_client_factory, user_id
    ):
        """Test that get_github_access_token returns None if user has no token."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[])
        mock_client_factory.return_value = mock_client

        env = BASE_ENV.copy()
        with patch.dict("os.environ", env, clear=False):
            result = get_github_access_token(user_id)
            assert result is None

    @patch("services.supabase_client._client")
    def test_get_github_access_token_returns_none_on_decryption_error(
        self, mock_client_factory, encryption_key, user_id
    ):
        """Test that get_github_access_token handles decryption errors gracefully."""
        # Create a corrupted encrypted token (valid format but wrong key)
        other_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        corrupted_token = encrypt_token("gho_test", other_key)

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_query = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(
            data=[{"github_access_token": corrupted_token}]
        )
        mock_client_factory.return_value = mock_client

        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = encryption_key

        with patch.dict("os.environ", env, clear=False):
            with patch("services.supabase_client.settings") as mock_settings:
                mock_settings.github_token_encryption_key = encryption_key
                with patch("services.supabase_client.logger") as mock_logger:
                    result = get_github_access_token(user_id)
                    assert result is None
                    # Verify warning was logged
                    mock_logger.warning.assert_called_once()

    @patch("services.supabase_client._client")
    def test_save_github_connection_stores_username_and_avatar(
        self, mock_client_factory, encryption_key, github_token, user_id
    ):
        """Test that save_github_connection stores username and avatar metadata."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{}])
        mock_client_factory.return_value = mock_client

        username = "octocat"
        avatar = "https://avatars.githubusercontent.com/u/1?v=4"

        env = BASE_ENV.copy()
        env["GITHUB_TOKEN_ENCRYPTION_KEY"] = encryption_key

        with patch.dict("os.environ", env, clear=False):
            with patch("services.supabase_client.settings") as mock_settings:
                mock_settings.github_token_encryption_key = encryption_key
                save_github_connection(
                    user_id=user_id,
                    access_token=github_token,
                    github_username=username,
                    avatar_url=avatar,
                )

                call_args = mock_table.update.call_args
                update_data = call_args[0][0]

                assert update_data["github_username"] == username
                assert update_data["avatar_url"] == avatar
