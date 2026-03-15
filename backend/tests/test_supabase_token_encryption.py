"""Tests for Supabase client GitHub token encryption integration.

These tests verify that GitHub access tokens are encrypted when stored
and decrypted when retrieved from the Supabase database.

Test Location: tests/test_supabase_token_encryption.py
Framework: pytest
"""

import pytest
import base64
import secrets
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

try:
    from backend.services.supabase_client import (
        save_github_connection,
        get_github_access_token,
    )
except ImportError:
    try:
        from services.supabase_client import (
            save_github_connection,
            get_github_access_token,
        )
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from services.supabase_client import (
                save_github_connection,
                get_github_access_token,
            )
        else:
            raise ImportError("Could not import supabase_client from any known path")

try:
    from backend.services.token_encryption import encrypt_token
except ImportError:
    try:
        from services.token_encryption import encrypt_token
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from services.token_encryption import encrypt_token
        else:
            raise ImportError("Could not import token_encryption from any known path")

try:
    from backend.config import settings
except ImportError:
    try:
        from config import settings
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        if backend_path.exists():
            sys.path.insert(0, str(backend_path))
            from config import settings
        else:
            raise ImportError("Could not import settings from any known path")


class TestSupabaseTokenEncryption:
    """Test suite for Supabase client token encryption integration."""

    def setup_method(self):
        """Set up test fixtures."""
        key_bytes = secrets.token_bytes(32)
        self.valid_key = base64.urlsafe_b64encode(key_bytes).decode()
        self.test_token = "ghu_test1234567890abcdefghijklmnopqrst"
        self.test_user_id = "user-123-uuid"
        self.test_username = "testuser"
        self.test_avatar_url = "https://example.com/avatar.jpg"

    @pytest.mark.asyncio
    async def test_save_github_connection_encrypts_token(self):
        """Test that save_github_connection encrypts the access token before storage."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_update = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.execute.return_value = MagicMock(data=[{"id": self.test_user_id}])

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                await save_github_connection(
                    user_id=self.test_user_id,
                    access_token=self.test_token,
                    github_username=self.test_username,
                    avatar_url=self.test_avatar_url,
                )

                mock_table.update.assert_called_once()
                call_args = mock_table.update.call_args
                update_data = call_args[0][0]
                assert "github_access_token" in update_data
                encrypted_token = update_data["github_access_token"]
                assert encrypted_token != self.test_token
                assert len(encrypted_token) > 0

    @pytest.mark.asyncio
    async def test_get_github_access_token_decrypts_token(self):
        """Test that get_github_access_token decrypts the stored token."""
        encrypted_token = encrypt_token(self.test_token, self.valid_key)
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_id = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_id
        mock_eq_id.limit.return_value.execute.return_value = MagicMock(
            data=[{"github_access_token": encrypted_token}]
        )

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                result = await get_github_access_token(self.test_user_id)
                assert result == self.test_token

    @pytest.mark.asyncio
    async def test_get_github_access_token_returns_none_when_no_token(self):
        """Test that get_github_access_token returns None when user has no token."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_id = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_id
        mock_eq_id.limit.return_value.execute.return_value = MagicMock(data=[])

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                result = await get_github_access_token(self.test_user_id)
                assert result is None

    @pytest.mark.asyncio
    async def test_get_github_access_token_returns_none_on_decryption_failure(self):
        """Test that get_github_access_token returns None when decryption fails."""
        tampered_ciphertext = "corrupted_ciphertext_data"
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_id = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_id
        mock_eq_id.limit.return_value.execute.return_value = MagicMock(
            data=[{"github_access_token": tampered_ciphertext}]
        )

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                result = await get_github_access_token(self.test_user_id)
                assert result is None

    @pytest.mark.asyncio
    async def test_get_github_access_token_handles_wrong_key(self):
        """Test that get_github_access_token handles wrong encryption key gracefully."""
        encrypted_with_key1 = encrypt_token(self.test_token, self.valid_key)
        key_bytes = secrets.token_bytes(32)
        wrong_key = base64.urlsafe_b64encode(key_bytes).decode()

        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_id = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_id
        mock_eq_id.limit.return_value.execute.return_value = MagicMock(
            data=[{"github_access_token": encrypted_with_key1}]
        )

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", wrong_key):
                result = await get_github_access_token(self.test_user_id)
                assert result is None

    @pytest.mark.asyncio
    async def test_save_github_connection_includes_username_and_avatar(self):
        """Test that save_github_connection updates username and avatar along with token."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_update = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.execute.return_value = MagicMock(data=[{"id": self.test_user_id}])

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                await save_github_connection(
                    user_id=self.test_user_id,
                    access_token=self.test_token,
                    github_username=self.test_username,
                    avatar_url=self.test_avatar_url,
                )

                call_args = mock_table.update.call_args
                update_data = call_args[0][0]
                assert update_data["github_username"] == self.test_username
                assert update_data["avatar_url"] == self.test_avatar_url
                assert "github_access_token" in update_data

    @pytest.mark.asyncio
    async def test_get_github_access_token_returns_none_for_null_stored_token(self):
        """Test that get_github_access_token returns None when stored token is null."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq_user = MagicMock()
        mock_eq_id = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq_user
        mock_eq_user.eq.return_value = mock_eq_id
        mock_eq_id.limit.return_value.execute.return_value = MagicMock(
            data=[{"github_access_token": None}]
        )

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                result = await get_github_access_token(self.test_user_id)
                assert result is None

    def test_save_github_connection_never_stores_plaintext_token(self):
        """Test that plaintext tokens are never passed to the database layer."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_update = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.update.return_value = mock_update
        mock_update.execute.return_value = MagicMock(data=[{"id": self.test_user_id}])

        with patch("services.supabase_client._client", return_value=mock_client):
            with patch.object(settings, "github_token_encryption_key", self.valid_key):
                asyncio.run(
                    save_github_connection(
                        user_id=self.test_user_id,
                        access_token=self.test_token,
                        github_username=self.test_username,
                        avatar_url=self.test_avatar_url,
                    )
                )

                call_args = mock_table.update.call_args
                update_data = call_args[0][0]
                stored_token = update_data["github_access_token"]
                assert stored_token != self.test_token
                assert self.test_token not in str(update_data)
