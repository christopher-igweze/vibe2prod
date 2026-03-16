"""Tests for probe_bridge -- HTTP client to Security Probe Service."""
import asyncio
import os
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")

import pytest
from unittest.mock import patch, AsyncMock
from services.probe_bridge import ProbeBridge, ProbeServiceResult


class TestProbeBridge:
    @pytest.fixture
    def bridge(self):
        return ProbeBridge(
            service_url="http://probe-service:8080",
            api_key="test-key",
        )

    def test_trigger_scan_success(self, bridge):
        mock_response = {"job_id": "abc-123", "status": "queued"}
        with patch.object(bridge, "_post", new_callable=AsyncMock, return_value=mock_response):
            result = asyncio.get_event_loop().run_until_complete(
                bridge.trigger_scan("https://example.com", {})
            )
            assert result.job_id == "abc-123"
            assert result.status == "queued"

    def test_trigger_scan_connection_error(self, bridge):
        with patch.object(bridge, "_post", new_callable=AsyncMock, side_effect=ConnectionError("refused")):
            result = asyncio.get_event_loop().run_until_complete(
                bridge.trigger_scan("https://example.com", {})
            )
            assert result.status == "error"
            assert "refused" in result.error

    def test_get_status(self, bridge):
        mock_response = {"job_id": "abc-123", "status": "running", "current_phase": 2, "progress": 35, "findings_so_far": 3}
        with patch.object(bridge, "_get", new_callable=AsyncMock, return_value=mock_response):
            result = asyncio.get_event_loop().run_until_complete(
                bridge.get_status("abc-123")
            )
            assert result["status"] == "running"
            assert result["progress"] == 35

    def test_get_results(self, bridge):
        mock_response = {
            "job_id": "abc-123", "status": "completed", "target_url": "https://example.com",
            "total_findings": 5, "findings": [{"title": "XSS", "severity": "high"}],
            "probe_score": 75, "duration_seconds": 120.0,
        }
        with patch.object(bridge, "_get", new_callable=AsyncMock, return_value=mock_response):
            result = asyncio.get_event_loop().run_until_complete(
                bridge.get_results("abc-123")
            )
            assert result["total_findings"] == 5
            assert result["probe_score"] == 75
