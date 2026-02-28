"""FORGE bridge — triggers FORGE scans and remediation.

Discovery scans run inside isolated Daytona sandboxes.
Remediation runs go through AgentField control plane.

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

import asyncio
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Sequence
from uuid import UUID

from config import settings
from sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)



@dataclass
class ForgeRunResult:
    """Result of a FORGE run triggered via AgentField."""

    execution_id: str = ""
    forge_run_id: str = ""
    status: str = "unknown"
    success: bool = False
    summary: str = ""
    error: str = ""
    total_findings: int = 0
    findings_fixed: int = 0
    findings_deferred: int = 0
    readiness_score: int = 0
    pr_url: str = ""
    raw_result: dict = field(default_factory=dict)
    discovery_report: dict = field(default_factory=dict)


# ── HTTP helpers (sync, stdlib — no external deps) ────────────────────


def _http_post(url: str, payload: dict, api_key: str = "") -> dict:
    """POST JSON to AgentField API."""
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error("HTTP %d from %s: %s", e.code, url, body[:500])
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        logger.error("HTTP %d from %s: %s", e.code, url, body[:500])
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
        except Exception as e:
            logger.warning("Poll failed (will retry): %s", e)
            continue

        status = str(result.get("status", "")).lower()
        if elapsed % 30 == 0:
            logger.info("FORGE execution %s: status=%s (%ds)", execution_id, status, elapsed)

        if status in ("completed", "succeeded", "failed", "aborted"):
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
    """Run a FORGE discovery scan inside an isolated Daytona sandbox.

    Provisions a fresh sandbox, installs FORGE, clones the repo,
    runs ``vibe2prod scan --json``, parses the result, and tears
    down the sandbox.

    Returns a ForgeRunResult with findings and readiness score.
    """
    if scan_id is None:
        raise ValueError("scan_id is required for sandbox-based discovery")

    exec_timeout = timeout or settings.forge_sandbox_exec_timeout
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

        result = await mgr.exec(scan_id, cmd, cwd="/home/daytona", timeout=exec_timeout)

        if result.exit_code != 0:
            logger.error(
                "FORGE scan exited %d for scan %s: %s",
                result.exit_code, scan_id, result.stderr[:500],
            )
            return ForgeRunResult(
                execution_id=str(scan_id),
                status="failed",
                error=f"FORGE scan failed (exit {result.exit_code}): {result.stderr[:500]}",
            )

        return _parse_sandbox_result(str(scan_id), result.stdout)

    except Exception as e:
        logger.exception("FORGE sandbox scan failed for %s", scan_id)
        return ForgeRunResult(
            execution_id=str(scan_id),
            status="error",
            error=f"Sandbox execution failed: {e}",
        )
    finally:
        await mgr.destroy(scan_id)


def _parse_sandbox_result(execution_id: str, stdout: str) -> ForgeRunResult:
    """Parse FORGE CLI JSON output from sandbox stdout.

    The CLI prints ``Scanning <path>...`` before the JSON blob.
    We try json.loads on the full output first; if that fails we
    locate the first ``{`` and parse from there.
    """
    text = stdout.strip()
    if not text:
        return ForgeRunResult(
            execution_id=execution_id,
            status="failed",
            error="FORGE produced no output",
        )

    data: dict | None = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        brace = text.find("{")
        if brace >= 0:
            try:
                data = json.loads(text[brace:])
            except json.JSONDecodeError:
                pass

    if data is None:
        return ForgeRunResult(
            execution_id=execution_id,
            status="failed",
            error=f"Could not parse FORGE output as JSON: {text[:300]}",
        )

    return ForgeRunResult(
        execution_id=execution_id,
        forge_run_id=data.get("forge_run_id", ""),
        status="completed",
        success=data.get("success", True),
        summary=data.get("summary", ""),
        error=data.get("error", ""),
        total_findings=data.get("total_findings", 0),
        findings_fixed=data.get("findings_fixed", 0),
        findings_deferred=data.get("findings_deferred", 0),
        readiness_score=_extract_readiness_score(data),
        raw_result=data,
        discovery_report=data.get("discovery_report") or {},
    )


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
    """Trigger a full FORGE remediation run.

    Args:
        repo_url: GitHub repository URL.
        scan_findings: Optional pre-existing scan findings.
        mode: "full", "discovery", or "remediation".
        model_override: Override default model for all agents.
        timeout: Max wait time in seconds.
        agentfield_url_override: Override AgentField URL.
        github_token: GitHub token for PR creation.
        project_context: User-provided project context for scan personalization.
    """
    agentfield_url = agentfield_url_override or settings.forge_agentfield_url
    api_key = settings.agentfield_api_key

    config: dict[str, Any] = {"mode": mode}
    if model_override:
        config["models"] = {"default": model_override}
    if project_context:
        config["project_context"] = project_context

    # Convert scan findings to dicts if they're model objects
    finding_dicts = None
    if scan_findings:
        finding_dicts = [
            f.model_dump() if hasattr(f, "model_dump") else dict(f)
            for f in scan_findings
        ]

    payload = {
        "input": {
            "repo_url": repo_url,
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

    # Poll for completion
    result = await _poll_until_complete(
        agentfield_url, execution_id, api_key, timeout,
    )

    return _parse_forge_result(execution_id, result)


def _parse_forge_result(execution_id: str, raw: dict) -> ForgeRunResult:
    """Parse AgentField execution result into ForgeRunResult."""
    status = str(raw.get("status", "unknown")).lower()
    output = raw.get("output", raw.get("result", {}))

    if not isinstance(output, dict):
        output = {}

    return ForgeRunResult(
        execution_id=execution_id,
        forge_run_id=output.get("forge_run_id", ""),
        status=status,
        success=output.get("success", status in ("completed", "succeeded")),
        summary=output.get("summary", ""),
        error=raw.get("error", output.get("error", "")),
        total_findings=output.get("total_findings", 0),
        findings_fixed=output.get("findings_fixed", 0),
        findings_deferred=output.get("findings_deferred", 0),
        readiness_score=_extract_readiness_score(output),
        pr_url=output.get("pr_url", ""),
        raw_result=raw,
        discovery_report=output.get("discovery_report") or {},
    )


def _extract_readiness_score(output: dict) -> int:
    """Extract the production readiness score from output."""
    report = output.get("readiness_report")
    if isinstance(report, dict):
        return report.get("overall_score", 0)
    return 0
