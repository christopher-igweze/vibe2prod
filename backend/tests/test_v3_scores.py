"""Tests for v3 evaluation-based score computation."""

from __future__ import annotations

import os
import sys
import types
import importlib.util
import unittest

os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("DAYTONA_API_KEY", "test")

# Pre-register package stubs so importing health_repository doesn't trigger
# the repositories __init__.py (which eagerly imports every repo module and
# may hang in dev environments due to transitive dependency resolution).
_backend = os.path.join(os.path.dirname(__file__), os.pardir)

for _pkg in ("services", "services.repositories"):
    if _pkg not in sys.modules:
        sys.modules[_pkg] = types.ModuleType(_pkg)

if "services.repositories._base" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "services.repositories._base",
        os.path.join(_backend, "services", "repositories", "_base.py"),
    )
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["services.repositories._base"] = _mod
    _spec.loader.exec_module(_mod)

if "services.repositories.health_repository" not in sys.modules:
    _spec2 = importlib.util.spec_from_file_location(
        "services.repositories.health_repository",
        os.path.join(_backend, "services", "repositories", "health_repository.py"),
    )
    _mod2 = importlib.util.module_from_spec(_spec2)
    sys.modules["services.repositories.health_repository"] = _mod2
    _spec2.loader.exec_module(_mod2)

# Pre-register scan_repository so @patch can resolve the module path.
if "services.repositories.scan_repository" not in sys.modules:
    # Need models.scan and models.findings stubs for scan_repository imports
    for _stub in ("models", "models.scan", "models.findings"):
        if _stub not in sys.modules:
            sys.modules[_stub] = types.ModuleType(_stub)

    # Provide ScanStatus on the stub
    from enum import Enum

    class _ScanStatus(str, Enum):
        pending = "pending"
        scanning = "scanning"
        completed = "completed"
        failed = "failed"

    sys.modules["models.scan"].ScanStatus = _ScanStatus

    # Provide AuditReport stub
    sys.modules["models.findings"].AuditReport = type("AuditReport", (), {})

    _spec3 = importlib.util.spec_from_file_location(
        "services.repositories.scan_repository",
        os.path.join(_backend, "services", "repositories", "scan_repository.py"),
    )
    _mod3 = importlib.util.module_from_spec(_spec3)
    sys.modules["services.repositories.scan_repository"] = _mod3
    # Attach to the parent package so @patch resolves correctly
    sys.modules["services.repositories"].scan_repository = _mod3
    _spec3.loader.exec_module(_mod3)

from services.repositories.health_repository import _compute_scores_from_discovery


class ComputeScoresV3Tests(unittest.TestCase):
    """v3 evaluation dimension scores are the source of truth."""

    def test_maps_v3_dimensions_to_frontend_scores(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 67,
                    "dimensions": {
                        "security": {"score": 72},
                        "reliability": {"score": 55},
                        "maintainability": {"score": 80},
                        "performance": {"score": 65},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 72)
        self.assertEqual(scores["reliability_score"], 55)
        self.assertEqual(scores["health_score"], 80)
        self.assertEqual(scores["scalability_score"], 65)

    def test_missing_dimensions_default_to_100(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 90,
                    "dimensions": {
                        "security": {"score": 85},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 85)
        self.assertEqual(scores["reliability_score"], 100)
        self.assertEqual(scores["health_score"], 100)
        self.assertEqual(scores["scalability_score"], 100)

    def test_zero_scores_preserved(self) -> None:
        report = {
            "findings": [],
            "evaluation": {
                "scores": {
                    "composite": 10,
                    "dimensions": {
                        "security": {"score": 0},
                        "reliability": {"score": 0},
                        "maintainability": {"score": 0},
                        "performance": {"score": 0},
                    },
                },
            },
        }
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 0)
        self.assertEqual(scores["health_score"], 0)

    def test_no_evaluation_returns_all_100(self) -> None:
        """Without v3 evaluation data, default to 100 (no findings to deduct)."""
        report = {"findings": []}
        scores = _compute_scores_from_discovery(report)
        self.assertEqual(scores["security_score"], 100)
        self.assertEqual(scores["reliability_score"], 100)


from unittest.mock import patch, MagicMock


class ScanStorageV3Tests(unittest.TestCase):
    """v3 evaluation and aivss data stored in report_data JSONB."""

    @patch("services.repositories.scan_repository._client")
    def test_evaluation_stored_in_report_data(self, mock_client_fn: MagicMock) -> None:
        import asyncio
        from uuid import uuid4
        from services.repositories.scan_repository import update_scan_with_discovery

        mock_table = MagicMock()
        mock_client_fn.return_value.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        scan_id = uuid4()
        discovery = {"findings": []}
        evaluation = {"scores": {"composite": 67, "dimensions": {"security": {"score": 72}}}}
        aivss = {"score": 6.2, "severity": "Medium"}

        asyncio.run(update_scan_with_discovery(scan_id, discovery, evaluation=evaluation, aivss_score=aivss))

        call_args = mock_table.update.call_args[0][0]
        self.assertEqual(call_args["report_data"]["evaluation"], evaluation)
        self.assertEqual(call_args["report_data"]["aivss_score"], aivss)
        self.assertEqual(call_args["report_data"]["discovery_report"], discovery)

    @patch("services.repositories.scan_repository._client")
    def test_no_evaluation_stores_discovery_only(self, mock_client_fn: MagicMock) -> None:
        import asyncio
        from uuid import uuid4
        from services.repositories.scan_repository import update_scan_with_discovery

        mock_table = MagicMock()
        mock_client_fn.return_value.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])

        scan_id = uuid4()
        discovery = {"findings": []}

        asyncio.run(update_scan_with_discovery(scan_id, discovery))

        call_args = mock_table.update.call_args[0][0]
        self.assertNotIn("evaluation", call_args["report_data"])
        self.assertEqual(call_args["report_data"]["discovery_report"], discovery)


if __name__ == "__main__":
    unittest.main()
