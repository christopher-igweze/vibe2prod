"""Tests for debug mode security validation.

These tests verify that the Settings class properly prevents debug mode
from being enabled in ANY environment, not just production.

Test Location: tests/test_config_debug_security.py
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


class TestDebugModeSecurityValidation:
    """Test suite for debug mode security validation in Settings.
    
    The fix ensures debug=True is NOT allowed in ANY environment.
    Previously, debug=True was only blocked in 'production' environment,
    allowing it in staging, development, test, or any other environment.
    This was a security issue as debug mode exposes detailed request logs,
    stack traces, and internal application state.
    """

    def test_debug_false_in_any_environment_allowed(self):
        """Test that debug=False is allowed regardless of environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "false",
            "ENVIRONMENT": "production",
        })
        with patch.dict("os.environ", env, clear=True):
            settings = Settings()
            assert settings.debug is False

    def test_debug_true_in_production_raises_error(self):
        """Test that debug=True raises ValueError in production environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "production",
        })
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "debug=True is not allowed in any environment" in str(exc_info.value)

    def test_debug_true_in_staging_raises_error(self):
        """Test that debug=True raises ValueError in staging environment.
        
        This was the original vulnerability - staging was not protected.
        """
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "staging",
        })
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "debug=True is not allowed in any environment" in str(exc_info.value)

    def test_debug_true_in_development_raises_error(self):
        """Test that debug=True raises ValueError in development environment.
        
        Previously development allowed debug=True, which is now blocked.
        """
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "development",
        })
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "debug=True is not allowed in any environment" in str(exc_info.value)

    def test_debug_true_in_test_raises_error(self):
        """Test that debug=True raises ValueError in test environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "test",
        })
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "debug=True is not allowed in any environment" in str(exc_info.value)

    def test_debug_true_in_custom_environment_raises_error(self):
        """Test that debug=True raises ValueError in any custom environment."""
        env = BASE_ENV.copy()
        env.update({
            "DEBUG": "true",
            "ENVIRONMENT": "custom-env",
        })
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Settings()
            assert "debug=True is not allowed in any environment" in str(exc_info.value)
