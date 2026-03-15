"""Local conftest for security tests.

This conftest overrides the top-level autouse fixtures that reference
``api.middleware.rate_limit`` (which requires a fully installed ``slowapi``
package with all submodules) so that the URL-sanitization unit tests can
run in environments where only a subset of dependencies are installed.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


def _ensure_slowapi_mocked() -> None:
    """Insert complete slowapi mock into sys.modules before any import of it."""
    if "slowapi" not in sys.modules or not isinstance(sys.modules["slowapi"], MagicMock):
        slowapi_mock = MagicMock()
        slowapi_mock.Limiter = MagicMock
        sys.modules["slowapi"] = slowapi_mock

    for submod in ("slowapi.util", "slowapi.errors", "slowapi.middleware", "slowapi.extension"):
        if submod not in sys.modules:
            sys.modules[submod] = MagicMock()

    # Ensure slowapi.util.get_remote_address is callable
    sys.modules["slowapi.util"].get_remote_address = lambda req: "127.0.0.1"


_ensure_slowapi_mocked()


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    """Provide mock settings — overrides the top-level autouse fixture."""
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
    mock_settings.debug = False
    mock_settings.cors_allowed_origins = ""
    mock_settings.cors_vercel_projects = ""

    if "config" in sys.modules:
        sys.modules["config"].settings = mock_settings
    else:
        mock_config_module = MagicMock()
        mock_config_module.settings = mock_settings
        sys.modules["config"] = mock_config_module

    monkeypatch.setattr("config.settings", mock_settings)
    return mock_settings


@pytest.fixture(autouse=True)
def mock_slowapi(monkeypatch):
    """Mock slowapi fully — overrides the top-level autouse fixture."""
    _ensure_slowapi_mocked()

    mock_limiter_instance = MagicMock()
    mock_limiter_instance.limit = lambda x: (lambda f: f)

    # Patch the rate_limit module's limiter attribute safely
    try:
        monkeypatch.setattr("api.middleware.rate_limit.limiter", mock_limiter_instance)
    except (ImportError, AttributeError):
        pass  # If module can't be imported even after mocking, skip patching it

    return mock_limiter_instance
