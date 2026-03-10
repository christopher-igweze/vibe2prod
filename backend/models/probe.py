"""Pydantic models for the live application probing feature."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProbeRequest(BaseModel):
    target_url: HttpUrl
    probe_type: str = "security"
    config: dict = Field(default_factory=dict)
    project_id: UUID | None = None


class ProbeResponse(BaseModel):
    probe_id: UUID
    status: str = "pending"
    message: str = "Probe queued"


class AuthorizeRequest(BaseModel):
    target_url: HttpUrl
    method: str = "dns_txt"


class VerifyRequest(BaseModel):
    target_url: HttpUrl
    method: str = "dns_txt"


class ProbeFinding(BaseModel):
    title: str
    description: str
    category: str
    severity: str
    url_tested: str
    method: str = "GET"
    request_summary: str = ""
    response_summary: str = ""
    evidence: str = ""
    owasp_category: str = ""
    cwe_id: str = ""
    confidence: float = 0.0


class ProbeResult(BaseModel):
    findings: list[ProbeFinding]
    probe_score: int
    duration_seconds: float
