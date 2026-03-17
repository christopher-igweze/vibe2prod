"""Shared utilities for the application.

Re-exports utc_now from the canonical location in models._utils
to avoid duplication.
"""

from models._utils import utc_now  # noqa: F401 — single source of truth

__all__ = ["utc_now"]
