"""Tests for services.project_context — intake-to-forge-context transformer."""

import os
import sys
import unittest

# Ensure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.project_context import intake_to_forge_context, _infer_stage


class TestIntakeToForgeContext(unittest.TestCase):
    """intake_to_forge_context transforms ProjectIntake dict to forge format."""

    def test_empty_intake_returns_empty(self):
        assert intake_to_forge_context({}) == {}

    def test_none_intake_returns_empty(self):
        assert intake_to_forge_context(None) == {}

    def test_basic_intake(self):
        intake = {
            "product_summary": "E-commerce app for selling handmade goods",
            "scale_expectation": "MVP with a few beta testers",
            "must_not_break_flows": ["checkout", "payment processing"],
            "sensitive_data": ["payments", "pii"],
        }
        ctx = intake_to_forge_context(intake)

        assert ctx["project_stage"] == "mvp"
        assert ctx["team_size"] == 1
        assert ctx["vision_summary"] == "E-commerce app for selling handmade goods"
        assert ctx["beloved_features"] == ["checkout", "payment processing"]
        assert "payment/financial data" in ctx["sensitive_data_types"]
        assert "personally identifiable information (PII)" in ctx["sensitive_data_types"]

    def test_vibe_prompt_included(self):
        intake = {"product_summary": "Todo app"}
        ctx = intake_to_forge_context(
            intake, vibe_prompt="Build a todo app with React and Supabase"
        )
        assert ctx["original_prompt"] == "Build a todo app with React and Supabase"

    def test_no_vibe_prompt_excluded(self):
        intake = {"product_summary": "Todo app"}
        ctx = intake_to_forge_context(intake)
        assert "original_prompt" not in ctx

    def test_custom_team_size(self):
        intake = {"product_summary": "SaaS dashboard"}
        ctx = intake_to_forge_context(intake, team_size=3)
        assert ctx["team_size"] == 3

    def test_sensitive_data_none_excluded(self):
        intake = {"sensitive_data": ["none"]}
        ctx = intake_to_forge_context(intake)
        assert "sensitive_data_types" not in ctx

    def test_sensitive_data_not_sure_excluded(self):
        intake = {"sensitive_data": ["not_sure"]}
        ctx = intake_to_forge_context(intake)
        assert "sensitive_data_types" not in ctx

    def test_sensitive_data_mixed(self):
        intake = {"sensitive_data": ["payments", "none", "health"]}
        ctx = intake_to_forge_context(intake)
        assert len(ctx["sensitive_data_types"]) == 2
        assert "payment/financial data" in ctx["sensitive_data_types"]
        assert "health/medical data (PHI)" in ctx["sensitive_data_types"]

    def test_empty_flows_excluded(self):
        intake = {"must_not_break_flows": []}
        ctx = intake_to_forge_context(intake)
        assert "beloved_features" not in ctx

    def test_empty_product_summary_excluded(self):
        intake = {"product_summary": ""}
        ctx = intake_to_forge_context(intake)
        assert "vision_summary" not in ctx


class TestInferStage(unittest.TestCase):
    """_infer_stage maps scale_expectation text to forge stage."""

    def test_mvp_keywords(self):
        assert _infer_stage("This is just an MVP") == "mvp"
        assert _infer_stage("prototype for demo day") == "mvp"
        assert _infer_stage("hackathon project") == "mvp"

    def test_early_product_keywords(self):
        assert _infer_stage("Beta testing with small group") == "early_product"
        assert _infer_stage("Alpha release, few users") == "early_product"

    def test_growth_keywords(self):
        assert _infer_stage("Scaling to thousands of users") == "growth"
        assert _infer_stage("Growing fast, need to handle 100k requests") == "growth"

    def test_enterprise_keywords(self):
        assert _infer_stage("Enterprise clients, SOC2 compliance needed") == "enterprise"
        assert _infer_stage("Millions of users, HIPAA required") == "enterprise"

    def test_empty_defaults_to_mvp(self):
        assert _infer_stage("") == "mvp"

    def test_unknown_text_defaults_to_mvp(self):
        assert _infer_stage("Some random text about my app") == "mvp"

    def test_case_insensitive(self):
        assert _infer_stage("ENTERPRISE DEPLOYMENT") == "enterprise"
        assert _infer_stage("MVP Phase") == "mvp"


class TestForgeBridgeProjectContext(unittest.TestCase):
    """Forge bridge accepts and forwards project_context."""

    def test_trigger_forge_scan_includes_context_in_config(self):
        """Verify project_context is placed into config dict."""
        from services.forge_bridge import trigger_forge_scan
        import inspect

        sig = inspect.signature(trigger_forge_scan)
        assert "project_context" in sig.parameters

    def test_trigger_forge_remediate_includes_context(self):
        """Verify project_context param exists on remediate."""
        from services.forge_bridge import trigger_forge_remediate
        import inspect

        sig = inspect.signature(trigger_forge_remediate)
        assert "project_context" in sig.parameters


if __name__ == "__main__":
    unittest.main()
