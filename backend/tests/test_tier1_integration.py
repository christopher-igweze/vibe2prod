"""Integration tests for Tier 1 project context + actionability pipeline.

Tests that _build_forge_context, actionability classification, and
reporter grouping work together end-to-end.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tier1.contracts import Tier1Evidence, Tier1Finding
from tier1.reporter import Tier1Reporter


def _finding(**kwargs) -> Tier1Finding:
    defaults = {
        "check_id": "SEC-001",
        "status": "fail",
        "category": "security",
        "severity": "high",
        "engine": "regex",
        "confidence": 0.9,
        "title": "Test finding",
        "description": "Test description",
        "suggested_fix_stub": "Fix it",
        "evidence": [
            Tier1Evidence(
                file_path="src/main.py",
                line_number=10,
                snippet="secret = 'abc'",
                match="secret",
            )
        ],
    }
    defaults.update(kwargs)
    return Tier1Finding(**defaults)


class TestOrchestratorBuildForgeContext(unittest.TestCase):
    """_build_forge_context transforms project_intake to forge context."""

    def _make_orchestrator(self, intake):
        """Create a Tier1Orchestrator with mocked dependencies."""
        from unittest.mock import MagicMock
        from tier1.orchestrator import Tier1Orchestrator

        orch = Tier1Orchestrator.__new__(Tier1Orchestrator)
        orch.project_intake = intake
        orch.log = MagicMock()
        return orch

    def test_builds_context_from_intake(self):
        intake = {
            "product_summary": "E-commerce app",
            "scale_expectation": "Growing fast to 100k users",
            "must_not_break_flows": ["checkout"],
            "sensitive_data": ["payments"],
        }
        orch = self._make_orchestrator(intake)
        ctx = orch._build_forge_context()

        assert ctx["project_stage"] == "growth"
        assert ctx["vision_summary"] == "E-commerce app"
        assert ctx["beloved_features"] == ["checkout"]
        assert "payment/financial data" in ctx["sensitive_data_types"]

    def test_empty_intake_returns_empty_dict(self):
        orch = self._make_orchestrator({})
        ctx = orch._build_forge_context()
        assert ctx == {}

    def test_none_intake_returns_empty_dict(self):
        orch = self._make_orchestrator(None)
        ctx = orch._build_forge_context()
        assert ctx == {}

    def test_missing_intake_attr_returns_empty_dict(self):
        """If project_intake attribute doesn't exist, should not crash."""
        from unittest.mock import MagicMock
        from tier1.orchestrator import Tier1Orchestrator

        orch = Tier1Orchestrator.__new__(Tier1Orchestrator)
        orch.log = MagicMock()
        # Don't set project_intake at all
        if hasattr(orch, "project_intake"):
            delattr(orch, "project_intake")
        ctx = orch._build_forge_context()
        assert ctx == {}


class TestReporterGroupByActionability(unittest.TestCase):
    """_group_by_actionability groups findings in tier order."""

    def test_groups_by_tier(self):
        findings = [
            _finding(actionability="should_fix", check_id="A"),
            _finding(actionability="must_fix", check_id="B"),
            _finding(actionability="informational", check_id="C"),
            _finding(actionability="consider", check_id="D"),
        ]
        groups = Tier1Reporter._group_by_actionability(findings)
        tier_names = [name for name, _ in groups]

        assert "Must Fix" in tier_names[0]
        assert "Should Fix" in tier_names[1]
        assert "Consider" in tier_names[2]
        assert "Informational" in tier_names[3]

    def test_skips_empty_tiers(self):
        findings = [
            _finding(actionability="must_fix"),
            _finding(actionability="informational"),
        ]
        groups = Tier1Reporter._group_by_actionability(findings)
        assert len(groups) == 2
        tier_names = [name for name, _ in groups]
        assert any("Must Fix" in n for n in tier_names)
        assert any("Informational" in n for n in tier_names)

    def test_empty_findings_returns_empty(self):
        groups = Tier1Reporter._group_by_actionability([])
        assert groups == []

    def test_unset_actionability_defaults_to_should_fix(self):
        """Findings with empty actionability go to should_fix bucket."""
        findings = [_finding(actionability="")]
        groups = Tier1Reporter._group_by_actionability(findings)
        assert len(groups) == 1
        assert "Should Fix" in groups[0][0]

    def test_preserves_finding_order_within_tier(self):
        findings = [
            _finding(actionability="must_fix", check_id="FIRST"),
            _finding(actionability="must_fix", check_id="SECOND"),
        ]
        groups = Tier1Reporter._group_by_actionability(findings)
        tier_findings = groups[0][1]
        assert tier_findings[0].check_id == "FIRST"
        assert tier_findings[1].check_id == "SECOND"


class TestActionabilityInSummaryJson(unittest.IsolatedAsyncioTestCase):
    """summary_json includes by_actionability counts."""

    async def test_by_actionability_in_summary(self):
        from unittest.mock import AsyncMock

        reporter = Tier1Reporter()
        findings = [
            _finding(actionability="must_fix", check_id="A", severity="critical"),
            _finding(actionability="should_fix", check_id="B", severity="high"),
            _finding(actionability="should_fix", check_id="C", severity="medium"),
        ]
        with unittest.mock.patch.object(
            reporter,
            "_generate_assistant_context",
            new=AsyncMock(return_value=({}, None)),
        ):
            artifact = await reporter.generate_report(
                findings=findings,
                score_summary={
                    "health_score": 70,
                    "security_score": 50,
                    "reliability_score": 80,
                    "scalability_score": 90,
                },
                intake_context={"product_summary": "Test", "target_users": "devs"},
                run_details={"scan_id": "test-1", "total_before_report_ms": 10},
                git_metadata={},
            )

        counts = artifact.summary_json["counts"]
        assert counts["by_actionability"]["must_fix"] == 1
        assert counts["by_actionability"]["should_fix"] == 2


if __name__ == "__main__":
    unittest.main()
