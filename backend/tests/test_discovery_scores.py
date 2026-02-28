"""Unit tests for _compute_scores_from_discovery — pure function, no DB."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")

from services.supabase_client import _compute_scores_from_discovery


class ComputeScoresTests(unittest.TestCase):
    """Verify score computation from FORGE discovery reports."""

    def test_empty_findings_gives_perfect_scores(self) -> None:
        scores = _compute_scores_from_discovery({"findings": []})
        self.assertEqual(scores["health_score"], 100)
        self.assertEqual(scores["security_score"], 100)
        self.assertEqual(scores["reliability_score"], 100)
        self.assertEqual(scores["scalability_score"], 100)

    def test_no_findings_key_gives_perfect_scores(self) -> None:
        scores = _compute_scores_from_discovery({})
        self.assertEqual(scores["health_score"], 100)

    def test_critical_security_deducts_15(self) -> None:
        report = {"findings": [
            {"severity": "critical", "category": "security"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 85)
        self.assertEqual(scores["health_score"], 100)  # unaffected

    def test_high_reliability_deducts_8(self) -> None:
        report = {"findings": [
            {"severity": "high", "category": "reliability"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["reliability_score"], 92)

    def test_quality_maps_to_health(self) -> None:
        report = {"findings": [
            {"severity": "medium", "category": "quality"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["health_score"], 96)

    def test_architecture_maps_to_health(self) -> None:
        report = {"findings": [
            {"severity": "medium", "category": "architecture"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["health_score"], 96)

    def test_performance_maps_to_scalability(self) -> None:
        report = {"findings": [
            {"severity": "low", "category": "performance"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["scalability_score"], 99)

    def test_scores_floor_at_zero(self) -> None:
        report = {"findings": [
            {"severity": "critical", "category": "security"},
        ] * 10}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 0)  # 100 - 150 = clamped to 0

    def test_multiple_categories(self) -> None:
        report = {"findings": [
            {"severity": "critical", "category": "security"},
            {"severity": "high", "category": "quality"},
            {"severity": "medium", "category": "reliability"},
            {"severity": "low", "category": "performance"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 85)
        self.assertEqual(scores["health_score"], 92)
        self.assertEqual(scores["reliability_score"], 96)
        self.assertEqual(scores["scalability_score"], 99)

    def test_info_severity_no_deduction(self) -> None:
        report = {"findings": [
            {"severity": "info", "category": "security"},
        ]}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 100)


if __name__ == "__main__":
    unittest.main()
