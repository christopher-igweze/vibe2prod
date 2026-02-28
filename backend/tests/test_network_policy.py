"""Unit tests for sandbox/network_policy.py — egress and command guardrails."""

from __future__ import annotations

import unittest

from sandbox.network_policy import (
    NetworkPolicy,
    PolicyViolationError,
    DEFAULT_ALLOWED_HOST_SUFFIXES,
    DEFAULT_POLICY,
)


class DefaultAllowlistTests(unittest.TestCase):
    """Verify the default allowlist includes all hosts FORGE needs."""

    def test_openrouter_in_allowlist(self) -> None:
        self.assertIn("openrouter.ai", DEFAULT_ALLOWED_HOST_SUFFIXES)

    def test_github_in_allowlist(self) -> None:
        self.assertIn("github.com", DEFAULT_ALLOWED_HOST_SUFFIXES)

    def test_pypi_in_allowlist(self) -> None:
        self.assertIn("pypi.org", DEFAULT_ALLOWED_HOST_SUFFIXES)
        self.assertIn("files.pythonhosted.org", DEFAULT_ALLOWED_HOST_SUFFIXES)


class EgressValidationTests(unittest.TestCase):
    """Test URL-based egress validation."""

    def test_allowed_host_passes(self) -> None:
        DEFAULT_POLICY.validate_command("curl https://api.github.com/repos")

    def test_allowed_subdomain_passes(self) -> None:
        DEFAULT_POLICY.validate_command("curl https://sub.openrouter.ai/v1/chat")

    def test_blocked_host_raises(self) -> None:
        with self.assertRaises(PolicyViolationError) as ctx:
            DEFAULT_POLICY.validate_command("curl https://evil.example.com/exfil")
        self.assertEqual(ctx.exception.code, "blocked_egress_host")

    def test_multiple_urls_all_checked(self) -> None:
        with self.assertRaises(PolicyViolationError):
            DEFAULT_POLICY.validate_command(
                "curl https://github.com/ok && curl https://evil.com/bad"
            )


class BlockedCommandTests(unittest.TestCase):
    """Test dangerous command blocking."""

    def test_rm_rf_root_blocked(self) -> None:
        with self.assertRaises(PolicyViolationError) as ctx:
            DEFAULT_POLICY.validate_command("rm -rf /")
        self.assertEqual(ctx.exception.code, "blocked_command")

    def test_git_reset_hard_blocked(self) -> None:
        with self.assertRaises(PolicyViolationError):
            DEFAULT_POLICY.validate_command("git reset --hard HEAD~5")

    def test_shutdown_blocked(self) -> None:
        with self.assertRaises(PolicyViolationError):
            DEFAULT_POLICY.validate_command("shutdown -h now")

    def test_safe_command_passes(self) -> None:
        DEFAULT_POLICY.validate_command("python -m pytest -q")

    def test_empty_command_blocked(self) -> None:
        with self.assertRaises(PolicyViolationError) as ctx:
            DEFAULT_POLICY.validate_command("")
        self.assertEqual(ctx.exception.code, "empty_command")


class CustomPolicyTests(unittest.TestCase):
    """Test NetworkPolicy with custom allowlist."""

    def test_custom_allowlist(self) -> None:
        policy = NetworkPolicy(allowed_host_suffixes=("internal.corp",))
        policy.validate_command("curl https://internal.corp/api")

        with self.assertRaises(PolicyViolationError):
            policy.validate_command("curl https://github.com/repo")


if __name__ == "__main__":
    unittest.main()
