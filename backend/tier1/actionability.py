"""Actionability classifier for Tier 1 findings.

Classifies each finding into one of four actionability tiers based on
severity, confidence, and project context. Mirrors the forge-engine
classifier logic for consistency.

Tiers:
  must_fix       — Exploitable now, fix before shipping
  should_fix     — Real issue, prioritize this sprint
  consider       — Valid observation, may not be urgent at current stage
  informational  — Noted for awareness, not actionable now
"""

from __future__ import annotations

from typing import Any


def classify_tier1_actionability(
    finding: Any,
    project_context: dict | None = None,
) -> str:
    """Classify a Tier 1 finding's actionability.

    Args:
        finding: A Tier1Finding (Pydantic model) or dict.
        project_context: Forge-compatible project context dict.

    Returns:
        One of: "must_fix", "should_fix", "consider", "informational"
    """
    ctx = project_context or {}
    severity = _get(finding, "severity", "low")
    confidence = _get(finding, "confidence", 0.0)
    category = _get(finding, "category", "")
    status = _get(finding, "status", "")
    stage = ctx.get("project_stage", "")

    # Passing checks are always informational
    if status == "pass":
        return "informational"

    # Known compromises check
    compromises = ctx.get("known_compromises", [])
    if compromises:
        desc = _get(finding, "description", "").lower()
        title = _get(finding, "title", "").lower()
        for comp in compromises:
            if comp.lower() in desc or comp.lower() in title:
                return "informational"

    # Critical + high confidence → must_fix
    if severity == "critical" and confidence >= 0.85:
        return "must_fix"

    # High severity
    if severity == "high" and confidence >= 0.8:
        if stage in ("growth", "enterprise"):
            return "must_fix"
        return "should_fix"

    # Critical/high/medium with decent confidence
    if severity in ("critical", "high", "medium") and confidence >= 0.7:
        return "should_fix"

    # Medium in early stages
    if severity == "medium" and stage in ("mvp", "early_product"):
        return "consider"

    # Low severity
    if severity == "low":
        return "informational"

    return "consider"


def apply_tier1_actionability(
    findings: list,
    project_context: dict | None = None,
) -> list:
    """Apply actionability classification to a list of Tier 1 findings.

    Mutates findings in-place (sets .actionability on Pydantic models
    or ["actionability"] on dicts).

    Returns the same list for chaining.
    """
    for finding in findings:
        classified = classify_tier1_actionability(finding, project_context)
        if isinstance(finding, dict):
            finding["actionability"] = classified
        else:
            finding.actionability = classified
    return findings


def _get(obj: Any, key: str, default: Any = "") -> Any:
    """Get a field from a dict or Pydantic model."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    val = getattr(obj, key, default)
    if hasattr(val, "value"):
        return val.value
    return val
