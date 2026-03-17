"""Transform vibe2prod ProjectIntake into forge-engine project_context.

The forge-engine expects a flat dict with specific keys:
    project_stage, team_size, vision_summary, target_launch,
    known_compromises, beloved_features, original_prompt,
    sensitive_data_types

vibe2prod collects this info via ProjectIntake (required on every audit)
plus optional fields from the audit request (vibe_prompt).

This module bridges the two formats with zero LLM cost.
"""

from __future__ import annotations

from typing import Any, Union

# Forge context values are strings, lists of strings, or ints — never nested dicts.
ForgeContextValue = Union[str, int, list[str]]

# Map vibe2prod scale_expectation hints to forge project stages.
# The frontend provides free-text scale_expectation; we pattern-match
# common keywords to the closest forge stage.
_SCALE_TO_STAGE: list[tuple[list[str], str]] = [
    (["mvp", "prototype", "proof of concept", "poc", "demo", "hackathon"], "mvp"),
    (["early", "beta", "alpha", "small", "few users", "handful"], "early_product"),
    (["growth", "scaling", "thousands", "10k", "100k", "growing"], "growth"),
    (["enterprise", "million", "compliance", "hipaa", "soc2", "large"], "enterprise"),
]

# Map SensitiveDataType enum values to human-readable labels
_SENSITIVE_DATA_LABELS: dict[str, str] = {
    "payments": "payment/financial data",
    "pii": "personally identifiable information (PII)",
    "health": "health/medical data (PHI)",
    "auth_secrets": "authentication secrets and credentials",
}


def intake_to_forge_context(
    intake: dict[str, Any],
    *,
    vibe_prompt: str | None = None,
    team_size: int = 1,
) -> dict[str, ForgeContextValue]:
    """Convert a ProjectIntake dict to forge-engine project_context.

    Args:
        intake: ProjectIntake.model_dump() dict — dynamic shape from Pydantic.
        vibe_prompt: Optional original vibe prompt that generated the codebase.
        team_size: Default 1 (solo vibe-coder).

    Returns:
        A dict compatible with forge-engine's build_project_context_string().
        Values are typed as ``ForgeContextValue`` (str | int | list[str]).
    """
    if not intake:
        return {}

    ctx: dict[str, ForgeContextValue] = {}

    # Project stage — inferred from scale_expectation
    scale = intake.get("scale_expectation", "")
    ctx["project_stage"] = _infer_stage(scale)

    # Team size — vibe-coded projects are typically solo
    ctx["team_size"] = team_size

    # Vision summary — from product_summary
    summary = intake.get("product_summary", "")
    if summary:
        ctx["vision_summary"] = summary

    # Beloved features / must-not-break flows
    flows = intake.get("must_not_break_flows", [])
    if flows:
        ctx["beloved_features"] = flows

    # Sensitive data types
    sensitive = intake.get("sensitive_data", [])
    data_types = [
        _SENSITIVE_DATA_LABELS.get(s, s)
        for s in sensitive
        if s not in ("none", "not_sure")
    ]
    if data_types:
        ctx["sensitive_data_types"] = data_types

    # Original prompt
    if vibe_prompt:
        ctx["original_prompt"] = vibe_prompt

    return ctx


def _infer_stage(scale_text: str) -> str:
    """Infer forge project_stage from free-text scale_expectation."""
    if not scale_text:
        return "mvp"

    lower = scale_text.lower()
    for keywords, stage in _SCALE_TO_STAGE:
        if any(kw in lower for kw in keywords):
            return stage

    # Default for vibe-coded apps: MVP
    return "mvp"
