"""FORGE execution logic — trigger scan in Daytona sandbox.

Extracted from forge_bridge.py for single-responsibility.
"""

from __future__ import annotations

import logging
from uuid import UUID

from daytona.common.errors import DaytonaError

from config import settings
from constants import FORGE_SANDBOX_STDERR_TRUNCATE
from sandbox.manager import SandboxManager
from services.forge_result_parser import (
    ForgeRunResult,
    _parse_sandbox_result,
)

logger = logging.getLogger(__name__)


def _authenticated_url(repo_url: str, token: str | None) -> str:
    """Inject a GitHub token into the clone URL for private repo access."""
    if token and "github.com" in repo_url:
        return repo_url.replace("https://github.com/", f"https://x-access-token:{token}@github.com/")
    return repo_url


# ── Public API ────────────────────────────────────────────────────────


async def trigger_forge_scan(
    repo_url: str,
    *,
    scan_id: UUID | None = None,
    github_token: str | None = None,
    model_override: str | None = None,
    timeout: int | None = None,
    project_context: dict | None = None,
    openrouter_api_key: str | None = None,
) -> ForgeRunResult:
    """Run a FORGE discovery scan inside an isolated Daytona sandbox."""
    if scan_id is None:
        raise ValueError("scan_id is required for sandbox-based discovery")

    exec_timeout = timeout or settings.forge_sandbox_exec_timeout
    model_override = model_override or settings.forge_default_model
    clone_url = _authenticated_url(repo_url, github_token)

    mgr = SandboxManager()
    try:
        await mgr.provision_forge(
            scan_id,
            clone_url,
            openrouter_api_key=openrouter_api_key or settings.openrouter_api_key,
            github_token=github_token,
        )

        cmd = "vibe2prod scan /home/daytona/repo --json"
        if model_override:
            cmd += f" --model {model_override}"

        def _on_output(line: str) -> None:
            logger.info("FORGE [%s]: %s", scan_id, line)

        result = await mgr.exec_streaming(
            scan_id, cmd, cwd="/home/daytona", timeout=exec_timeout,
            on_output=_on_output,
        )

        if result.exit_code != 0:
            logger.error(
                "FORGE scan exited %d for scan %s: %s",
                result.exit_code, scan_id, result.stderr[:FORGE_SANDBOX_STDERR_TRUNCATE],
            )
            return ForgeRunResult(
                execution_id=str(scan_id),
                status="failed",
                error=f"FORGE scan failed (exit {result.exit_code}): {result.stderr[:FORGE_SANDBOX_STDERR_TRUNCATE]}",
            )

        return _parse_sandbox_result(str(scan_id), result.stdout)

    except DaytonaError as e:
        status_code = getattr(e, "status_code", None)
        detail = f"DaytonaError (HTTP {status_code}): {e}" if status_code else f"DaytonaError: {e}"
        logger.error("FORGE sandbox scan failed for %s — %s", scan_id, detail)
        return ForgeRunResult(
            execution_id=str(scan_id),
            status="error",
            error=f"Sandbox execution failed: {detail}",
        )
    except Exception as e:
        logger.exception("FORGE sandbox scan failed for %s", scan_id)
        return ForgeRunResult(
            execution_id=str(scan_id),
            status="error",
            error=f"Sandbox execution failed: {type(e).__name__}: {e}",
        )
    finally:
        await mgr.destroy(scan_id)
