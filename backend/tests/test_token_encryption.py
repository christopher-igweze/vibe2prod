"""Tests for the token_encryption module.

These tests verify that the token encryption/decryption functionality
works correctly, including edge cases and error handling.

Test Location: tests/test_token_encryption.py
Project: backend/services/token_encryption.py
Framework: pytest

Note: These tests must be run with --no-header to avoid conftest.py issues,
or run directly with: python -m pytest tests/test_token_encryption.py -p no:cacheprovider
"""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

# Ensure backend is in path and environment is set up BEFORE any other imports
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Set up environment BEFORE importing anything that might import config
os.environ["SUPABASE_URL"] = "http://test.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "test-key"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret"
os.environ["OPENROUTER_API_KEY"] = "test-key"
os.environ["DAYTONA_API_KEY"] = "test-daytona-key"
os.environ["GITHUB_TOKEN_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"x" * 32).decode()

# Now we can import the encryption module directly (it only depends on cryptography)
from services.token_encryption import decrypt_token, encrypt_token, is_encrypted

import pytest
from cryptography.exceptions import InvalidTag

# Test key: URL-safe base64-encoded 32 bytes
TEST_KEY = base64.urlsafe_b64encode(b"x" * 32).decode()
TEST_KEY_ALT = base64.urlsafe_b64encode(b"y" * 32).decode()


class TestTokenEncryption:
    """Test suite for token encryption and decryption."""

    def test_encrypt_token_returns_different_values_each_time(self):
        """Encrypting the same token twice should produce different ciphertexts."""
        token = "ghp_test_token_123"

        encrypted1 = encrypt_token(token, TEST_KEY)
        encrypted2 = encrypt_token(token, TEST_KEY)

        # Should be different due to random nonce
        assert encrypted1 != encrypted2
        # But both should be valid encrypted format
        assert is_encrypted(encrypted1)
        assert is_encrypted(encrypted2)

    def test_decrypt_token_returns_original(self):
        """Decrypting an encrypted token should return the original."""
        original = "ghp_my_secret_token"

        encrypted = encrypt_token(original, TEST_KEY)
        decrypted = decrypt_token(encrypted, TEST_KEY)

        assert decrypted == original

    def test_decrypt_with_wrong_key_fails(self):
        """Decrypting with a different key should raise InvalidTag."""
        original = "ghp_my_secret_token"

        encrypted = encrypt_token(original, TEST_KEY)

        with pytest.raises(InvalidTag):
            decrypt_token(encrypted, TEST_KEY_ALT)

    def test_decrypt_tampered_ciphertext_fails(self):
        """Tampering with ciphertext should be detected and raise InvalidTag."""
        original = "ghp_my_secret_token"

        encrypted = encrypt_token(original, TEST_KEY)
        # Tamper with the ciphertext
        parts = encrypted.split(".")
        tampered_ciphertext = parts[0] + "." + base64.urlsafe_b64encode(b"tampered").decode()

        with pytest.raises(InvalidTag):
            decrypt_token(tampered_ciphertext, TEST_KEY)

    def test_is_encrypted_returns_true_for_encrypted(self):
        """is_encrypted should return True for encrypted tokens."""
        encrypted = encrypt_token("test", TEST_KEY)

        assert is_encrypted(encrypted) is True

    def test_is_encrypted_returns_false_for_plaintext(self):
        """is_encrypted should return False for plaintext tokens."""
        plaintext = "ghp_plaintext_token_123"

        assert is_encrypted(plaintext) is False

    def test_is_encrypted_returns_false_for_empty(self):
        """is_encrypted should return False for empty strings."""
        assert is_encrypted("") is False

    def test_is_encrypted_returns_false_for_invalid_format(self):
        """is_encrypted should return False for strings without separator."""
        assert is_encrypted("notencrypted") is False
        assert is_encrypted("too.many.dots.here") is False
        assert is_encrypted(".") is False  # empty parts

    def test_encrypt_decrypt_long_token(self):
        """Should handle long tokens correctly."""
        # GitHub tokens can be up to 255 characters
        long_token = "ghp_" + "a" * 251

        encrypted = encrypt_token(long_token, TEST_KEY)
        decrypted = decrypt_token(encrypted, TEST_KEY)

        assert decrypted == long_token

    def test_encrypt_decrypt_unicode(self):
        """Should handle unicode characters correctly."""
        # Though GitHub tokens are ASCII, test robustness
        unicode_token = "token_with_unicode_ñáéíóú_中文"

        encrypted = encrypt_token(unicode_token, TEST_KEY)
        decrypted = decrypt_token(encrypted, TEST_KEY)

        assert decrypted == unicode_token

    def test_missing_key_raises_valueerror(self):
        """Encrypting without a key should raise ValueError."""
        with pytest.raises(ValueError, match="GITHUB_TOKEN_ENCRYPTION_KEY"):
            encrypt_token("test", "")

        with pytest.raises(ValueError, match="GITHUB_TOKEN_ENCRYPTION_KEY"):
            encrypt_token("test", None)  # type: ignore[arg-type]

    def test_invalid_key_raises_valueerror(self):
        """Encrypting with an invalid key should raise ValueError."""
        with pytest.raises(ValueError, match="not valid base64"):
            encrypt_token("test", "not-valid-base64!!!")

    def test_wrong_key_length_raises_valueerror(self):
        """Encrypting with a key of wrong length should raise ValueError."""
        # 16 bytes instead of 32
        short_key = base64.urlsafe_b64encode(b"x" * 16).decode()

        with pytest.raises(ValueError, match="32 bytes"):
            encrypt_token("test", short_key)

    def test_decrypt_malformed_raises_valueerror(self):
        """Decrypting malformed data should raise ValueError."""
        with pytest.raises(ValueError, match="not in the expected encrypted format"):
            decrypt_token("not-valid-format", TEST_KEY)

    def test_decrypt_invalid_base64_raises_valueerror(self):
        """Decrypting with invalid base64 should raise ValueError."""
        # Valid format but invalid base64
        with pytest.raises(ValueError, match="invalid base64"):
            decrypt_token("abc.def", TEST_KEY)

    def test_uses_environment_variable_when_key_none(self, monkeypatch):
        """Should read key from environment when key parameter is None."""
        monkeypatch.setenv("GITHUB_TOKEN_ENCRYPTION_KEY", TEST_KEY)

        original = "test_token"
        encrypted = encrypt_token(original, None)  # type: ignore[arg-type]
        decrypted = decrypt_token(encrypted, None)  # type: ignore[arg-type]

        assert decrypted == original


class TestTokenEncryptionIntegration:
    """Integration tests with actual GitHub token formats."""

    def test_classic_github_token(self):
        """Should handle classic GitHub personal access tokens."""
        # Format: ghp_<40 alphanumeric chars>
        token = "ghp_" + "a" * 36

        encrypted = encrypt_token(token, TEST_KEY)
        decrypted = decrypt_token(encrypted, TEST_KEY)

        assert decrypted == token

    def test_fine_grained_github_token(self):
        """Should handle fine-grained GitHub personal access tokens."""
        # Format: github_pat_<...>
        token = "github_pat_11ABCD" + "x" * 100

        encrypted = encrypt_token(token, TEST_KEY)
        decrypted = decrypt_token(encrypted, TEST_KEY)

        assert decrypted == token

    def test_oauth_access_token(self):
        """Should handle OAuth access tokens."""
        # OAuth tokens are typically alphanumeric
        token = "gho_" + "x" * 32

        encrypted = encrypt_token(token, TEST_KEY)
        decrypted = decrypt_token(encrypted, TEST_KEY)

        assert decrypted == token


class TestPlaintextTokenDetection:
    """Tests for detecting and handling plaintext tokens."""

    def test_plaintext_github_token_not_encrypted(self):
        """Real-looking GitHub tokens should not appear encrypted."""
        plaintext_tokens = [
            "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxx",
        ]

        for token in plaintext_tokens:
            assert is_encrypted(token) is False, f"Token should not appear encrypted: {token[:10]}..."

    def test_migration_scenario_plaintext_to_encrypted(self):
        """Simulate the migration flow: detect plaintext, encrypt, verify."""
        # Simulate a plaintext token in the database
        db_value = "ghp_old_plaintext_token_12345"

        # Step 1: Detect if encrypted
        assert not is_encrypted(db_value), "Should detect as plaintext"

        # Step 2: Encrypt it
        encrypted = encrypt_token(db_value, TEST_KEY)
        assert is_encrypted(encrypted), "Should now appear encrypted"

        # Step 3: Verify it can be decrypted
        decrypted = decrypt_token(encrypted, TEST_KEY)
        assert decrypted == db_value, "Should decrypt back to original"

    def test_attempt_decrypt_plaintext_gives_helpful_error(self):
        """Attempting to decrypt plaintext should give a helpful error message."""
        plaintext = "ghp_plaintext_token"

        with pytest.raises(ValueError) as exc_info:
            decrypt_token(plaintext, TEST_KEY)

        assert "not in the expected encrypted format" in str(exc_info.value)
        assert "plaintext token" in str(exc_info.value).lower()
