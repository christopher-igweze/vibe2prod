"""Unit tests for _compute_scores_from_discovery — v3 dimension mapping."""

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
    """Verify score computation from FORGE v3 evaluation data."""

    def test_empty_findings_no_evaluation_gives_perfect_scores(self) -> None:
        scores = _compute_scores_from_discovery({"findings": []})
        self.assertEqual(scores["health_score"], 100)
        self.assertEqual(scores["security_score"], 100)
        self.assertEqual(scores["reliability_score"], 100)
        self.assertEqual(scores["scalability_score"], 100)

    def test_no_findings_key_gives_perfect_scores(self) -> None:
        scores = _compute_scores_from_discovery({})
        self.assertEqual(scores["health_score"], 100)

    def test_v3_security_dimension(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 85,
                    "dimensions": {
                        "security": {"score": 85},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 85)
        self.assertEqual(scores["health_score"], 100)  # unset defaults to 100

    def test_v3_reliability_dimension(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 92,
                    "dimensions": {
                        "reliability": {"score": 92},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["reliability_score"], 92)

    def test_v3_maintainability_maps_to_health(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 96,
                    "dimensions": {
                        "maintainability": {"score": 96},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["health_score"], 96)

    def test_v3_performance_maps_to_scalability(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 99,
                    "dimensions": {
                        "performance": {"score": 99},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["scalability_score"], 99)

    def test_v3_zero_scores_preserved(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 0,
                    "dimensions": {
                        "security": {"score": 0},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 0)

    def test_v3_all_dimensions(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 70,
                    "dimensions": {
                        "security": {"score": 85},
                        "maintainability": {"score": 92},
                        "reliability": {"score": 96},
                        "performance": {"score": 99},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 85)
        self.assertEqual(scores["health_score"], 92)
        self.assertEqual(scores["reliability_score"], 96)
        self.assertEqual(scores["scalability_score"], 99)

    def test_no_evaluation_returns_all_100(self) -> None:
        """Without v3 evaluation, all scores default to 100."""
        report = {
            "findings": [
                {"severity": "critical", "category": "security"},
            ],
        }
        scores = _compute_scores_from_discovery(report)
        # v3: findings alone don't deduct — need evaluation data
        self.assertEqual(scores["security_score"], 100)


if __name__ == "__main__":
    unittest.main()
