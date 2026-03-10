"""Probe routes — live application security testing.

POST /api/probe/authorize   — generate verification token for a domain
POST /api/probe/verify      — verify domain ownership
POST /api/probe             — start a security probe (background task)
GET  /api/probe/{probe_id}  — probe status + results
GET  /api/probe/{probe_id}/findings — findings list
GET  /api/user/probes       — list user's probes
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from models.probe import (
    AuthorizeRequest,
    ProbeRequest,
    ProbeResponse,
    VerifyRequest,
)
from services import supabase_client as db
from services.target_auth import (
    extract_domain,
    generate_verification_token,
    is_authorized,
    verify_dns_txt,
    verify_file,
    verify_meta_tag,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ------------------------------------------------------------------ #
# Background task: run the probe
# ------------------------------------------------------------------ #


async def _run_probe(probe_id: str, target_url: str, user_id: str, probe_type: str) -> None:
    """Background task that executes the probe engine and stores results."""
    from services.probe_engine import ProbeEngine

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        await db.update_probe_status(probe_id, "running", started_at=now_iso)

        engine = ProbeEngine(target_url, probe_type)
        result = engine.run()
        # ProbeEngine.run() is async
        if asyncio.iscoroutine(result):
            result = await result

        completed_iso = datetime.now(timezone.utc).isoformat()

        # Count severities
        severity_counts = Counter(f.severity for f in result.findings)

        await db.update_probe_results(
            probe_id,
            total_findings=len(result.findings),
            critical_count=severity_counts.get("critical", 0),
            high_count=severity_counts.get("high", 0),
            medium_count=severity_counts.get("medium", 0),
            low_count=severity_counts.get("low", 0),
            probe_score=result.probe_score,
            report_data={"findings_summary": [f.model_dump() for f in result.findings[:50]]},
        )

        # Save individual findings
        finding_rows = [
            {
                "title": f.title,
                "description": f.description,
                "category": f.category,
                "severity": f.severity,
                "url_tested": f.url_tested,
                "method": f.method,
                "request_summary": f.request_summary,
                "response_summary": f.response_summary,
                "evidence": f.evidence,
                "owasp_category": f.owasp_category,
                "cwe_id": f.cwe_id,
                "confidence": f.confidence,
            }
            for f in result.findings
        ]
        await db.save_probe_findings(probe_id, user_id, finding_rows)

        await db.update_probe_status(
            probe_id,
            "completed",
            completed_at=completed_iso,
            duration_seconds=result.duration_seconds,
        )
        logger.info(
            "Probe %s completed: score=%d, findings=%d (%.1fs)",
            probe_id, result.probe_score, len(result.findings), result.duration_seconds,
        )
    except Exception as exc:
        logger.exception("Probe %s failed: %s", probe_id, exc)
        try:
            await db.update_probe_status(
                probe_id,
                "failed",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception("Failed to update probe status after error for %s", probe_id)


# Need asyncio for the iscoroutine check
import asyncio  # noqa: E402


# ------------------------------------------------------------------ #
# POST /api/probe/authorize
# ------------------------------------------------------------------ #


@router.post("/probe/authorize")
@limiter.limit(rate_limit_string())
async def authorize_domain(body: AuthorizeRequest, request: Request) -> dict:
    """Generate a verification token for domain ownership."""
    user_id: str = request.state.user_id
    domain = extract_domain(str(body.target_url))
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid target URL")

    token = generate_verification_token(user_id, domain)

    instructions = {
        "dns_txt": f'Add a TXT record to {domain}: "vibe2prod-verify={token}"',
        "meta_tag": f'Add <meta name="vibe2prod-verify" content="{token}"> to the <head> of your homepage.',
        "file_upload": f"Create a file at {body.target_url}/.well-known/vibe2prod-verify.txt containing: {token}",
    }

    return {
        "domain": domain,
        "token": token,
        "method": body.method,
        "instructions": instructions.get(body.method, "Unknown method"),
    }


# ------------------------------------------------------------------ #
# POST /api/probe/verify
# ------------------------------------------------------------------ #


@router.post("/probe/verify")
@limiter.limit(rate_limit_string())
async def verify_domain(body: VerifyRequest, request: Request) -> dict:
    """Verify domain ownership via the chosen method."""
    user_id: str = request.state.user_id
    domain = extract_domain(str(body.target_url))
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid target URL")

    token = generate_verification_token(user_id, domain)

    verified = False
    if body.method == "dns_txt":
        verified = await verify_dns_txt(domain, token)
    elif body.method == "meta_tag":
        verified = await verify_meta_tag(str(body.target_url), token)
    elif body.method == "file_upload":
        verified = await verify_file(str(body.target_url), token)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported method: {body.method}")

    if not verified:
        raise HTTPException(status_code=403, detail="Domain verification failed")

    # Store authorization (valid for 30 days)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    await db.save_authorized_target(user_id, domain, body.method, expires_at)

    return {"verified": True, "domain": domain, "expires_at": expires_at}


# ------------------------------------------------------------------ #
# POST /api/probe
# ------------------------------------------------------------------ #


@router.post("/probe", response_model=ProbeResponse)
@limiter.limit(rate_limit_string())
async def start_probe(
    body: ProbeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> ProbeResponse:
    """Start a security probe against a target URL."""
    user_id: str = request.state.user_id

    if not settings.probe_enabled:
        raise HTTPException(status_code=503, detail="Live probing is not enabled")

    domain = extract_domain(str(body.target_url))
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid target URL")

    # Role check
    role = db.get_user_role(user_id)

    # For beta/developer users, auto-authorize with manual_approve
    if role in ("developer", "beta_tester"):
        existing = await db.get_authorized_target(user_id, domain)
        if not existing:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            await db.save_authorized_target(user_id, domain, "manual_approve", expires_at)
    elif not await is_authorized(user_id, domain, db):
        raise HTTPException(
            status_code=403,
            detail="Domain not authorized. Use POST /api/probe/authorize and /api/probe/verify first.",
        )

    probe_id = str(uuid4())
    probe_data = {
        "id": probe_id,
        "user_id": user_id,
        "target_url": str(body.target_url),
        "status": "pending",
        "probe_type": body.probe_type,
        "config": body.config,
        "auth_method": "manual_approve" if role in ("developer", "beta_tester") else None,
    }
    if body.project_id:
        probe_data["project_id"] = str(body.project_id)

    await db.create_probe(probe_data)

    background_tasks.add_task(_run_probe, probe_id, str(body.target_url), user_id, body.probe_type)

    return ProbeResponse(
        probe_id=probe_id,
        status="pending",
        message="Probe queued",
    )


# ------------------------------------------------------------------ #
# GET /api/probe/{probe_id}
# ------------------------------------------------------------------ #


@router.get("/probe/{probe_id}")
@limiter.limit(rate_limit_string())
async def get_probe_status(probe_id: str, request: Request) -> dict:
    """Return probe status and results."""
    user_id: str = request.state.user_id
    probe = await db.get_probe(probe_id, user_id)
    if not probe:
        raise HTTPException(status_code=404, detail="Probe not found")
    return probe


# ------------------------------------------------------------------ #
# GET /api/probe/{probe_id}/findings
# ------------------------------------------------------------------ #


@router.get("/probe/{probe_id}/findings")
@limiter.limit(rate_limit_string())
async def get_probe_findings(probe_id: str, request: Request) -> list[dict]:
    """Return all findings for a probe."""
    user_id: str = request.state.user_id
    # Verify probe exists and belongs to user
    probe = await db.get_probe(probe_id, user_id)
    if not probe:
        raise HTTPException(status_code=404, detail="Probe not found")
    return await db.get_probe_findings(probe_id, user_id)


# ------------------------------------------------------------------ #
# GET /api/user/probes
# ------------------------------------------------------------------ #


@router.get("/user/probes")
@limiter.limit(rate_limit_string())
async def list_probes(request: Request) -> list[dict]:
    """Return the authenticated user's probes."""
    user_id: str = request.state.user_id
    return await db.list_user_probes(user_id)
