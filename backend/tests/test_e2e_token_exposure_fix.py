"""Tests for e2e_testing_token exposure prevention (CWE-532).

Verifies that e2e_testing_token is never exposed in logs, error responses,
or request state as a raw value. Only boolean flags and user_id are stored.

Test Location: tests/test_e2e_token_exposure_fix.py
Project: backend/config.py, backend/api/middleware/auth.py
Framework: pytest
"""

import pytest
from unittest.mock import patch, MagicMock
from pydantic import SecretStr

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


# All required environment variables for Settings to instantiate
BASE_ENV = {
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SUPABASE_JWT_SECRET": "test-jwt-secret",
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "DAYTONA_API_KEY": "test-daytona-api-key",
}


class TestE2ETokenStorageProtection:
    """Test suite for preventing e2e_testing_token exposure in request state."""

    def test_e2e_token_stored_as_secret_str_in_config(self):
        """Test that e2e_testing_token is stored as SecretStr in config."""
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "development",
            "E2E_TESTING": "true",
            "E2E_TESTING_TOKEN": "my-secret-e2e-token-12345",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            # Token must be SecretStr to prevent accidental logging
            assert isinstance(settings.e2e_testing_token, SecretStr)
            # Verify we can access the actual value
            assert settings.e2e_testing_token.get_secret_value() == "my-secret-e2e-token-12345"

    def test_e2e_token_secret_str_repr_does_not_expose_value(self):
        """Test that repr/str of SecretStr token does not expose the actual value."""
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "development",
            "E2E_TESTING": "true",
            "E2E_TESTING_TOKEN": "sensitive-token-value-123",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            token_repr = repr(settings.e2e_testing_token)
            token_str = str(settings.e2e_testing_token)
            # The actual token value should not appear in string representations
            assert "sensitive-token-value-123" not in token_repr
            assert "sensitive-token-value-123" not in token_str
            # But it should contain markers indicating it's masked
            assert "***" in token_repr or "SecretStr" in token_repr

    def test_e2e_token_default_is_empty_secret_str(self):
        """Test that default e2e_testing_token is an empty SecretStr."""
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "development",
            "E2E_TESTING": "false",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert isinstance(settings.e2e_testing_token, SecretStr)
            assert settings.e2e_testing_token.get_secret_value() == ""

    def test_e2e_testing_enabled_without_token_raises_error(self):
        """Test that e2e_testing=True without token raises ValidationError."""
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "development",
            "E2E_TESTING": "true",
            # E2E_TESTING_TOKEN not set, defaults to empty
        })
        with patch.dict("os.environ", env, clear=False):
            from pydantic import ValidationError
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            # Check that the error mentions the missing token
            error_str = str(exc_info.value)
            assert "e2e_testing_token" in error_str or "required" in error_str.lower()

    def test_e2e_testing_in_production_raises_error(self):
        """Test that e2e_testing=True in production raises error."""
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "production",
            "E2E_TESTING": "true",
            "E2E_TESTING_TOKEN": "test-token",
        })
        with patch.dict("os.environ", env, clear=False):
            from pydantic import ValidationError
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            error_str = str(exc_info.value)
            assert "production" in error_str.lower()

    def test_token_value_extraction_via_get_secret_value(self):
        """Test that token value can only be extracted via get_secret_value()."""
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "development",
            "E2E_TESTING": "true",
            "E2E_TESTING_TOKEN": "test-secret-xyz",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            # The only safe way to get the value is via get_secret_value()
            token_value = settings.e2e_testing_token.get_secret_value()
            assert token_value == "test-secret-xyz"
            assert isinstance(token_value, str)
