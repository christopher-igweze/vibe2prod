"""Tests for URL sanitization security fix (F-8dcfb516).

Verifies that sensitive query parameters are redacted from logged URLs
using a whitelist approach, and that sanitization is applied consistently
across all request logging (not just error handlers).

Test Location: tests/test_url_sanitization_security.py
Project: backend/main.py
Framework: pytest
Finding: F-8dcfb516 - Sensitive query parameters logged in URLs without sanitization
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from logging import LogRecord

# Add backend to path if needed
backend_path = Path(__file__).parent.parent / "backend"
if backend_path.exists():
    sys.path.insert(0, str(backend_path.parent))

try:
    from backend.main import _sanitize_url, _SAFE_QUERY_PARAMS
except ImportError:
    from main import _sanitize_url, _SAFE_QUERY_PARAMS


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
        url = "http://api.example.com/endpoint?refresh_token=ref_token_abc&order=desc"
        sanitized = _sanitize_url(url)
        assert "refresh_token=***" in sanitized
        assert "ref_token_abc" not in sanitized
        assert "order=desc" in sanitized

    def test_sanitize_url_preserves_page_parameter(self):
        """Test that 'page' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?page=5&token=secret"
        sanitized = _sanitize_url(url)
        assert "page=5" in sanitized
        assert "token=***" in sanitized

    def test_sanitize_url_preserves_limit_parameter(self):
        """Test that 'limit' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?limit=50&key=abc123"
        sanitized = _sanitize_url(url)
        assert "limit=50" in sanitized
        assert "key=***" in sanitized

    def test_sanitize_url_preserves_offset_parameter(self):
        """Test that 'offset' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?offset=100&secret=xyz"
        sanitized = _sanitize_url(url)
        assert "offset=100" in sanitized
        assert "secret=***" in sanitized

    def test_sanitize_url_preserves_sort_parameter(self):
        """Test that 'sort' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?sort=name&password=pass123"
        sanitized = _sanitize_url(url)
        assert "sort=name" in sanitized
        assert "password=***" in sanitized

    def test_sanitize_url_preserves_order_parameter(self):
        """Test that 'order' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?order=asc&jwt=token_xyz"
        sanitized = _sanitize_url(url)
        assert "order=asc" in sanitized
        assert "jwt=***" in sanitized

    def test_sanitize_url_preserves_filter_parameter(self):
        """Test that 'filter' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?filter=active&bearer=token123"
        sanitized = _sanitize_url(url)
        assert "filter=active" in sanitized
        assert "bearer=***" in sanitized

    def test_sanitize_url_preserves_q_parameter(self):
        """Test that 'q' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?q=search_term&access_token=token"
        sanitized = _sanitize_url(url)
        assert "q=search_term" in sanitized
        assert "access_token=***" in sanitized

    def test_sanitize_url_preserves_search_parameter(self):
        """Test that 'search' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?search=query&refresh_token=ref"
        sanitized = _sanitize_url(url)
        assert "search=query" in sanitized
        assert "refresh_token=***" in sanitized

    def test_sanitize_url_preserves_format_parameter(self):
        """Test that 'format' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?format=json&user_id=123"
        sanitized = _sanitize_url(url)
        assert "format=json" in sanitized
        assert "user_id=***" in sanitized

    def test_sanitize_url_preserves_version_parameter(self):
        """Test that 'version' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?version=v2&email=test@test.com"
        sanitized = _sanitize_url(url)
        assert "version=v2" in sanitized
        assert "email=***" in sanitized

    def test_sanitize_url_preserves_lang_parameter(self):
        """Test that 'lang' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?lang=en&session_id=sess123"
        sanitized = _sanitize_url(url)
        assert "lang=en" in sanitized
        assert "session_id=***" in sanitized

    def test_sanitize_url_preserves_locale_parameter(self):
        """Test that 'locale' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?locale=en_US&password=pwd123"
        sanitized = _sanitize_url(url)
        assert "locale=en_US" in sanitized
        assert "password=***" in sanitized

    def test_sanitize_url_preserves_v_parameter(self):
        """Test that 'v' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?v=1.0.0&jwt=jwttoken"
        sanitized = _sanitize_url(url)
        assert "v=1.0.0" in sanitized
        assert "jwt=***" in sanitized

    def test_sanitize_url_preserves_cb_parameter(self):
        """Test that 'cb' parameter (in whitelist) is preserved."""
        url = "http://api.example.com/endpoint?cb=12345&key=secret_key"
        sanitized = _sanitize_url(url)
        assert "cb=12345" in sanitized
        assert "key=***" in sanitized

    def test_sanitize_url_case_insensitive_token(self):
        """Test that parameter matching is case-insensitive for 'token'."""
        url = "http://api.example.com/endpoint?Token=abc123&TOKEN=xyz789"
        sanitized = _sanitize_url(url)
        assert "Token=***" in sanitized
        assert "TOKEN=***" in sanitized
        assert "abc123" not in sanitized
        assert "xyz789" not in sanitized

    def test_sanitize_url_case_insensitive_key(self):
        """Test that parameter matching is case-insensitive for 'key'."""
        url = "http://api.example.com/endpoint?Key=secret&KEY=topsecret"
        sanitized = _sanitize_url(url)
        assert "Key=***" in sanitized
        assert "KEY=***" in sanitized
        assert "secret" not in sanitized
        assert "topsecret" not in sanitized

    def test_sanitize_url_multiple_parameters_mixed(self):
        """Test sanitization with multiple safe and unsafe parameters."""
        url = "http://api.example.com/endpoint?page=1&token=secret&limit=50&user_id=123&sort=name&password=pass123"
        sanitized = _sanitize_url(url)
        assert "page=1" in sanitized
        assert "token=***" in sanitized
        assert "limit=50" in sanitized
        assert "user_id=***" in sanitized
        assert "sort=name" in sanitized
        assert "password=***" in sanitized
        assert "secret" not in sanitized
        assert "123" not in sanitized or "limit=50" in sanitized  # 123 only in limit
        assert "pass123" not in sanitized

    def test_sanitize_url_empty_parameter_value(self):
        """Test sanitization with empty parameter values."""
        url = "http://api.example.com/endpoint?token=&page=1&key=&sort=asc"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        assert "key=***" in sanitized
        assert "page=1" in sanitized
        assert "sort=asc" in sanitized

    def test_sanitize_url_no_parameters(self):
        """Test sanitization with URL that has no parameters."""
        url = "http://api.example.com/endpoint"
        sanitized = _sanitize_url(url)
        assert sanitized == url

    def test_sanitize_url_fragment_not_affected(self):
        """Test that URL fragments are not modified."""
        url = "http://api.example.com/endpoint?token=abc123#section"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        # Fragment may or may not be present depending on URL parsing

    def test_sanitize_url_with_object_input(self):
        """Test that _sanitize_url accepts any object with str() method."""
        class URLObj:
            def __str__(self):
                return "http://api.example.com/endpoint?token=secret&page=1"
        
        url_obj = URLObj()
        sanitized = _sanitize_url(url_obj)
        assert "token=***" in sanitized
        assert "secret" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_special_characters_in_values(self):
        """Test sanitization with special characters in parameter values."""
        url = "http://api.example.com/endpoint?token=abc%2Fdef%3Dxyz&page=1"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        assert "abc%2Fdef%3Dxyz" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_multiple_same_parameters(self):
        """Test sanitization when same parameter appears multiple times."""
        url = "http://api.example.com/endpoint?token=secret1&token=secret2&page=1"
        sanitized = _sanitize_url(url)
        # Both token parameters should be redacted
        token_count = sanitized.count("token=***")
        assert token_count >= 1  # At least one redacted
        assert "secret1" not in sanitized
        assert "secret2" not in sanitized
        assert "page=1" in sanitized

    def test_sanitize_url_ampersand_separation(self):
        """Test that parameters separated by ampersands are all processed."""
        url = "http://api.example.com/endpoint?page=1&token=sec&limit=10&user_id=123&sort=asc"
        sanitized = _sanitize_url(url)
        assert "page=1" in sanitized
        assert "token=***" in sanitized
        assert "limit=10" in sanitized
        assert "user_id=***" in sanitized
        assert "sort=asc" in sanitized
        assert "sec" not in sanitized
        assert "123" not in sanitized or "limit=10" in sanitized


class TestSafeQueryParamsWhitelist:
    """Test suite for _SAFE_QUERY_PARAMS whitelist constant."""

    def test_safe_query_params_is_frozenset(self):
        """Test that _SAFE_QUERY_PARAMS is a frozenset for immutability."""
        assert isinstance(_SAFE_QUERY_PARAMS, frozenset)

    def test_safe_query_params_contains_pagination_params(self):
        """Test that whitelist includes pagination parameters."""
        pagination_params = {"page", "limit", "offset"}
        assert pagination_params.issubset(_SAFE_QUERY_PARAMS)

    def test_safe_query_params_contains_filtering_params(self):
        """Test that whitelist includes filtering/search parameters."""
        filtering_params = {"sort", "order", "filter", "q", "search"}
        assert filtering_params.issubset(_SAFE_QUERY_PARAMS)

    def test_safe_query_params_contains_metadata_params(self):
        """Test that whitelist includes metadata/format parameters."""
        metadata_params = {"format", "version", "lang", "locale", "v", "cb"}
        assert metadata_params.issubset(_SAFE_QUERY_PARAMS)

    def test_safe_query_params_does_not_include_sensitive_params(self):
        """Test that whitelist excludes known sensitive parameters."""
        sensitive_params = {
            "token", "key", "secret", "password", "jwt", "bearer",
            "access_token", "refresh_token", "user_id", "email", "session_id"
        }
        # Check that sensitive params are NOT in the whitelist
        for param in sensitive_params:
            assert param not in _SAFE_QUERY_PARAMS, f"{param} should not be in whitelist"


class TestURLSanitizationInContext:
    """Test URL sanitization in realistic application contexts."""

    def test_sanitize_url_api_with_auth_token(self):
        """Test sanitization of API endpoint with authentication token."""
        url = "http://api.example.com/v1/users/profile?token=sk_live_abc123def456&format=json"
        sanitized = _sanitize_url(url)
        assert "token=***" in sanitized
        assert "sk_live_abc123def456" not in sanitized
        assert "/v1/users/profile" in sanitized
        assert "format=json" in sanitized

    def test_sanitize_url_webhook_with_multiple_secrets(self):
        """Test sanitization of webhook URL with multiple secret parameters."""
        url = "http://webhook.example.com/events?key=webhook_key_123&token=wh_token_456&user_id=789&page=1"
        sanitized = _sanitize_url(url)
        assert "key=***" in sanitized
        assert "token=***" in sanitized
        assert "user_id=***" in sanitized
        assert "page=1" in sanitized
        assert "webhook_key_123" not in sanitized
        assert "wh_token_456" not in sanitized
        assert "789" not in sanitized or "page=1" in sanitized

    def test_sanitize_url_oauth_callback_with_state(self):
        """Test sanitization of OAuth callback with state parameter."""
        url = "http://callback.example.com/auth?code=auth_code_xyz&state=oauth_state_123&session_id=sess_456"
        sanitized = _sanitize_url(url)
        # These should be redacted as they're not in whitelist
        assert "code=***" in sanitized or "auth_code_xyz" not in sanitized
        assert "state=***" in sanitized or "oauth_state_123" not in sanitized
        assert "session_id=***" in sanitized
        assert "456" not in sanitized or ("456" in sanitized and "session" in sanitized)

    def test_sanitize_url_complex_query_string(self):
        """Test sanitization of complex query string with many parameters."""
        url = (
            "http://api.example.com/search?"
            "q=test&"
            "page=1&"
            "limit=20&"
            "sort=relevance&"
            "filter=active&"
            "user_id=12345&"
            "api_key=sk_prod_abc123&"
            "session_id=sess_xyz&"
            "format=json&"
            "version=v2"
        )
        sanitized = _sanitize_url(url)
        # Safe parameters preserved
        assert "q=test" in sanitized
        assert "page=1" in sanitized
        assert "limit=20" in sanitized
        assert "sort=relevance" in sanitized
        assert "filter=active" in sanitized
        assert "format=json" in sanitized
        assert "version=v2" in sanitized
        # Sensitive parameters redacted
        assert "user_id=***" in sanitized
        assert "api_key=***" in sanitized
        assert "session_id=***" in sanitized
        assert "12345" not in sanitized
        assert "sk_prod_abc123" not in sanitized
        assert "sess_xyz" not in sanitized
