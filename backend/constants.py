"""Centralized constants for the Vibe2Prod backend.

All magic numbers, timeouts, limits, and hardcoded string literals live here
so they can be referenced by name and updated in one place.
"""

from __future__ import annotations

# ------------------------------------------------------------------ #
# HTTP / Networking
# ------------------------------------------------------------------ #

HTTP_TIMEOUT_DEFAULT_SECONDS: float = 30.0
HTTP_TIMEOUT_CONNECT_SECONDS: float = 10.0
HTTP_MAX_CONNECTIONS: int = 100
HTTP_MAX_KEEPALIVE_CONNECTIONS: int = 20

# Retry-After header values (seconds) for GitHub API errors
GITHUB_RETRY_AFTER_TIMEOUT: str = "30"
GITHUB_RETRY_AFTER_CONNECT: str = "60"

# ------------------------------------------------------------------ #
# FORGE bridge
# ------------------------------------------------------------------ #

FORGE_HTTP_TIMEOUT_SECONDS: int = 30
FORGE_ERROR_LOG_TRUNCATE: int = 500
FORGE_SANDBOX_STDERR_TRUNCATE: int = 500
FORGE_POLL_LOG_INTERVAL_SECONDS: int = 30
FORGE_OUTPUT_PREVIEW_LENGTH: int = 300

# ------------------------------------------------------------------ #
# Probe service
# ------------------------------------------------------------------ #

PROBE_DEFAULT_POLL_INTERVAL_SECONDS: int = 10
PROBE_DEFAULT_MAX_WAIT_SECONDS: int = 4200  # 70 minutes
PROBE_FREE_LIMIT: int = 3
PROBE_FINDINGS_SUMMARY_LIMIT: int = 50

# ------------------------------------------------------------------ #
# Pagination
# ------------------------------------------------------------------ #

PAGINATION_DEFAULT_LIMIT: int = 20
PAGINATION_MAX_LIMIT: int = 100
PROJECTS_DEFAULT_LIMIT: int = 50

# ------------------------------------------------------------------ #
# Scan / ActionItem effort values
# ------------------------------------------------------------------ #

EFFORT_QUICK: str = "quick"
EFFORT_MODERATE: str = "moderate"
EFFORT_SIGNIFICANT: str = "significant"
VALID_EFFORT_VALUES: frozenset[str] = frozenset({EFFORT_QUICK, EFFORT_MODERATE, EFFORT_SIGNIFICANT})

# ------------------------------------------------------------------ #
# Probe statuses
# ------------------------------------------------------------------ #

STATUS_PENDING: str = "pending"
STATUS_RUNNING: str = "running"
STATUS_COMPLETED: str = "completed"
STATUS_FAILED: str = "failed"
STATUS_CANCELLED: str = "cancelled"

# Terminal statuses used by FORGE polling
FORGE_TERMINAL_STATUSES: frozenset[str] = frozenset({
    "completed", "succeeded", "failed", "aborted",
})

# Terminal statuses used by probe polling
PROBE_TERMINAL_STATUSES: frozenset[str] = frozenset({
    "completed", "failed", "cancelled",
})

# ------------------------------------------------------------------ #
# Domain authorization
# ------------------------------------------------------------------ #

DOMAIN_AUTH_EXPIRY_DAYS: int = 30

# ------------------------------------------------------------------ #
# Webhook
# ------------------------------------------------------------------ #

WEBHOOK_MIN_REPLAY_WINDOW_SECONDS: int = 60

# ------------------------------------------------------------------ #
# Sandbox
# ------------------------------------------------------------------ #

SANDBOX_MAX_RETRIES: int = 3
SANDBOX_RETRY_BACKOFF_MULTIPLIER: int = 5  # delay = multiplier * attempt
SANDBOX_REPO_PATH: str = "/home/daytona/repo"
SANDBOX_WORKDIR: str = "/home/daytona"
SANDBOX_FILE_READ_TIMEOUT: int = 120
SANDBOX_FILE_TREE_LIMIT: int = 500
