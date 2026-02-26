"""Tests for tier1.actionability — Tier 1 finding actionability classifier."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tier1.actionability import (
    classify_tier1_actionability,
    apply_tier1_actionability,
)
from tier1.contracts import Tier1Finding


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
    }
    defaults.update(kwargs)
    return Tier1Finding(**defaults)


class TestClassifyTier1Actionability(unittest.TestCase):
    """classify_tier1_actionability returns correct tiers."""

    def test_pass_status_always_informational(self):
        f = _finding(status="pass", severity="critical", confidence=0.95)
        assert classify_tier1_actionability(f) == "informational"

    def test_critical_high_confidence_must_fix(self):
        f = _finding(severity="critical", confidence=0.9)
        assert classify_tier1_actionability(f) == "must_fix"

    def test_critical_low_confidence_should_fix(self):
        f = _finding(severity="critical", confidence=0.75)
        assert classify_tier1_actionability(f) == "should_fix"

    def test_high_growth_stage_must_fix(self):
        f = _finding(severity="high", confidence=0.85)
        ctx = {"project_stage": "growth"}
        assert classify_tier1_actionability(f, ctx) == "must_fix"

    def test_high_mvp_stage_should_fix(self):
        f = _finding(severity="high", confidence=0.85)
        ctx = {"project_stage": "mvp"}
        assert classify_tier1_actionability(f, ctx) == "should_fix"

    def test_medium_mvp_low_confidence_consider(self):
        f = _finding(severity="medium", confidence=0.6)
        ctx = {"project_stage": "mvp"}
        assert classify_tier1_actionability(f, ctx) == "consider"

    def test_low_severity_informational(self):
        f = _finding(severity="low", confidence=0.8)
        assert classify_tier1_actionability(f) == "informational"

    def test_known_compromise_match_informational(self):
        f = _finding(
            title="Missing rate limiting",
            description="No rate limiting on API endpoints",
        )
        ctx = {"known_compromises": ["rate limiting"]}
        assert classify_tier1_actionability(f, ctx) == "informational"

    def test_no_context_defaults(self):
        f = _finding(severity="medium", confidence=0.8)
        assert classify_tier1_actionability(f) == "should_fix"

    def test_works_with_dict(self):
        f = {
            "severity": "critical",
            "confidence": 0.95,
            "status": "fail",
            "category": "security",
            "title": "SQL injection",
            "description": "Found SQL injection",
        }
        assert classify_tier1_actionability(f) == "must_fix"


class TestApplyTier1Actionability(unittest.TestCase):
    """apply_tier1_actionability mutates findings in-place."""

    def test_sets_actionability_on_pydantic_models(self):
        findings = [
            _finding(severity="critical", confidence=0.95),
            _finding(severity="low", confidence=0.8),
        ]
        result = apply_tier1_actionability(findings)
        assert result[0].actionability == "must_fix"
        assert result[1].actionability == "informational"
        assert result is findings  # same list returned

    def test_sets_actionability_on_dicts(self):
        findings = [
            {"severity": "high", "confidence": 0.85, "status": "fail",
             "category": "security", "title": "t", "description": "d"},
        ]
        apply_tier1_actionability(findings)
        assert findings[0]["actionability"] == "should_fix"

    def test_with_project_context(self):
        findings = [
            _finding(severity="high", confidence=0.85),
        ]
        ctx = {"project_stage": "enterprise"}
        apply_tier1_actionability(findings, ctx)
        assert findings[0].actionability == "must_fix"

    def test_empty_list(self):
        result = apply_tier1_actionability([])
        assert result == []


class TestContractsFields(unittest.TestCase):
    """Tier1Finding has actionability and data_flow fields."""

    def test_actionability_defaults_empty(self):
        f = _finding()
        assert f.actionability == ""

    def test_data_flow_defaults_empty(self):
        f = _finding()
        assert f.data_flow == ""

    def test_actionability_roundtrip(self):
        f = _finding(actionability="must_fix", data_flow="input -> query -> db")
        assert f.actionability == "must_fix"
        assert f.data_flow == "input -> query -> db"
        d = f.model_dump()
        assert d["actionability"] == "must_fix"
        assert d["data_flow"] == "input -> query -> db"


if __name__ == "__main__":
    unittest.main()
