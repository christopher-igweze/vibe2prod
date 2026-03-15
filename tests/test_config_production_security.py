"""Tests for production security configuration validation.

These tests verify that the Settings class properly prevents debug mode
from being enabled in production environments.

Test Location: tests/test_config_production_security.py
Project: backend/config.py
Framework: pytest
"""

import pytest
from unittest.mock import patch

# Import Settings from config.py - try multiple import paths to handle different project layouts
try:
    from backend.config import Settings
except ImportError:
    try:
        from config import Settings
    except ImportError:
        import sys
        from pathlib import Path
        # Add backend to path if needed
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


class TestProductionSecurityValidation:
    """Test suite for production security validation in Settings."""

    def test_debug_false_in_production_allowed(self):
        """Test that debug=False is allowed in production environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "false",
            "ENVIRONMENT": "production",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.debug is False
            assert settings.environment == "production"

    def test_debug_true_in_production_raises_error(self):
        """Test that debug=True raises ValueError in production environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "production",
        })
        with patch.dict("os.environ", env, clear=False):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "debug=True is not allowed in production" in str(exc_info.value)
            assert "sensitive information" in str(exc_info.value)

    def test_debug_true_in_development_allowed(self):
        """Test that debug=True is allowed in development environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "development",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.debug is True
            assert settings.environment == "development"

    def test_debug_true_in_staging_allowed(self):
        """Test that debug=True is allowed in staging environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "staging",
        })
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.debug is True
            assert settings.environment == "staging"

    def test_debug_default_false_in_production_allowed(self):
        """Test that default debug=False is allowed in production."""
        # Environment variable not set at all - debug defaults to False
        env = BASE_ENV.copy()
        env.update({
            "ENVIRONMENT": "production",
        })
        # Remove DEBUG from env to test default behavior
        env.pop("DEBUG", None)
        with patch.dict("os.environ", env, clear=False):
            settings = Settings()
            assert settings.debug is False
            assert settings.environment == "production"

    def test_environment_not_production_allows_debug(self):
        """Test that debug=True is allowed in any non-production environment."""
        for env_name in ["development", "staging", "test", "local"]:
            env = BASE_ENV.copy()
            env.update({
                "DEBUG": "true",
                "ENVIRONMENT": env_name,
            })
            with patch.dict("os.environ", env, clear=False):
                settings = Settings()
                assert settings.debug is True
                assert settings.environment == env_name
