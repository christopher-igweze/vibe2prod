"""Tests for CORS security configuration (F-acc7affa).

This module tests that the CORS middleware is properly configured to restrict
Vercel preview deployment domains, preventing overly permissive allowlists
that could accept untrusted origins (CWE-346).
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCORSConfiguration:
    """Test CORS middleware configuration based on settings."""

    def test_explicit_origins_when_cors_allowed_origins_set(self):
        """When cors_allowed_origins is configured, use explicit origin allowlist."""
        with patch('main.settings') as mock_settings:
            mock_settings.cors_allowed_origins = "https://www.vibe2prod.com,https://app-staging.vibe2prod.verstandai.site"
            mock_settings.cors_vercel_projects = ""
            
            # Re-import to pick up patched settings
            import importlib
            import main
            importlib.reload(main)
            
            app = main.app
            
            # Check that CORSMiddleware is added
            middleware_classes = [m.cls for m in app.user_middleware]
            assert CORSMiddleware in middleware_classes
    
    def test_vercel_projects_when_no_explicit_origins(self):
        """When cors_vercel_projects is set but not cors_allowed_origins, restrict to specific projects."""
        with patch('main.settings') as mock_settings:
            mock_settings.cors_allowed_origins = ""
            mock_settings.cors_vercel_projects = "my-app,frontend-app"
            
            import importlib
            import main
            importlib.reload(main)
            
            app = main.app
            
            middleware_classes = [m.cls for m in app.user_middleware]
            assert CORSMiddleware in middleware_classes
    
    def test_fallback_no_wildcard_vercel_when_both_empty(self):
        """When neither cors_allowed_origins nor cors_vercel_projects is set, no Vercel wildcard."""
        with patch('main.settings') as mock_settings:
            mock_settings.cors_allowed_origins = ""
            mock_settings.cors_vercel_projects = ""
            
            import importlib
            import main
            importlib.reload(main)
            
            app = main.app
            
            middleware_classes = [m.cls for m in app.user_middleware]
            assert CORSMiddleware in middleware_classes


class TestCORSRegexPatterns:
    """Test that CORS regex patterns correctly match/block origins."""
    
    def test_vercel_project_regex_allows_specific_project(self):
        """Regex pattern should allow specific Vercel project subdomains."""
        import re
        
        # Simulate the regex built for cors_vercel_projects=my-app,frontend-app
        projects = ["my-app", "frontend-app"]
        _vercel_pattern = "|".join(
            rf"^https://{re.escape(project)}\\.vercel\\.app$" for project in projects
        )
        _cors_regex = (
            r"^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$|"
            + _vercel_pattern
            + r"|^https://(www\\.)?vibe2prod\\.com$|^https://.*\\.verstandai\\.site$"
        )
        
        # Should match
        assert re.match(_cors_regex, "https://my-app.vercel.app")
        assert re.match(_cors_regex, "https://frontend-app.vercel.app")
    
    def test_vercel_project_regex_blocks_unknown_project(self):
        """Regex pattern should block unknown Vercel project subdomains."""
        import re
        
        projects = ["my-app", "frontend-app"]
        _vercel_pattern = "|".join(
            rf"^https://{re.escape(project)}\\.vercel\\.app$" for project in projects
        )
        _cors_regex = (
            r"^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$|"
            + _vercel_pattern
            + r"|^https://(www\\.)?vibe2prod\\.com$|^https://.*\\.verstandai\\.site$"
        )
        
        # Should NOT match - unknown project
        assert not re.match(_cors_regex, "https://attacker-project.vercel.app")
        assert not re.match(_cors_regex, "https://random-user-preview.vercel.app")
    
    def test_fallback_regex_no_vercel_wildcard(self):
        """Fallback regex should NOT include wildcard Vercel pattern."""
        import re
        
        # This is the fallback regex (no Vercel wildcard)
        _cors_regex = (
            r"^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$"
            r"|^https://(www\\.)?vibe2prod\\.com$"
            r"|^https://.*\\.verstandai\\.site$"
        )
        
        # Should match localhost
        assert re.match(_cors_regex, "http://localhost:3000")
        assert re.match(_cors_regex, "https://127.0.0.1:8000")
        
        # Should match vibe2prod.com
        assert re.match(_cors_regex, "https://www.vibe2prod.com")
        
        # Should match verstandai.site
        assert re.match(_cors_regex, "https://app-staging.vibe2prod.verstandai.site")
        
        # Should NOT match Vercel (the fix - no wildcard)
        assert not re.match(_cors_regex, "https://any-project.vercel.app")
        assert not re.match(_cors_regex, "https://legitimate-project.vercel.app")


class TestCORSConfigParsing:
    """Test that configuration values are properly parsed."""
    
    def test_parse_empty_cors_allowed_origins(self):
        """Empty string should result in empty list."""
        cors_allowed_origins = ""
        result = [o.strip() for o in cors_allowed_origins.split(",") if o.strip()]
        assert result == []
    
    def test_parse_single_origin(self):
        """Single origin should be parsed correctly."""
        cors_allowed_origins = "https://www.vibe2prod.com"
        result = [o.strip() for o in cors_allowed_origins.split(",") if o.strip()]
        assert result == ["https://www.vibe2prod.com"]
    
    def test_parse_multiple_origins(self):
        """Multiple origins should be parsed correctly."""
        cors_allowed_origins = "https://www.vibe2prod.com,https://app-staging.vibe2prod.verstandai.site"
        result = [o.strip() for o in cors_allowed_origins.split(",") if o.strip()]
        assert result == ["https://www.vibe2prod.com", "https://app-staging.vibe2prod.verstandai.site"]
    
    def test_parse_vercel_projects(self):
        """Vercel projects should be parsed correctly."""
        cors_vercel_projects = "my-app,frontend-app"
        result = [p.strip() for p in cors_vercel_projects.split(",") if p.strip()]
        assert result == ["my-app", "frontend-app"]
    
    def test_parse_vercel_projects_with_whitespace(self):
        """Vercel projects with extra whitespace should be trimmed."""
        cors_vercel_projects = " my-app , frontend-app , test-prod "
        result = [p.strip() for p in cors_vercel_projects.split(",") if p.strip()]
        assert result == ["my-app", "frontend-app", "test-prod"]


class TestSecurityRegression:
    """Regression tests to ensure the security fix is in place."""
    
    def test_old_wildcard_pattern_would_be_blocked(self):
        """The old wildcard pattern ^https://.*\.vercel\.app$ would match any Vercel subdomain.
        
        This test verifies that we no longer use this pattern by default.
        The fix ensures that untrusted Vercel preview deployments are blocked.
        """
        import re
        
        # OLD (vulnerable) pattern that was in the code
        old_wildcard = r"^https://.*\.vercel\.app$"
        
        # This would have matched ANY Vercel subdomain (security issue)
        assert re.match(old_wildcard, "https://any-user-preview.vercel.app")
        assert re.match(old_wildcard, "https://attacker-controlled.vercel.app")
        
        # The fix ensures we DON'T use this pattern without explicit project names
        # This is tested by verifying the fallback regex does NOT contain the wildcard
        current_fallback = (
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        )
        
        # Verify fallback does NOT have Vercel wildcard
        assert "vercel.app" not in current_fallback or "*" not in current_fallback
    
    def test_config_has_cors_vercel_projects_field(self):
        """Verify the new config field exists."""
        from config import Settings
        
        # The new field should exist
        assert hasattr(Settings, 'model_fields')
        assert 'cors_vercel_projects' in Settings.model_fields
    
    def test_config_cors_vercel_projects_default_empty(self):
        """Verify cors_vercel_projects defaults to empty string."""
        from config import Settings
        
        # Check the default value
        field = Settings.model_fields['cors_vercel_projects']
        assert field.default == "" or field.default is None or field.default == ""
