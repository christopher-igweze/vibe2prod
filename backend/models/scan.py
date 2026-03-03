"""Pydantic models for scan requests and responses."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

import json

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ScanStatus(str, Enum):
    pending = "pending"
    scanning = "scanning"
    completed = "completed"
    failed = "failed"


class ProjectOrigin(str, Enum):
    inspired = "inspired"
    external = "external"


class SensitiveDataType(str, Enum):
    payments = "payments"
    pii = "pii"
    health = "health"
    auth_secrets = "auth_secrets"
    none = "none"
    not_sure = "not_sure"


class ProjectIntake(BaseModel):
    """Intake context for audit request. All fields optional with defaults."""

    project_origin: ProjectOrigin = ProjectOrigin.inspired
    product_summary: str = Field(default="Not provided", max_length=800)
    target_users: str = Field(default="Not provided", max_length=400)
    sensitive_data: list[SensitiveDataType] = Field(default_factory=lambda: [SensitiveDataType.not_sure])
    must_not_break_flows: list[str] = Field(default_factory=list, max_length=20)
    deployment_target: str = Field(default="Not provided", max_length=200)
    scale_expectation: str = Field(default="Not provided", max_length=200)


class PrimerResult(BaseModel):
    """Output contract for Agent_Primer."""

    primer_json: dict = Field(default_factory=dict)
    summary: str = ""
    repo_sha: str = ""
    confidence: int = Field(default=0, ge=0, le=100)
    failure_reason: str | None = None


_MAX_CHARTER_BYTES = 10_240  # 10 KB
_MAX_CHARTER_DEPTH = 5


def _check_depth(obj: object, current: int = 0) -> None:
    if current > _MAX_CHARTER_DEPTH:
        raise ValueError(f"project_charter exceeds maximum nesting depth of {_MAX_CHARTER_DEPTH}")
    if isinstance(obj, dict):
        for v in obj.values():
            _check_depth(v, current + 1)
    elif isinstance(obj, list):
        for item in obj:
            _check_depth(item, current + 1)


class AuditRequest(BaseModel):
    """Incoming request to start an audit."""

    repo_url: HttpUrl
    branch: str | None = None  # If None, uses repo's default branch
    vibe_prompt: str | None = None
    project_charter: dict | None = None
    project_intake: ProjectIntake = Field(default_factory=ProjectIntake)
    primer: PrimerResult | None = None

    @field_validator("project_charter")
    @classmethod
    def validate_project_charter(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        serialized = json.dumps(v)
        if len(serialized.encode()) > _MAX_CHARTER_BYTES:
            raise ValueError(f"project_charter exceeds maximum size of {_MAX_CHARTER_BYTES} bytes")
        _check_depth(v)
        return v


class AuditResponse(BaseModel):
    """Immediate response when an audit is kicked off."""

    scan_id: UUID
    status: ScanStatus = ScanStatus.pending
    tier: str = "free"
    quota_remaining: int | None = None
    message: str = "Audit queued. Stream progress via /api/status/{scan_id}."


class FixRequest(BaseModel):
    """Request to auto-fix a specific action item."""

    action_item_id: UUID


class FixResponse(BaseModel):
    """Immediate response when an auto-fix is triggered."""

    fix_attempt_id: UUID
    status: str = "pending"
    message: str = "Fix queued. Stream progress via /api/status/{scan_id}."


class ScanFixResponse(BaseModel):
    """Immediate response when scan-level remediation is triggered."""

    fix_attempt_id: UUID
    status: str = "pending"
    message: str = "Remediation started"


class ScanFixStatusResponse(BaseModel):
    """Status response for a scan-level fix attempt."""

    fix_attempt_id: UUID
    scan_id: UUID
    status: str
    findings_fixed: int | None = None
    findings_deferred: int | None = None
    readiness_score: int | None = None
    pr_url: str | None = None
    summary: str | None = None
    cost_usd: float | None = None
    duration_seconds: float | None = None
