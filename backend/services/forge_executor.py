"""FORGE execution logic — trigger scan, trigger remediate, polling.

Extracted from forge_bridge.py for single-responsibility.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Sequence
from uuid import UUID

from daytona.common.errors import DaytonaError

from config import settings
from constants import (
    FORGE_ERROR_LOG_TRUNCATE,
    FORGE_HTTP_TIMEOUT_SECONDS,
    FORGE_POLL_LOG_INTERVAL_SECONDS,
    FORGE_SANDBOX_STDERR_TRUNCATE,
    FORGE_TERMINAL_STATUSES,
)
from sandbox.manager import SandboxManager
from services.forge_result_parser import (
    ForgeRunResult,
    _parse_sandbox_result,
    _parse_forge_result,
)

logger = logging.getLogger(__name__)


# ── HTTP helpers (sync, stdlib — no external deps) ────────────────────


def _http_post(url: str, payload: dict, api_key: str = "") -> dict:
    """POST JSON to AgentField API."""
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=FORGE_HTTP_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error("HTTP %d from %s: %s", e.code, url, body[:FORGE_ERROR_LOG_TRUNCATE])
        raise
    except urllib.error.URLError as e:
        logger.error("Connection error to %s: %s", url, e.reason)
        raise


def _http_get(url: str, api_key: str = "") -> dict:
    """GET from AgentField API."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=FORGE_HTTP_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error("HTTP %d from %s: %s", e.code, url, body[:FORGE_ERROR_LOG_TRUNCATE])
        raise


async def _poll_until_complete(
    agentfield_url: str,
    execution_id: str,
    api_key: str = "",
    timeout: int | None = None,
    poll_interval: int | None = None,
) -> dict:
    """Poll AgentField for execution completion."""
    timeout = timeout or settings.forge_remediate_timeout_seconds
    poll_interval = poll_interval or settings.forge_poll_interval_seconds
    url = f"{agentfield_url}/api/v1/executions/{execution_id}"
    elapsed = 0

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        try:
            result = _http_get(url, api_key)
        except asyncio.TimeoutError as e:
            logger.warning("Timeout polling FORGE execution %s (will retry): %s", execution_id, e)
            continue
        except Exception as e:
            logger.warning("Poll failed (will retry): %s", e)
            continue

        status = str(result.get("status", "")).lower()
        if elapsed % FORGE_POLL_LOG_INTERVAL_SECONDS == 0:
            logger.info("FORGE execution %s: status=%s (%ds)", execution_id, status, elapsed)

        if status in FORGE_TERMINAL_STATUSES:
            return result

    return {"status": "timeout", "error": f"Timed out after {timeout}s"}


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
            openrouter_api_key=settings.openrouter_api_key,
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


async def trigger_forge_remediate(
    repo_url: str,
    scan_findings: Sequence[Any] | None = None,
    *,
    mode: str = "full",
    model_override: str | None = None,
    timeout: int | None = None,
    agentfield_url_override: str | None = None,
    github_token: str | None = None,
    project_context: dict | None = None,
) -> ForgeRunResult:
    """Trigger a full FORGE remediation run."""
    agentfield_url = agentfield_url_override or settings.forge_agentfield_url
    api_key = settings.agentfield_api_key

    config: dict[str, Any] = {"mode": mode}
    if model_override:
        config["models"] = {"default": model_override}
    if project_context:
        config["project_context"] = project_context

    finding_dicts = None
    if scan_findings:
        finding_dicts = [
            f.model_dump() if hasattr(f, "model_dump") else dict(f)
            for f in scan_findings
        ]

    clone_url = _authenticated_url(repo_url, github_token)

    payload = {
        "input": {
            "repo_url": clone_url,
            "config": config,
            "scan_findings": finding_dicts,
        }
    }

    return await _trigger_forge(
        agentfield_url, api_key, "remediate", payload,
        timeout or settings.forge_remediate_timeout_seconds,
    )


async def _trigger_forge(
    agentfield_url: str,
    api_key: str,
    reasoner: str,
    payload: dict,
    timeout: int,
) -> ForgeRunResult:
    """Internal: trigger a FORGE reasoner and wait for result."""
    node_id = settings.forge_node_id
    url = f"{agentfield_url}/api/v1/execute/async/{node_id}.{reasoner}"

    logger.info("Triggering FORGE %s at %s", reasoner, url)

    try:
        resp = _http_post(url, payload, api_key)
    except asyncio.TimeoutError as e:
        return ForgeRunResult(
            status="error",
            error=f"Timeout triggering FORGE: {e}",
        )
    except Exception as e:
        return ForgeRunResult(
            status="error",
            error=f"Failed to trigger FORGE: {e}",
        )

    execution_id = resp.get("execution_id", resp.get("id", ""))
    if not execution_id:
        return ForgeRunResult(
            status="error",
            error=f"No execution_id in response: {resp}",
        )

    logger.info("FORGE execution started: %s", execution_id)

    try:
        result = await _poll_until_complete(
            agentfield_url, execution_id, api_key, timeout,
        )
    except asyncio.TimeoutError as e:
        return ForgeRunResult(
            execution_id=execution_id,
            status="timeout",
            error=f"Polling for FORGE result timed out: {e}",
        )

    return _parse_forge_result(execution_id, result)
