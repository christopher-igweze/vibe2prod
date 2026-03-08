"""Pydantic models for org onboarding payloads."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class TechnicalLevel(str, Enum):
    founder = "founder"
    vibe_coder = "vibe_coder"
    engineer = "engineer"


class ExplanationStyle(str, Enum):
    teach_me = "teach_me"
    just_steps = "just_steps"
    cto_brief = "cto_brief"


class ShippingPosture(str, Enum):
    ship_fast = "ship_fast"
    balanced = "balanced"
    production_first = "production_first"


class CodingTool(str, Enum):
    claude_code = "claude_code"
    codex = "codex"
    antigravity = "antigravity"
    cursor = "cursor"
    replit = "replit"
    lovable = "lovable"
    other = "other"


class AcquisitionSource(str, Enum):
    hackathon = "hackathon"
    linkedin = "linkedin"
    founder_begged_me = "founder_begged_me"
    x_twitter = "x_twitter"
    threads = "threads"
    other = "other"


class OrgOnboardingPayload(BaseModel):
    """Org-profile defaults captured during required onboarding."""

    technical_level: TechnicalLevel
    explanation_style: ExplanationStyle
    shipping_posture: ShippingPosture = ShippingPosture.balanced
    tool_tags: list[str] = Field(default_factory=list, max_length=30)
    coding_tool: CodingTool
    coding_tool_other: str | None = None
    acquisition_source: AcquisitionSource
    acquisition_other: str | None = None
