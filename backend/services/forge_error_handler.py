"""FORGE error handling and retry logic.

Extracted from forge_bridge.py for single-responsibility.
Provides error classification and structured error responses.
"""

from __future__ import annotations

import logging

from services.forge_result_parser import ForgeRunResult

logger = logging.getLogger(__name__)


def forge_timeout_error(execution_id: str = "", detail: str = "") -> ForgeRunResult:
    """Create a ForgeRunResult for timeout errors."""
    return ForgeRunResult(
        execution_id=execution_id,
        status="timeout",
        error=detail or "FORGE operation timed out",
    )


def forge_execution_error(execution_id: str = "", detail: str = "") -> ForgeRunResult:
    """Create a ForgeRunResult for execution errors."""
    return ForgeRunResult(
        execution_id=execution_id,
        status="error",
        error=detail or "FORGE execution failed",
    )


def forge_sandbox_error(execution_id: str = "", detail: str = "") -> ForgeRunResult:
    """Create a ForgeRunResult for sandbox errors."""
    return ForgeRunResult(
        execution_id=execution_id,
        status="error",
        error=detail or "Sandbox execution failed",
    )


def is_retriable_error(error: str) -> bool:
    """Determine if a FORGE error is retriable."""
    retriable_patterns = [
        "timeout",
        "temporarily unavailable",
        "connection",
        "rate limit",
    ]
    error_lower = error.lower()
    return any(pattern in error_lower for pattern in retriable_patterns)
