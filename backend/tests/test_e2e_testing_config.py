"""Tests for E2E testing configuration validation.

These tests verify that the Settings class properly validates that
e2e_testing can only be enabled in development environment with a valid token.

Test Location: tests/test_e2e_testing_config.py
Project: config.py
Framework: pytest
"""

import pytest
from pydantic import ValidationError

# Import using relative path based on project structure
try:
    from config import Settings
except ImportError:
    import sys
    from pathlib import Path
    # Add backend to path if needed
    backend_path = Path(__file__).parent.parent
    if backend_path.exists():
        sys.path.insert(0, str(backend_path))
        from config import Settings


class TestE2ETestingConfigValidation:
    """Test suite for E2E testing configuration validation."""

    def test_e2e_testing_enabled_in_production_raises_error(self):
        """Test that enabling e2e_testing in production raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                e2e_testing=True,
                environment="production",
                e2e_testing_token="some-token",
                # Required fields with dummy values
                supabase_url="https://test.supabase.co",
                supabase_service_key="test-key",
                supabase_jwt_secret="test-secret",
                openrouter_api_key="test-key",
                daytona_api_key="test-key",
                daytona_api_url="https://test.daytona.io/api",
            )
        
        # Check that the error message mentions e2e_testing and production
        error_message = str(exc_info.value)
        assert "e2e_testing" in error_message.lower() or "production" in error_message.lower()

    def test_e2e_testing_enabled_without_token_raises_error(self):
        """Test that enabling e2e_testing without token raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                e2e_testing=True,
                environment="development",
                e2e_testing_token="",
                # Required fields with dummy values
                supabase_url="https://test.supabase.co",
                supabase_service_key="test-key",
                supabase_jwt_secret="test-secret",
                openrouter_api_key="test-key",
                daytona_api_key="test-key",
                daytona_api_url="https://test.daytona.io/api",
            )
        
        # Check that the error message mentions e2e_testing_token
        error_message = str(exc_info.value)
        assert "token" in error_message.lower()

    def test_e2e_testing_enabled_in_development_with_token_succeeds(self):
        """Test that e2e_testing works in development with valid token."""
        settings = Settings(
            e2e_testing=True,
            environment="development",
            e2e_testing_token="valid-test-token-123",
            # Required fields with dummy values
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-key",
            supabase_jwt_secret="test-secret",
            openrouter_api_key="test-key",
            daytona_api_key="test-key",
            daytona_api_url="https://test.daytona.io/api",
        )
        
        assert settings.e2e_testing is True
        assert settings.environment == "development"
        assert settings.e2e_testing_token == "valid-test-token-123"

    def test_e2e_testing_disabled_allows_production(self):
        """Test that e2e_testing=False allows production environment."""
        settings = Settings(
            e2e_testing=False,
            environment="production",
            # Required fields with dummy values
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-key",
            supabase_jwt_secret="test-secret",
            openrouter_api_key="test-key",
            daytona_api_key="test-key",
            daytona_api_url="https://test.daytona.io/api",
        )
        
        assert settings.e2e_testing is False
        assert settings.environment == "production"

    def test_e2e_testing_disabled_allows_development_without_token(self):
        """Test that e2e_testing=False allows development without token."""
        settings = Settings(
            e2e_testing=False,
            environment="development",
            e2e_testing_token="",
            # Required fields with dummy values
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-key",
            supabase_jwt_secret="test-secret",
            openrouter_api_key="test-key",
            daytona_api_key="test-key",
            daytona_api_url="https://test.daytona.io/api",
        )
        
        assert settings.e2e_testing is False
        assert settings.environment == "development"

    def test_default_environment_is_production(self):
        """Test that the default environment is production."""
        settings = Settings(
            e2e_testing=False,
            # Required fields with dummy values
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-key",
            supabase_jwt_secret="test-secret",
            openrouter_api_key="test-key",
            daytona_api_key="test-key",
            daytona_api_url="https://test.daytona.io/api",
        )
        
        assert settings.environment == "production"

    def test_default_e2e_testing_is_false(self):
        """Test that the default e2e_testing is False."""
        settings = Settings(
            # Required fields with dummy values
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-key",
            supabase_jwt_secret="test-secret",
            openrouter_api_key="test-key",
            daytona_api_key="test-key",
            daytona_api_url="https://test.daytona.io/api",
        )
        
        assert settings.e2e_testing is False

    def test_default_e2e_testing_token_is_empty(self):
        """Test that the default e2e_testing_token is empty string."""
        settings = Settings(
            # Required fields with dummy values
            supabase_url="https://test.supabase.co",
            supabase_service_key="test-key",
            supabase_jwt_secret="test-secret",
            openrouter_api_key="test-key",
            daytona_api_key="test-key",
            daytona_api_url="https://test.daytona.io/api",
        )
        
        assert settings.e2e_testing_token == ""
