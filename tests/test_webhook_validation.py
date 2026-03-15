"""Tests for webhook endpoint validation error handling.

These tests verify that the GitHub webhook endpoint properly validates
incoming requests and handles malformed payloads gracefully.

Test Location: tests/test_webhook_validation.py
Project: backend/api/routes/webhook.py
Framework: pytest
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, Request

# Import webhook router - try multiple import paths to handle different project layouts
try:
    from backend.api.routes.webhook import github_webhook
except ImportError:
    try:
        from api.routes.webhook import github_webhook
    except ImportError:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent / "backend"
        if backend_path.exists():
            sys.path.insert(0, str(backend_path.parent))
            from api.routes.webhook import github_webhook
        else:
            raise ImportError("Could not import github_webhook from any known path")


class TestGitHubWebhookValidation:
    """Test suite for GitHub webhook validation and error handling."""

    @pytest.mark.asyncio
    async def test_webhook_empty_body_returns_400(self):
        """Test that empty request body returns 400 Bad Request."""
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"x-hub-signature-256": "sha256=test"}
        mock_request.body = AsyncMock(return_value=b"")

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request)

        assert exc_info.value.status_code == 400
        # Verify the error detail contains the expected code
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("code") == "body_empty"
        assert "empty" in detail.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_webhook_missing_signature_header(self):
        """Test that missing signature header returns 401 Unauthorized."""
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {}  # Missing x-hub-signature-256
        mock_request.body = AsyncMock(return_value=b'{"action": "opened"}')

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request)

        # Should raise HTTPException for missing signature
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self):
        """Test that invalid webhook signature returns 401 Unauthorized."""
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"x-hub-signature-256": "sha256=invalidsignature"}
        mock_request.body = AsyncMock(return_value=b'{"action": "opened"}')

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_webhook_empty_body_before_signature_check(self):
        """Test that empty body validation happens before signature verification."""
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"x-hub-signature-256": "sha256=anysignature"}
        mock_request.body = AsyncMock(return_value=b"")

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request)

        # Should fail with 400 (empty body) not 401 (signature)
        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail.get("code") == "body_empty"

    @pytest.mark.asyncio
    async def test_webhook_valid_body_structure_but_invalid_signature(self):
        """Test that valid JSON body with invalid signature raises 401."""
        mock_request = AsyncMock(spec=Request)
        mock_request.headers = {"x-hub-signature-256": "sha256=wrongsignature"}
        mock_request.body = AsyncMock(return_value=b'{"action": "opened", "pull_request": {}}')

        with pytest.raises(HTTPException) as exc_info:
            await github_webhook(mock_request)

        # Should fail signature verification, not body validation
        assert exc_info.value.status_code == 401
