"""FORGE result parsing — ForgeRunResult handling.

Extracted from forge_bridge.py for single-responsibility.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from constants import FORGE_OUTPUT_PREVIEW_LENGTH

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
    readiness_report: dict = field(default_factory=dict)
    agent_invocations: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    # v3: deterministic evaluation framework
    evaluation: dict = field(default_factory=dict)
    aivss_score: dict = field(default_factory=dict)


def _extract_readiness_score(output: dict) -> int:
    """Extract production readiness score from v3 evaluation."""
    evaluation = output.get("evaluation")
    if isinstance(evaluation, dict):
        scores = evaluation.get("scores")
        if isinstance(scores, dict):
            return scores.get("composite", 0)
    return 0


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
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                data = json.loads(text[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

    if data is None:
        return ForgeRunResult(
            execution_id=execution_id,
            status="failed",
            error=f"Could not parse FORGE output as JSON: {text[:FORGE_OUTPUT_PREVIEW_LENGTH]}",
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
        readiness_report=data.get("readiness_report") or {},
        agent_invocations=data.get("agent_invocations", 0),
        cost_usd=data.get("cost_usd", 0.0),
        duration_seconds=data.get("duration_seconds", 0.0),
        evaluation=data.get("evaluation") or {},
        aivss_score=data.get("aivss_score") or {},
    )


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
        readiness_report=output.get("readiness_report") or {},
        agent_invocations=output.get("agent_invocations", 0),
        cost_usd=output.get("cost_usd", 0.0),
        duration_seconds=output.get("duration_seconds", 0.0),
        evaluation=output.get("evaluation") or {},
        aivss_score=output.get("aivss_score") or {},
    )
