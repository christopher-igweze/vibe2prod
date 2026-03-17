"""FORGE bridge — backward-compatible facade.

Re-exports from split sub-modules:
  - forge_executor: Execution logic (trigger scan, trigger remediate, polling)
  - forge_result_parser: Result parsing (ForgeRunResult handling)
  - forge_error_handler: Error handling and retry logic

Usage:
    from services.forge_bridge import trigger_forge_scan, trigger_forge_remediate

    # Discovery (runs in Daytona sandbox)
    result = await trigger_forge_scan(
        scan_id=scan_id,
        repo_url="https://github.com/user/repo",
    )

    # Full remediation (via AgentField)
    result = await trigger_forge_remediate(
        repo_url="https://github.com/user/repo",
        scan_findings=scan_result.findings,
    )
"""

from __future__ import annotations

# Re-export from forge_result_parser
from services.forge_result_parser import (  # noqa: F401
    ForgeRunResult,
    _extract_readiness_score,
    _parse_sandbox_result,
    _parse_forge_result,
)

# Re-export from forge_executor
from services.forge_executor import (  # noqa: F401
    trigger_forge_scan,
    trigger_forge_remediate,
    _http_post,
    _http_get,
    _poll_until_complete,
    _authenticated_url,
    _trigger_forge,
)

# Re-export from forge_error_handler
from services.forge_error_handler import (  # noqa: F401
    forge_timeout_error,
    forge_execution_error,
    forge_sandbox_error,
    is_retriable_error,
)
