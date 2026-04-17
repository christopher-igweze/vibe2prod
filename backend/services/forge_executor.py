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


def _build_scan_context(
    user_preferences: dict | None,
    project_context: dict | None,
) -> dict | None:
    """Merge user preferences and project context into a FORGE context dict.

    The resulting JSON is uploaded to the sandbox at /home/daytona/forge-context.json
    and passed to ``vibe2prod scan --context``. FORGE agents read it to:

    - Adjust finding language based on ``technical_level``
    - Filter noise based on ``shipping_posture``
    - Tailor fix instructions to ``coding_tool``
    - Use project charter / vibe prompt for intent-aware analysis
    """
    ctx: dict = {}

    if user_preferences:
        prefs = {}
        if user_preferences.get("technical_level"):
            prefs["technical_level"] = user_preferences["technical_level"]
        if user_preferences.get("explanation_style"):
            prefs["explanation_style"] = user_preferences["explanation_style"]
        if user_preferences.get("shipping_posture"):
            prefs["shipping_posture"] = user_preferences["shipping_posture"]
        if user_preferences.get("coding_tool"):
            prefs["coding_tool"] = user_preferences["coding_tool"]
            if user_preferences.get("coding_tool_other"):
                prefs["coding_tool_other"] = user_preferences["coding_tool_other"]
        if prefs:
            ctx["user"] = prefs

    if project_context:
        proj = {}
        for key in ("vibe_prompt", "project_charter", "project_stage",
                     "team_size", "sensitive_data_types", "beloved_features"):
            if project_context.get(key):
                proj[key] = project_context[key]
        if proj:
            ctx["project"] = proj

    return ctx or None


# ── Public API ────────────────────────────────────────────────────────


async def trigger_forge_scan(
    repo_url: str,
    *,
    scan_id: UUID | None = None,
    github_token: str | None = None,
    model_override: str | None = None,
    timeout: int | None = None,
    project_context: dict | None = None,
    user_preferences: dict | None = None,
    openrouter_api_key: str | None = None,
    branch: str | None = None,
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

        # Checkout the specified branch (clone defaults to the repo's default branch)
        if branch:
            checkout_result = await mgr.exec(scan_id, f"git checkout {branch}", timeout=30)
            if checkout_result.exit_code != 0:
                logger.warning(
                    "Branch checkout failed for scan %s (branch=%s): %s",
                    scan_id, branch, checkout_result.stderr,
                )

        # Write scan context file into the sandbox so FORGE agents can
        # personalize findings based on the user's preferences and any
        # project context (vibe_prompt, project_charter, etc.)
        scan_context = _build_scan_context(user_preferences, project_context)
        if scan_context:
            import json as _json
            context_bytes = _json.dumps(scan_context, indent=2).encode()
            await mgr.upload_file(scan_id, "/home/daytona/forge-context.json", context_bytes)

        cmd = "vibe2prod scan /home/daytona/repo --json"
        if scan_context:
            cmd += " --context /home/daytona/forge-context.json"
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

        parsed = _parse_sandbox_result(str(scan_id), result.stdout)

        # Persist CLI project context to scan_reports.project_intake so the
        # web UI can pre-fill the intake form on rescans (CLI → DB → web).
        if parsed.success and project_context:
            try:
                from services.repositories.scan_repository import update_scan_project_intake
                await update_scan_project_intake(scan_id, project_context)
            except Exception:
                logger.exception(
                    "Failed to persist project_context to project_intake for scan %s",
                    scan_id,
                )

        return parsed

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
