"""Pytest configuration for shared client usage tests."""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    """Mock config.settings to avoid requiring environment variables."""
    # Create mock settings with required attributes
    mock_settings = MagicMock()
    mock_settings.supabase_url = "http://localhost:54321"
    mock_settings.supabase_service_key = "test-service-key"
    mock_settings.supabase_jwt_secret = "test-jwt-secret"
    mock_settings.daytona_api_key = "test-daytona-key"
    mock_settings.github_client_id = "test-client-id"
    mock_settings.github_client_secret = "test-client-secret"
    mock_settings.github_oauth_state_secret = "test-state-secret"
    mock_settings.github_oauth_allowed_redirect_origins = ""
    mock_settings.github_oauth_state_ttl_minutes = 10
    mock_settings.github_oauth_scope = "repo"
    mock_settings.openrouter_api_key = "test-key"
    mock_settings.openrouter_base_url = "http://localhost:11434"
    mock_settings.model_scanner = "test-model"
    mock_settings.probe_enabled = True
    mock_settings.probe_service_url = "http://localhost:8000"
    
    # Patch config module
    import sys
    if 'config' in sys.modules:
        sys.modules['config'].settings = mock_settings
    else:
        mock_config_module = MagicMock()
        mock_config_module.settings = mock_settings
        sys.modules['config'] = mock_config_module
    
    monkeypatch.setattr("config.settings", mock_settings)
    
    return mock_settings


@pytest.fixture(autouse=True)
def mock_slowapi(monkeypatch):
    """Mock slowapi limiter to avoid import errors."""
    import sys
    
    # Mock the Limiter class
    mock_limit_decorator = lambda x: lambda f: f
    mock_limiter_instance = MagicMock()
    mock_limiter_instance.limit = mock_limit_decorator
    
    class MockLimiter:
        def __init__(self, *args, **kwargs):
            pass
        def limit(self, *args, **kwargs):
            return mock_limit_decorator
    
    # Patch slowapi
    if 'slowapi' in sys.modules:
        sys.modules['slowapi'].Limiter = MockLimiter
    else:
        slowapi_mock = MagicMock()
        slowapi_mock.Limiter = MockLimiter
        slowapi_mock._rate_limit_exceeded = MagicMock()
        sys.modules['slowapi'] = slowapi_mock
    
    # Also patch api.middleware.rate_limit
    monkeypatch.setattr("api.middleware.rate_limit.limiter", mock_limiter_instance)