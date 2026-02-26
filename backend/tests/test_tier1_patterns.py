"""Unit tests for Tier 1 vendored pattern library and signal evaluation."""

from __future__ import annotations

import unittest
from pathlib import Path

from tier1.patterns import (
    DeterministicSignal,
    PatternLibrary,
    VulnerabilityPattern,
    evaluate_pattern_signals,
    read_dependency_names,
)


class TestPatternLibraryLoad(unittest.TestCase):
    """Tests for loading the curated pattern YAML files."""

    def test_load_default_returns_patterns(self) -> None:
        lib = PatternLibrary.load_default()
        self.assertGreaterEqual(len(lib), 3)

    def test_load_default_contains_vp001(self) -> None:
        lib = PatternLibrary.load_default()
        vp001 = lib.get("VP-001")
        self.assertIsNotNone(vp001)
        self.assertEqual(vp001.slug, "client-writable-server-authority")

    def test_load_default_contains_vp002(self) -> None:
        lib = PatternLibrary.load_default()
        vp002 = lib.get("VP-002")
        self.assertIsNotNone(vp002)

    def test_load_default_contains_vp003(self) -> None:
        lib = PatternLibrary.load_default()
        vp003 = lib.get("VP-003")
        self.assertIsNotNone(vp003)

    def test_load_from_empty_directory(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            lib = PatternLibrary.load_from_directory(tmp)
            self.assertEqual(len(lib), 0)

    def test_all_returns_list(self) -> None:
        lib = PatternLibrary.load_default()
        patterns = lib.all()
        self.assertIsInstance(patterns, list)
        for p in patterns:
            self.assertIsInstance(p, VulnerabilityPattern)


class TestEvaluatePatternSignals(unittest.TestCase):
    """Tests for the weighted signal evaluation logic."""

    def _make_pattern(self, signals: list[DeterministicSignal], threshold: float = 0.7) -> VulnerabilityPattern:
        return VulnerabilityPattern(
            id="TEST-001",
            name="Test Pattern",
            slug="test-pattern",
            description="A test pattern",
            signals=signals,
            deterministic_threshold=threshold,
            fix_strategy="Fix it.",
        )

    def test_dependency_signal_matches(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="dependency",
                description="Supabase client",
                package_names=["@supabase/supabase-js"],
                weight=1.0,
            ),
        ])
        score, evidence = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=["@supabase/supabase-js", "react"],
            all_file_paths=[],
        )
        self.assertEqual(score, 1.0)
        self.assertTrue(len(evidence) > 0)

    def test_dependency_signal_case_insensitive(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="dependency",
                description="Firebase",
                package_names=["firebase"],
                weight=1.0,
            ),
        ])
        score, _ = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=["Firebase"],
            all_file_paths=[],
        )
        self.assertEqual(score, 1.0)

    def test_dependency_signal_no_match(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="dependency",
                description="Supabase client",
                package_names=["@supabase/supabase-js"],
                weight=1.0,
            ),
        ])
        score, evidence = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=["react", "express"],
            all_file_paths=[],
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(len(evidence), 0)

    def test_regex_signal_matches(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="regex",
                description="Dangerous call",
                patterns=[r"\.update\("],
                weight=1.0,
            ),
        ])
        score, evidence = evaluate_pattern_signals(
            pattern,
            signals={
                "pattern:test-pattern": [
                    {"file_path": "src/api.ts", "line_number": 10, "snippet": ".update(data)", "match": "update call"},
                ],
            },
            dependency_names=[],
            all_file_paths=[],
        )
        self.assertEqual(score, 1.0)
        self.assertTrue(len(evidence) > 0)

    def test_regex_signal_no_match(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="regex",
                description="Dangerous call",
                patterns=[r"\.update\("],
                weight=1.0,
            ),
        ])
        score, _ = evaluate_pattern_signals(
            pattern,
            signals={"pattern:test-pattern": []},
            dependency_names=[],
            all_file_paths=[],
        )
        self.assertEqual(score, 0.0)

    def test_file_presence_positive_signal(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="file_presence",
                description="Admin route present",
                patterns=["admin/", "/admin"],
                weight=1.0,
                is_positive=True,
            ),
        ])
        score, _ = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=[],
            all_file_paths=["src/admin/dashboard.tsx", "src/app.tsx"],
        )
        self.assertEqual(score, 1.0)

    def test_file_presence_negative_signal_fires_when_absent(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="file_presence",
                description="Missing server functions",
                patterns=["supabase/functions", "api/functions", "netlify/functions"],
                weight=1.0,
                is_positive=False,
            ),
        ])
        score, evidence = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=[],
            all_file_paths=["src/app.tsx", "package.json"],
        )
        self.assertEqual(score, 1.0)
        self.assertTrue(len(evidence) > 0)

    def test_file_presence_negative_signal_silent_when_present(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="file_presence",
                description="Missing server functions",
                patterns=["supabase/functions"],
                weight=1.0,
                is_positive=False,
            ),
        ])
        score, _ = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=[],
            all_file_paths=["supabase/functions/hello/index.ts"],
        )
        self.assertEqual(score, 0.0)

    def test_weighted_scoring(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="dependency",
                description="Has supabase",
                package_names=["@supabase/supabase-js"],
                weight=0.3,
            ),
            DeterministicSignal(
                signal_type="regex",
                description="Client mutations",
                patterns=[r"\.update\("],
                weight=0.7,
            ),
        ], threshold=0.7)

        # Only dependency matches → score = 0.3/1.0 = 0.3 (below threshold)
        score, _ = evaluate_pattern_signals(
            pattern,
            signals={"pattern:test-pattern": []},
            dependency_names=["@supabase/supabase-js"],
            all_file_paths=[],
        )
        self.assertAlmostEqual(score, 0.3)

    def test_weighted_scoring_above_threshold(self) -> None:
        pattern = self._make_pattern([
            DeterministicSignal(
                signal_type="dependency",
                description="Has supabase",
                package_names=["@supabase/supabase-js"],
                weight=0.3,
            ),
            DeterministicSignal(
                signal_type="regex",
                description="Client mutations",
                patterns=[r"\.update\("],
                weight=0.7,
            ),
        ], threshold=0.7)

        # Both match → score = 1.0 (above threshold)
        score, _ = evaluate_pattern_signals(
            pattern,
            signals={
                "pattern:test-pattern": [
                    {"file_path": "src/api.ts", "line_number": 5, "snippet": ".update()", "match": "update"},
                ],
            },
            dependency_names=["@supabase/supabase-js"],
            all_file_paths=[],
        )
        self.assertAlmostEqual(score, 1.0)

    def test_empty_signals_returns_zero(self) -> None:
        pattern = self._make_pattern([])
        score, evidence = evaluate_pattern_signals(
            pattern,
            signals={},
            dependency_names=[],
            all_file_paths=[],
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(evidence, [])


class TestReadDependencyNames(unittest.TestCase):
    """Tests for dependency name extraction."""

    def test_reads_from_package_json(self) -> None:
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "package.json"
            pkg.write_text(json.dumps({
                "dependencies": {"react": "^18.0.0", "@supabase/supabase-js": "^2.0.0"},
                "devDependencies": {"vitest": "^1.0.0"},
            }))
            deps = read_dependency_names(tmp)
            self.assertIn("react", deps)
            self.assertIn("@supabase/supabase-js", deps)
            self.assertIn("vitest", deps)

    def test_reads_from_requirements_txt(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            req = Path(tmp) / "requirements.txt"
            req.write_text("flask==2.0.0\nrequests>=2.28\npydantic[dotenv]\n# comment\n")
            deps = read_dependency_names(tmp)
            self.assertIn("flask", deps)
            self.assertIn("requests", deps)
            self.assertIn("pydantic", deps)
            self.assertNotIn("# comment", deps)

    def test_empty_directory_returns_empty(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            deps = read_dependency_names(tmp)
            self.assertEqual(deps, [])


class TestScannerPatternIntegration(unittest.TestCase):
    """Tests for pattern-library-driven checks in the scanner."""

    def setUp(self) -> None:
        from tier1.scanner import DeterministicScanner
        self.scanner = DeterministicScanner()

    def _base_payload(self) -> dict:
        return {
            "index_json": {
                "signals": {
                    "secret_matches": [],
                    "private_key_matches": [],
                    "insecure_cors_matches": [],
                    "dangerous_exec_matches": [],
                    "sql_matches": [],
                    "route_hints": [],
                    "env_usage": [],
                    "weak_error_logging": [],
                    "blocking_sync": [],
                },
                "facts": {
                    "has_ci": True,
                    "has_tests": True,
                    "has_env_example": True,
                    "tracked_env_files": [],
                    "manifests_present": ["package.json"],
                    "lockfiles_present": ["package-lock.json"],
                    "dependency_names": [],
                },
                "files": [
                    {"path": "src/app.ts", "loc": 120, "ext": ".ts", "sha256": "x", "path_role": "source"},
                ],
                "linter_probes": [],
            }
        }

    def test_no_pattern_findings_on_clean_repo(self) -> None:
        payload = self._base_payload()
        findings = self.scanner.scan(index_payload=payload)
        pattern_findings = [f for f in findings if f.engine == "pattern_library"]
        self.assertEqual(len(pattern_findings), 0)

    def test_vp001_triggers_with_supabase_and_regex_signals(self) -> None:
        """VP-001 should fire when supabase dependency + regex matches exist."""
        payload = self._base_payload()
        payload["index_json"]["facts"]["dependency_names"] = ["@supabase/supabase-js"]
        payload["index_json"]["signals"]["pattern:client-writable-server-authority"] = [
            {"file_path": "src/api.ts", "line_number": 10, "snippet": ".update({ role: newRole })", "match": "client mutation on authority column"},
        ]
        findings = self.scanner.scan(index_payload=payload)
        pattern_findings = [f for f in findings if f.pattern_id == "VP-001"]
        self.assertEqual(len(pattern_findings), 1)
        self.assertEqual(pattern_findings[0].engine, "pattern_library")
        self.assertEqual(pattern_findings[0].status, "fail")
        self.assertEqual(pattern_findings[0].pattern_slug, "client-writable-server-authority")

    def test_pattern_findings_have_correct_fields(self) -> None:
        """Pattern findings should populate pattern_id, pattern_slug, and fix_strategy."""
        payload = self._base_payload()
        payload["index_json"]["facts"]["dependency_names"] = ["@supabase/supabase-js"]
        payload["index_json"]["signals"]["pattern:client-writable-server-authority"] = [
            {"file_path": "src/api.ts", "line_number": 10, "snippet": ".update({ role: 'admin' })", "match": "mutation"},
        ]
        findings = self.scanner.scan(index_payload=payload)
        pattern_findings = [f for f in findings if f.pattern_id == "VP-001"]
        if pattern_findings:
            f = pattern_findings[0]
            self.assertTrue(f.suggested_fix_stub)  # has fix strategy
            self.assertEqual(f.category, "security")

    def test_existing_15_checks_still_present(self) -> None:
        """Pattern library should not break existing check count."""
        payload = self._base_payload()
        findings = self.scanner.scan(index_payload=payload)
        check_ids = [f.check_id for f in findings if not f.check_id.startswith("VP-")]
        self.assertEqual(len(check_ids), 15)


if __name__ == "__main__":
    unittest.main()
