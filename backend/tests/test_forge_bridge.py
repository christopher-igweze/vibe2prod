"""Unit tests for services/forge_bridge.py — FORGE HTTP bridge."""

from __future__ import annotations

import asyncio
import os
import unittest
import urllib.error
from unittest.mock import patch, MagicMock, AsyncMock

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")

from services.forge_bridge import (
    ForgeRunResult,
    trigger_forge_scan,
    trigger_forge_remediate,
    _parse_forge_result,
    _extract_readiness_score,
)


class ParseForgeResultTests(unittest.TestCase):
    """Tests for _parse_forge_result — pure function, no mocking."""

    def test_successful_completed_result(self) -> None:
        raw = {
            "status": "completed",
            "output": {
                "forge_run_id": "run-123",
                "success": True,
                "summary": "Fixed 3 findings",
                "total_findings": 5,
                "findings_fixed": 3,
                "findings_deferred": 2,
                "pr_url": "https://github.com/user/repo/pull/1",
                "readiness_report": {"overall_score": 78},
            },
        }
        result = _parse_forge_result("exec-abc", raw)

        self.assertEqual(result.execution_id, "exec-abc")
        self.assertEqual(result.forge_run_id, "run-123")
        self.assertTrue(result.success)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.total_findings, 5)
        self.assertEqual(result.findings_fixed, 3)
        self.assertEqual(result.findings_deferred, 2)
        self.assertEqual(result.readiness_score, 78)
        self.assertEqual(result.pr_url, "https://github.com/user/repo/pull/1")

    def test_failed_result(self) -> None:
        raw = {
            "status": "failed",
            "error": "Agent timeout",
            "output": {},
        }
        result = _parse_forge_result("exec-fail", raw)

        self.assertEqual(result.status, "failed")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Agent timeout")

    def test_timeout_result(self) -> None:
        raw = {"status": "timeout", "error": "Timed out after 2700s"}
        result = _parse_forge_result("exec-timeout", raw)

        self.assertEqual(result.status, "timeout")
        self.assertFalse(result.success)
        self.assertIn("2700", result.error)

    def test_missing_output_uses_result_fallback(self) -> None:
        raw = {
            "status": "completed",
            "result": {"forge_run_id": "run-fallback", "success": True},
        }
        result = _parse_forge_result("exec-fb", raw)
        self.assertEqual(result.forge_run_id, "run-fallback")
        self.assertTrue(result.success)

    def test_non_dict_output_handled(self) -> None:
        raw = {"status": "completed", "output": "unexpected string"}
        result = _parse_forge_result("exec-bad", raw)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.forge_run_id, "")

    def test_readiness_score_without_report(self) -> None:
        raw = {"status": "completed", "output": {"success": True}}
        result = _parse_forge_result("exec-no-score", raw)
        self.assertEqual(result.readiness_score, 0)


class ExtractReadinessScoreTests(unittest.TestCase):
    """Tests for _extract_readiness_score helper."""

    def test_extracts_from_report(self) -> None:
        output = {"readiness_report": {"overall_score": 85}}
        self.assertEqual(_extract_readiness_score(output), 85)

    def test_returns_zero_when_no_report(self) -> None:
        self.assertEqual(_extract_readiness_score({}), 0)

    def test_returns_zero_when_report_not_dict(self) -> None:
        self.assertEqual(_extract_readiness_score({"readiness_report": "bad"}), 0)


class TriggerForgeScanTests(unittest.TestCase):
    """Tests for trigger_forge_scan with mocked HTTP."""

    def test_posts_correct_payload(self) -> None:
        mock_post = MagicMock(return_value={"execution_id": "exec-1"})
        mock_get = MagicMock(return_value={
            "status": "completed",
            "output": {"forge_run_id": "run-1", "success": True},
        })

        with patch("services.forge_bridge._http_post", mock_post), \
             patch("services.forge_bridge._http_get", mock_get), \
             patch("services.forge_bridge.asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(trigger_forge_scan(
                repo_url="https://github.com/user/repo",
                agentfield_url_override="http://test:8080",
                timeout=10,
            ))

        self.assertTrue(result.success)
        call_args = mock_post.call_args
        self.assertIn(".scan", call_args[0][0])
        payload = call_args[0][1]
        self.assertEqual(payload["input"]["repo_url"], "https://github.com/user/repo")
        self.assertEqual(payload["input"]["config"]["mode"], "discovery")
        self.assertTrue(payload["input"]["config"]["dry_run"])

    def test_http_failure_returns_error(self) -> None:
        mock_post = MagicMock(side_effect=urllib.error.URLError("Connection refused"))

        with patch("services.forge_bridge._http_post", mock_post):
            result = asyncio.run(trigger_forge_scan(
                repo_url="https://github.com/user/repo",
                agentfield_url_override="http://test:8080",
            ))

        self.assertFalse(result.success)
        self.assertEqual(result.status, "error")
        self.assertIn("Failed to trigger FORGE", result.error)

    def test_no_execution_id_returns_error(self) -> None:
        mock_post = MagicMock(return_value={"message": "ok but no id"})

        with patch("services.forge_bridge._http_post", mock_post):
            result = asyncio.run(trigger_forge_scan(
                repo_url="https://github.com/user/repo",
                agentfield_url_override="http://test:8080",
            ))

        self.assertFalse(result.success)
        self.assertEqual(result.status, "error")
        self.assertIn("No execution_id", result.error)


class TriggerForgeRemediateTests(unittest.TestCase):
    """Tests for trigger_forge_remediate with mocked HTTP."""

    def test_includes_tier1_findings(self) -> None:
        mock_post = MagicMock(return_value={"execution_id": "exec-2"})
        mock_get = MagicMock(return_value={
            "status": "completed",
            "output": {
                "forge_run_id": "run-2",
                "success": True,
                "findings_fixed": 2,
            },
        })
        findings = [{"title": "No auth", "severity": "critical"}]

        with patch("services.forge_bridge._http_post", mock_post), \
             patch("services.forge_bridge._http_get", mock_get), \
             patch("services.forge_bridge.asyncio.sleep", new=AsyncMock()):
            result = asyncio.run(trigger_forge_remediate(
                repo_url="https://github.com/user/repo",
                tier1_findings=findings,
                agentfield_url_override="http://test:8080",
                timeout=10,
            ))

        self.assertTrue(result.success)
        self.assertEqual(result.findings_fixed, 2)
        payload = mock_post.call_args[0][1]
        self.assertEqual(payload["input"]["tier1_findings"], findings)

    def test_mode_defaults_to_full(self) -> None:
        mock_post = MagicMock(return_value={"execution_id": "exec-3"})
        mock_get = MagicMock(return_value={
            "status": "completed",
            "output": {"success": True},
        })

        with patch("services.forge_bridge._http_post", mock_post), \
             patch("services.forge_bridge._http_get", mock_get), \
             patch("services.forge_bridge.asyncio.sleep", new=AsyncMock()):
            asyncio.run(trigger_forge_remediate(
                repo_url="https://github.com/user/repo",
                agentfield_url_override="http://test:8080",
                timeout=10,
            ))

        payload = mock_post.call_args[0][1]
        self.assertEqual(payload["input"]["config"]["mode"], "full")


if __name__ == "__main__":
    unittest.main()
