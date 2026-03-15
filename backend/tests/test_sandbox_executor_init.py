"""Tests for SandboxManager initialization error handling.

Verifies that:
1. A failing Daytona client constructor is caught, logged, and re-raised as a
   descriptive RuntimeError (not as a raw SDK exception).
2. The error message identifies the sandbox service as the source, giving
   callers and operators actionable context.
3. Successful initialization works as before.

Test Location: tests/test_sandbox_executor_init.py
Project: sandbox/manager.py
Framework: pytest
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_settings(
    daytona_api_key: str = "test-key",
    daytona_api_url: str = "https://app.daytona.io/api",
    daytona_target: str | None = None,
) -> MagicMock:
    """Return a minimal mock settings object for SandboxManager construction."""
    mock = MagicMock()
    mock.daytona_api_key = daytona_api_key
    mock.daytona_api_url = daytona_api_url
    mock.daytona_target = daytona_target
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSandboxManagerInit:
    """Unit tests for SandboxManager.__init__ error handling."""

    def test_daytona_init_failure_raises_runtime_error(self):
        """When Daytona() raises, SandboxManager must re-raise as RuntimeError.

        Raw SDK exceptions (DaytonaError, ValueError, etc.) bubbling up
        unhandled from a constructor give callers and operators no context.
        Wrapping them in a RuntimeError with a clear message makes the
        failure immediately understandable.
        """
        mock_settings = _make_mock_settings()

        with patch("sandbox.manager.settings", mock_settings), \
             patch("sandbox.manager.Daytona", side_effect=Exception("invalid API key")), \
             patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()), \
             patch("sandbox.manager.SandboxExecutor"):

            from sandbox.manager import SandboxManager

            with pytest.raises(RuntimeError) as exc_info:
                SandboxManager()

            error_msg = str(exc_info.value)
            assert "sandbox" in error_msg.lower() or "daytona" in error_msg.lower(), (
                "RuntimeError message should mention 'sandbox' or 'daytona' so operators "
                f"know what failed. Got: {error_msg!r}"
            )
            assert "invalid API key" in error_msg, (
                "RuntimeError message should include the original exception text. "
                f"Got: {error_msg!r}"
            )

    def test_daytona_init_failure_preserves_cause(self):
        """The RuntimeError must chain the original exception via __cause__.

        Preserving the cause lets logging and error-tracking tools (Sentry,
        CloudWatch, etc.) show the full traceback to the original SDK error.
        """
        original_exc = ValueError("Connection refused to Daytona API")
        mock_settings = _make_mock_settings()

        with patch("sandbox.manager.settings", mock_settings), \
             patch("sandbox.manager.Daytona", side_effect=original_exc), \
             patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()), \
             patch("sandbox.manager.SandboxExecutor"):

            from sandbox.manager import SandboxManager

            with pytest.raises(RuntimeError) as exc_info:
                SandboxManager()

            assert exc_info.value.__cause__ is original_exc, (
                "RuntimeError.__cause__ must be the original SDK exception so the "
                "full traceback is preserved."
            )

    def test_daytona_init_failure_logs_warning(self, caplog):
        """A warning must be emitted before re-raising so operators see it in logs.

        The warning (not error) level is intentional: the severity of the
        failure is best expressed by the RuntimeError propagating to the
        caller; the log entry is for operator awareness at startup or
        request time.
        """
        mock_settings = _make_mock_settings()

        with patch("sandbox.manager.settings", mock_settings), \
             patch("sandbox.manager.Daytona", side_effect=RuntimeError("Daytona SDK boom")), \
             patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()), \
             patch("sandbox.manager.SandboxExecutor"):

            from sandbox.manager import SandboxManager

            with caplog.at_level(logging.WARNING, logger="sandbox.manager"):
                with pytest.raises(RuntimeError):
                    SandboxManager()

            warning_records = [
                r for r in caplog.records
                if r.levelno >= logging.WARNING and (
                    "daytona" in r.message.lower() or "sandbox" in r.message.lower()
                )
            ]
            assert len(warning_records) >= 1, (
                "Expected at least one WARNING log mentioning 'daytona' or 'sandbox' "
                f"when Daytona initialization fails. Records: {caplog.records}"
            )

    def test_daytona_init_failure_not_silent(self):
        """Daytona constructor failures must never be silently swallowed.

        Swallowing the exception would leave _daytona unset and cause a
        confusing AttributeError later when provision() tries to use it.
        """
        mock_settings = _make_mock_settings()

        with patch("sandbox.manager.settings", mock_settings), \
             patch("sandbox.manager.Daytona", side_effect=OSError("network unreachable")), \
             patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()), \
             patch("sandbox.manager.SandboxExecutor"):

            from sandbox.manager import SandboxManager

            # Must raise — must not silently return a broken manager object
            with pytest.raises((RuntimeError, OSError)):
                SandboxManager()

    def test_daytona_init_success_returns_manager(self):
        """When Daytona() succeeds, SandboxManager initialises cleanly.

        This is the happy-path regression test: the error-handling wrapper
        must not break normal operation.
        """
        mock_daytona_instance = MagicMock()
        mock_settings = _make_mock_settings()

        with patch("sandbox.manager.settings", mock_settings), \
             patch("sandbox.manager.Daytona", return_value=mock_daytona_instance), \
             patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()), \
             patch("sandbox.manager.SandboxExecutor", return_value=MagicMock()):

            from sandbox.manager import SandboxManager

            mgr = SandboxManager()

        # Internal Daytona client must be set to the mock instance
        assert mgr._daytona is mock_daytona_instance
        # Session store must start empty
        assert mgr._sessions == {}

    def test_daytona_init_success_with_none_target(self):
        """SandboxManager handles a None (or blank) target cleanly."""
        mock_daytona_instance = MagicMock()
        mock_settings = _make_mock_settings(daytona_target=None)

        with patch("sandbox.manager.settings", mock_settings), \
             patch("sandbox.manager.Daytona", return_value=mock_daytona_instance) as mock_daytona_cls, \
             patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()) as mock_config_cls, \
             patch("sandbox.manager.SandboxExecutor", return_value=MagicMock()):

            from sandbox.manager import SandboxManager

            mgr = SandboxManager()

        # DaytonaConfig must have been called (once)
        mock_config_cls.assert_called_once()
        # Daytona must have been constructed from that config
        mock_daytona_cls.assert_called_once()
        assert mgr._daytona is mock_daytona_instance

    def test_daytona_init_different_exception_types_all_become_runtime_error(self):
        """Various SDK exception types must all become RuntimeError at the boundary.

        The Daytona SDK may raise different exception types depending on what
        goes wrong (bad config, network, import issues).  Callers should not
        need to catch every possible SDK exception — only RuntimeError.
        """
        mock_settings = _make_mock_settings()
        exception_types = [
            ValueError("Bad API key format"),
            ConnectionError("Cannot reach Daytona endpoint"),
            TypeError("Unexpected config parameter"),
            Exception("Unknown SDK error"),
        ]

        for original in exception_types:
            with patch("sandbox.manager.settings", mock_settings), \
                 patch("sandbox.manager.Daytona", side_effect=original), \
                 patch("sandbox.manager.DaytonaConfig", return_value=MagicMock()), \
                 patch("sandbox.manager.SandboxExecutor"):

                from sandbox.manager import SandboxManager

                with pytest.raises(RuntimeError, match=r"[Ss]andbox"):
                    SandboxManager()
