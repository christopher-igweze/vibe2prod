"""Tests for OAuth repository — token storage, decryption, state consumption."""

from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")
os.environ.setdefault("GITHUB_TOKEN_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")

from services.token_encryption import encrypt_token, decrypt_token, is_encrypted  # noqa: E402


RAW_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


class TestTokenEncryption(unittest.TestCase):
    """Token encryption round-trip and edge cases."""

    def test_encrypt_decrypt_roundtrip(self):
        token = "gho_abc123secrettoken"
        encrypted = encrypt_token(token, RAW_KEY)
        decrypted = decrypt_token(encrypted, RAW_KEY)
        self.assertEqual(decrypted, token)

    def test_encrypted_format(self):
        encrypted = encrypt_token("test", RAW_KEY)
        self.assertIn(".", encrypted)
        parts = encrypted.split(".", 1)
        self.assertEqual(len(parts), 2)
        self.assertTrue(len(parts[0]) > 0)
        self.assertTrue(len(parts[1]) > 0)

    def test_different_encryptions_differ(self):
        """Each encryption uses a fresh nonce — same plaintext produces different ciphertext."""
        a = encrypt_token("same_token", RAW_KEY)
        b = encrypt_token("same_token", RAW_KEY)
        self.assertNotEqual(a, b)
        self.assertEqual(decrypt_token(a, RAW_KEY), decrypt_token(b, RAW_KEY))

    def test_wrong_key_raises(self):
        from cryptography.exceptions import InvalidTag
        encrypted = encrypt_token("secret", RAW_KEY)
        wrong_key = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="
        with self.assertRaises(InvalidTag):
            decrypt_token(encrypted, wrong_key)

    def test_empty_key_raises(self):
        with self.assertRaises(ValueError):
            encrypt_token("test", "")

    def test_invalid_base64_key_raises(self):
        with self.assertRaises(ValueError):
            encrypt_token("test", "not-valid-base64!!!")

    def test_is_encrypted_detects_format(self):
        encrypted = encrypt_token("token", RAW_KEY)
        self.assertTrue(is_encrypted(encrypted))

    def test_is_encrypted_rejects_plaintext(self):
        self.assertFalse(is_encrypted("gho_plaintext_token_no_dots"))

    def test_is_encrypted_rejects_empty(self):
        self.assertFalse(is_encrypted(""))
        self.assertFalse(is_encrypted("."))

    def test_decrypt_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            decrypt_token("no-separator-here", RAW_KEY)


class TestOAuthRepository(unittest.TestCase):
    """OAuth repository DB operations with mocked Supabase client."""

    def _make_mock_client(self, select_data=None):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table

        mock_result = MagicMock()
        mock_result.data = select_data or []
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"jti": "test"}]
        mock_table.insert.return_value.execute.return_value = mock_insert_result

        mock_delete_result = MagicMock()
        mock_delete_result.data = []
        mock_table.delete.return_value.lt.return_value.execute.return_value = mock_delete_result

        return mock_client

    @patch("services.repositories.oauth_repository._client")
    @patch("services.repositories.oauth_repository.settings")
    def test_get_github_access_token_decrypts(self, mock_settings, mock_client_fn):
        from services.repositories.oauth_repository import get_github_access_token

        mock_settings.github_token_encryption_key = RAW_KEY
        encrypted = encrypt_token("gho_real_token", RAW_KEY)
        mock_client_fn.return_value = self._make_mock_client(
            select_data=[{"github_access_token": encrypted}]
        )

        result = asyncio.run(get_github_access_token("user_1"))
        self.assertEqual(result, "gho_real_token")

    @patch("services.repositories.oauth_repository._client")
    def test_get_github_access_token_returns_none_for_missing_user(self, mock_client_fn):
        from services.repositories.oauth_repository import get_github_access_token

        mock_client_fn.return_value = self._make_mock_client(select_data=[])
        result = asyncio.run(get_github_access_token("nonexistent"))
        self.assertIsNone(result)

    @patch("services.repositories.oauth_repository._client")
    @patch("services.repositories.oauth_repository.settings")
    def test_get_github_access_token_returns_none_on_bad_decrypt(self, mock_settings, mock_client_fn):
        from services.repositories.oauth_repository import get_github_access_token

        mock_settings.github_token_encryption_key = RAW_KEY
        mock_client_fn.return_value = self._make_mock_client(
            select_data=[{"github_access_token": "corrupted.data"}]
        )

        result = asyncio.run(get_github_access_token("user_1"))
        self.assertIsNone(result)

    @patch("services.repositories.oauth_repository._client")
    def test_consume_oauth_state_atomic_returns_true_on_first_use(self, mock_client_fn):
        from services.repositories.oauth_repository import consume_oauth_state_atomic

        mock_client_fn.return_value = self._make_mock_client()
        result = asyncio.run(
            consume_oauth_state_atomic(jti="nonce-1", user_id="user_1", ttl_minutes=15)
        )
        self.assertTrue(result)

    @patch("services.repositories.oauth_repository._client")
    def test_consume_oauth_state_atomic_returns_false_on_duplicate(self, mock_client_fn):
        from services.repositories.oauth_repository import consume_oauth_state_atomic

        mock_client = self._make_mock_client()
        mock_table = mock_client.table.return_value
        mock_table.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )
        mock_client_fn.return_value = mock_client

        result = asyncio.run(
            consume_oauth_state_atomic(jti="nonce-1", user_id="user_1", ttl_minutes=15)
        )
        self.assertFalse(result)

    @patch("services.repositories.oauth_repository._client")
    def test_save_github_connection_calls_update(self, mock_client_fn):
        from services.repositories.oauth_repository import save_github_connection

        mock_client = self._make_mock_client()
        mock_client_fn.return_value = mock_client

        asyncio.run(
            save_github_connection(
                user_id="user_1",
                access_token="encrypted_token",
                github_username="octocat",
                avatar_url="https://avatars.githubusercontent.com/u/1",
            )
        )
        mock_client.table.assert_called_with("profiles")

    @patch("services.repositories.oauth_repository._client")
    def test_clear_github_connection_nullifies_fields(self, mock_client_fn):
        from services.repositories.oauth_repository import clear_github_connection

        mock_client = self._make_mock_client()
        mock_client_fn.return_value = mock_client

        asyncio.run(clear_github_connection(user_id="user_1"))
        mock_client.table.assert_called_with("profiles")


if __name__ == "__main__":
    unittest.main()
