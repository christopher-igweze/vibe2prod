"""Tests for URL sanitization security fix (F-8dcfb516).

Verifies that sensitive query parameters are redacted from logged URLs
using a whitelist approach, and that sanitization is applied consistently
across all request logging via the AccessLogMiddleware.

Test Location: tests/test_url_sanitization_whitelist.py
Project: backend/main.py
Framework: pytest
Finding: F-8dcfb516 - Sensitive query parameters logged in URLs without sanitization
"""

import pytest
from unittest.mock import patch

# Import the sanitization function and safe params set from main.py
try:
    from backend.main import _sanitize_url, _SAFE_QUERY_PARAMS
except ImportError:
    try:
        from main import _sanitize_url, _SAFE_QUERY_PARAMS
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from main import _sanitize_url, _SAFE_QUERY_PARAMS
        else:
            raise ImportError("Could not import _sanitize_url or _SAFE_QUERY_PARAMS from any known path")


class TestURLSanitizationWhitelist:
    """Test suite for URL sanitization using whitelist approach."""

    def test_sanitize_url_redacts_token_parameter(self):
        """Test that 'token' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?token=secret123&page=1"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        assert "secret123" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_redacts_key_parameter(self):
        """Test that 'key' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?key=abc123def456&limit=10"
        sanitized = _sanitize_url(url)
        assert "key=***" in sanitized
        assert "abc123def456" not in sanitized
        assert "limit=10" in sanitized

    def test_sanitize_url_redacts_user_id_parameter(self):
        """Test that 'user_id' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?user_id=12345&sort=name"
        sanitized = _sanitize_url(url)
        assert "user_id=***" in sanitized
        assert "12345" not in sanitized
        assert "sort=name" in sanitized

    def test_sanitize_url_redacts_email_parameter(self):
        """Test that 'email' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?email=user@example.com&page=2"
        sanitized = _sanitize_url(url)
        assert "email=***" in sanitized
        assert "user@example.com" not in sanitized
        assert "page=2" in sanitized

    def test_sanitize_url_redacts_session_id_parameter(self):
        """Test that 'session_id' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?session_id=sess_xyz789&version=v1"
        sanitized = _sanitize_url(url)
        assert "session_id=***" in sanitized
        assert "sess_xyz789" not in sanitized
        assert "version=v1" in sanitized

    def test_sanitize_url_redacts_password_parameter(self):
        """Test that 'password' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?password=mypass123&search=test"
        sanitized = _sanitize_url(url)
        assert "password=***" in sanitized
        assert "mypass123" not in sanitized
        assert "search=test" in sanitized

    def test_sanitize_url_redacts_jwt_parameter(self):
        """Test that 'jwt' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?jwt=eyJhbGc&q=query"
        sanitized = _sanitize_url(url)
        assert "jwt=***" in sanitized
        assert "eyJhbGc" not in sanitized
        assert "q=query" in sanitized

    def test_sanitize_url_redacts_access_token_parameter(self):
        """Test that 'access_token' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?access_token=tk_prod_123&filter=active"
        sanitized = _sanitize_url(url)
        assert "access_token=***" in sanitized
        assert "tk_prod_123" not in sanitized
        assert "filter=active" in sanitized

    def test_sanitize_url_redacts_refresh_token_parameter(self):
        """Test that 'refresh_token' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?refresh_token=rt_xyz&lang=en"
        sanitized = _sanitize_url(url)
        assert "refresh_token=***" in sanitized
        assert "rt_xyz" not in sanitized
        assert "lang=en" in sanitized

    def test_sanitize_url_redacts_secret_parameter(self):
        """Test that 'secret' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?secret=my_secret_value&locale=en_US"
        sanitized = _sanitize_url(url)
        assert "secret=***" in sanitized
        assert "my_secret_value" not in sanitized
        assert "locale=en_US" in sanitized

    def test_sanitize_url_redacts_bearer_parameter(self):
        """Test that 'bearer' parameters are redacted (not in whitelist)."""
        url = "http://api.example.com/endpoint?bearer=Bearer_token_123&v=2"
        sanitized = _sanitize_url(url)
        assert "bearer=***" in sanitized
        assert "Bearer_token_123" not in sanitized
        assert "v=2" in sanitized

    def test_sanitize_url_preserves_safe_params(self):
        """Test that safe parameters are preserved in the URL."""
        url = "http://api.example.com/endpoint?page=1&limit=10&sort=name&offset=0"
        sanitized = _sanitize_url(url)
        assert "page=1" in sanitized
        assert "limit=10" in sanitized
        assert "sort=name" in sanitized
        assert "offset=0" in sanitized

    def test_sanitize_url_mixed_safe_and_unsafe_params(self):
        """Test sanitization with mix of safe and unsafe parameters."""
        url = "http://api.example.com/endpoint?page=1&token=secret&limit=10&password=pass123&sort=name"
        sanitized = _sanitize_url(url)
        # Safe params preserved
        assert "page=1" in sanitized
        assert "limit=10" in sanitized
        assert "sort=name" in sanitized
        # Unsafe params redacted
        assert "token=***" in sanitized
        assert "secret" not in sanitized
        assert "password=***" in sanitized
        assert "pass123" not in sanitized

    def test_sanitize_url_case_insensitive_redaction(self):
        """Test that parameter name matching is case-insensitive."""
        url = "http://api.example.com/endpoint?TOKEN=secret123&Password=pass456&PAGE=1"
        sanitized = _sanitize_url(url)
        assert "TOKEN=***" in sanitized
        assert "secret123" not in sanitized
        assert "Password=***" in sanitized
        assert "pass456" not in sanitized
        assert "PAGE=1" in sanitized

    def test_sanitize_url_empty_param_value(self):
        """Test sanitization of parameters with empty values."""
        url = "http://api.example.com/endpoint?token=&page=1"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_multiple_same_parameter(self):
        """Test sanitization when same parameter appears multiple times."""
        url = "http://api.example.com/endpoint?token=first&page=1&token=second"
        sanitized = _sanitize_url(url)
        assert sanitized.count("token=***") == 2
        assert "first" not in sanitized
        assert "second" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_special_characters_in_value(self):
        """Test sanitization preserves structure with special characters."""
        url = "http://api.example.com/endpoint?token=abc%20def%3D%26&page=1"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        assert "abc%20def" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_no_query_string(self):
        """Test sanitization of URL without query string."""
        url = "http://api.example.com/endpoint"
        sanitized = _sanitize_url(url)
        assert sanitized == url

    def test_sanitize_url_only_fragment(self):
        """Test sanitization of URL with only fragment."""
        url = "http://api.example.com/endpoint#section"
        sanitized = _sanitize_url(url)
        assert sanitized == url

    def test_sanitize_url_multiple_ampersands(self):
        """Test sanitization with multiple consecutive ampersands."""
        url = "http://api.example.com/endpoint?page=1&&token=secret&&limit=10"
        sanitized = _sanitize_url(url)
        assert "page=1" in sanitized
        assert "token=***" in sanitized
        assert "secret" not in sanitized
        assert "limit=10" in sanitized

    def test_safe_query_params_is_frozenset(self):
        """Test that _SAFE_QUERY_PARAMS is a frozenset for immutability."""
        assert isinstance(_SAFE_QUERY_PARAMS, frozenset)

    def test_safe_query_params_contains_expected_values(self):
        """Test that _SAFE_QUERY_PARAMS contains the expected safe parameters."""
        expected_safe = {
            "page", "limit", "offset", "sort", "order", "filter",
            "q", "search", "format", "version", "lang", "locale", "v", "cb"
        }
        assert _SAFE_QUERY_PARAMS == expected_safe

    def test_sanitize_url_preserves_all_safe_params(self):
        """Test that all parameters in _SAFE_QUERY_PARAMS are preserved."""
        safe_params = []
        for param in _SAFE_QUERY_PARAMS:
            safe_params.append(f"{param}=value")
        query_string = "&".join(safe_params)
        url = f"http://api.example.com/endpoint?{query_string}"
        sanitized = _sanitize_url(url)
        # Each safe param should be preserved unchanged
        for param in _SAFE_QUERY_PARAMS:
            assert f"{param}=value" in sanitized

    def test_sanitize_url_with_encoded_sensitive_data(self):
        """Test sanitization of URL-encoded sensitive parameters."""
        url = "http://api.example.com/endpoint?email=test%40example.com&page=1"
        sanitized = _sanitize_url(url)
        assert "email=***" in sanitized
        assert "test%40example.com" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_non_string_input(self):
        """Test sanitization works with non-string URL objects."""
        class URLLike:
            def __str__(self):
                return "http://api.example.com/endpoint?token=secret&page=1"
        url_obj = URLLike()
        sanitized = _sanitize_url(url_obj)
        assert "token=***" in sanitized
        assert "secret" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_very_long_url(self):
        """Test sanitization of very long URLs with many parameters."""
        params = []
        for i in range(50):
            if i % 2 == 0:
                params.append(f"page={i}")
            else:
                params.append(f"token{i}=secret{i}")
        url = f"http://api.example.com/endpoint?" + "&".join(params)
        sanitized = _sanitize_url(url)
        # Check that safe params are preserved
        for i in range(0, 50, 2):
            assert f"page={i}" in sanitized
        # Check that sensitive params are redacted
        for i in range(1, 50, 2):
            assert f"secret{i}" not in sanitized
            assert f"token{i}=***" in sanitized
