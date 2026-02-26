"""FORGE bridge — triggers FORGE remediation via AgentField control plane.

This is the integration layer that the vibe2prod backend uses
to trigger FORGE engine runs via AgentField HTTP API.

Usage:
    from services.forge_bridge import trigger_forge_scan, trigger_forge_remediate

    # Discovery only (free tier)
    result = await trigger_forge_scan(repo_url="https://github.com/user/repo")

    # Full remediation
    result = await trigger_forge_remediate(
        repo_url="https://github.com/user/repo",
        tier1_findings=scan_result.findings,
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

from config import settings

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 10  # seconds
_SCAN_TIMEOUT = 600  # 10 minutes for discovery
_REMEDIATE_TIMEOUT = 2700  # 45 minutes for full remediation


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
    timeout: int = _REMEDIATE_TIMEOUT,
    poll_interval: int = _POLL_INTERVAL,
) -> dict:
    """Poll AgentField for execution completion."""
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

        if status in ("completed", "failed", "aborted"):
            return result

    return {"status": "timeout", "error": f"Timed out after {timeout}s"}


# ── Public API ────────────────────────────────────────────────────────


async def trigger_forge_scan(
    repo_url: str,
    *,
    model_override: str | None = None,
    timeout: int = _SCAN_TIMEOUT,
    agentfield_url_override: str | None = None,
) -> ForgeRunResult:
    """Trigger a FORGE discovery scan (no fixes applied).

    Returns a ForgeRunResult with findings and readiness score.
    """
    agentfield_url = agentfield_url_override or settings.forge_agentfield_url
    api_key = settings.agentfield_api_key

    config: dict[str, Any] = {
        "mode": "discovery",
        "dry_run": True,
    }
    if model_override:
        config["models"] = {"default": model_override}

    payload = {
        "input": {
            "repo_url": repo_url,
            "config": config,
        }
    }

    return await _trigger_forge(
        agentfield_url, api_key, "scan", payload, timeout,
    )


async def trigger_forge_remediate(
    repo_url: str,
    tier1_findings: Sequence[Any] | None = None,
    *,
    mode: str = "full",
    model_override: str | None = None,
    timeout: int = _REMEDIATE_TIMEOUT,
    agentfield_url_override: str | None = None,
    github_token: str | None = None,
) -> ForgeRunResult:
    """Trigger a full FORGE remediation run.

    Args:
        repo_url: GitHub repository URL.
        tier1_findings: Optional pre-existing Tier 1 scan findings.
        mode: "full", "discovery", or "remediation".
        model_override: Override default model for all agents.
        timeout: Max wait time in seconds.
        agentfield_url_override: Override AgentField URL.
        github_token: GitHub token for PR creation.
    """
    agentfield_url = agentfield_url_override or settings.forge_agentfield_url
    api_key = settings.agentfield_api_key

    config: dict[str, Any] = {"mode": mode}
    if model_override:
        config["models"] = {"default": model_override}

    # Convert tier1 findings to dicts if they're model objects
    t1_dicts = None
    if tier1_findings:
        t1_dicts = [
            f.model_dump() if hasattr(f, "model_dump") else dict(f)
            for f in tier1_findings
        ]

    payload = {
        "input": {
            "repo_url": repo_url,
            "config": config,
            "tier1_findings": t1_dicts,
        }
    }

    return await _trigger_forge(
        agentfield_url, api_key, "remediate", payload, timeout,
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
        success=output.get("success", status == "completed"),
        summary=output.get("summary", ""),
        error=raw.get("error", output.get("error", "")),
        total_findings=output.get("total_findings", 0),
        findings_fixed=output.get("findings_fixed", 0),
        findings_deferred=output.get("findings_deferred", 0),
        readiness_score=_extract_readiness_score(output),
        pr_url=output.get("pr_url", ""),
        raw_result=raw,
    )


def _extract_readiness_score(output: dict) -> int:
    """Extract the production readiness score from output."""
    report = output.get("readiness_report")
    if isinstance(report, dict):
        return report.get("overall_score", 0)
    return 0
