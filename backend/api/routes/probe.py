"""Probe routes — live application security testing.

POST /api/probe/authorize   — generate verification token for a domain
POST /api/probe/verify      — verify domain ownership
POST /api/probe             — start a security probe (background task)
GET  /api/probe/{probe_id}  — probe status + results
GET  /api/probe/{probe_id}/findings — findings list
GET  /api/user/probes       — list user's probes
"""

from __future__ import annotations

import hashlib
import logging
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

# Non-onboarded / anonymous users get this many free probes.
FREE_PROBE_LIMIT = 3


def _get_user_id(request: Request) -> str:
    """Return authenticated user_id or a deterministic anon ID from client IP."""
    if hasattr(request.state, "user_id"):
        return request.state.user_id
    ip = request.client.host if request.client else "unknown"
    return f"anon:{hashlib.sha256(ip.encode()).hexdigest()[:16]}"


def _is_authenticated(request: Request) -> bool:
    return hasattr(request.state, "user_id")


# ------------------------------------------------------------------ #
# Background task: run the probe
# ------------------------------------------------------------------ #


async def _run_probe(probe_id: str, target_url: str, user_id: str, probe_type: str, config: dict | None = None) -> None:
    """Background task that triggers probe service scan and stores results."""
    import asyncio
    from services.probe_bridge import probe_bridge

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        await db.update_probe_status(probe_id, "running", started_at=now_iso)

        # Trigger scan on probe service
        trigger_result = await probe_bridge.trigger_scan(target_url, config or {})
        if trigger_result.status == "error":
            raise RuntimeError(f"Probe service error: {trigger_result.error}")

        job_id = trigger_result.job_id
        if not job_id:
            raise RuntimeError("Probe service returned no job_id")
        logger.info("Probe %s → service job %s", probe_id, job_id)

        # Poll until completion (max 70 minutes, 10s interval)
        poll_interval = 10
        max_wait = 4200  # 70 minutes
        elapsed = 0
        current_status = "queued"

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            try:
                status = await probe_bridge.get_status(job_id)
                current_status = status.get("status", "unknown")
            except Exception as poll_err:
                logger.warning("Poll failed for %s (will retry): %s", job_id, poll_err)
                continue

            if current_status in ("completed", "failed", "cancelled"):
                break

        if current_status != "completed":
            raise RuntimeError(f"Probe service scan {current_status} after {elapsed}s")

        # Fetch results
        results = await probe_bridge.get_results(job_id)
        completed_iso = datetime.now(timezone.utc).isoformat()

        await db.update_probe_results(
            probe_id,
            total_findings=results.get("total_findings", 0),
            critical_count=results.get("critical_count", 0),
            high_count=results.get("high_count", 0),
            medium_count=results.get("medium_count", 0),
            low_count=results.get("low_count", 0),
            probe_score=results.get("probe_score", 0),
            report_data={"findings_summary": results.get("findings", [])[:50]},
        )

        # Save individual findings
        finding_rows = []
        for f in results.get("findings", []):
            finding_rows.append({
                "title": f.get("title", ""),
                "description": f.get("description", ""),
                "category": f.get("tool", ""),
                "severity": f.get("severity", "info"),
                "url_tested": f.get("url", ""),
                "method": "GET",
                "request_summary": "",
                "response_summary": "",
                "evidence": f.get("evidence", ""),
                "owasp_category": "",
                "cwe_id": "",
                "confidence": f.get("confidence", 0.8),
            })
        await db.save_probe_findings(probe_id, user_id, finding_rows)

        await db.update_probe_status(
            probe_id, "completed",
            completed_at=completed_iso,
            duration_seconds=results.get("duration_seconds", 0.0),
        )
        logger.info(
            "Probe %s completed: score=%d, findings=%d",
            probe_id, results.get("probe_score", 0), results.get("total_findings", 0),
        )
    except Exception as exc:
        logger.exception("Probe %s failed: %s", probe_id, exc)
        try:
            await db.update_probe_status(
                probe_id, "failed",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            logger.exception("Failed to update probe status after error for %s", probe_id)



# ------------------------------------------------------------------ #
# POST /api/probe/authorize
# ------------------------------------------------------------------ #


@router.post("/probe/authorize")
@limiter.limit(rate_limit_string())
async def authorize_domain(body: AuthorizeRequest, request: Request) -> dict:
    """Generate a verification token for domain ownership. Requires auth."""
    if not settings.probe_enabled:
        raise HTTPException(status_code=503, detail="Live probing is not enabled")
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to use domain verification")
    user_id: str = request.state.user_id
    domain = extract_domain(str(body.target_url))
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid target URL")

    # Check if already authorized
    if await is_authorized(user_id, domain, db):
        return {
            "domain": domain,
            "token": "",
            "method": "already_verified",
            "instructions": "Domain is already verified.",
        }

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
    """Verify domain ownership via the chosen method. Requires auth."""
    if not settings.probe_enabled:
        raise HTTPException(status_code=503, detail="Live probing is not enabled")
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to use domain verification")
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
    user_id = _get_user_id(request)
    authenticated = _is_authenticated(request)

    if not settings.probe_enabled:
        raise HTTPException(status_code=503, detail="Live probing is not enabled")

    if not settings.probe_service_url:
        raise HTTPException(status_code=503, detail="Probe service not configured")

    profile = db.get_user_profile(user_id) if authenticated else None
    role = profile.get("role", "user") if profile else "user"
    onboarded = bool(profile and profile.get("onboarding_complete"))

    # Enforce free-tier limit for anonymous and non-onboarded users
    if not onboarded:
        existing_probes = await db.list_user_probes(user_id, limit=FREE_PROBE_LIMIT + 1)
        if len(existing_probes) >= FREE_PROBE_LIMIT:
            msg = (
                f"Free probe limit reached ({FREE_PROBE_LIMIT}). Sign up for unlimited probes."
                if not authenticated
                else f"Free probe limit reached ({FREE_PROBE_LIMIT}). Complete onboarding for unlimited probes."
            )
            raise HTTPException(status_code=403, detail=msg)

    domain = extract_domain(str(body.target_url))
    if not domain:
        raise HTTPException(status_code=400, detail="Invalid target URL")

    # Domain authorization — skip for anonymous users (public URL scanning)
    auth_method: str | None = None
    if not authenticated:
        auth_method = "anonymous"
    elif role in ("developer", "beta_tester"):
        existing = await db.get_authorized_target(user_id, domain)
        if not existing:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            await db.save_authorized_target(user_id, domain, "manual_approve", expires_at)
        auth_method = "manual_approve"
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
        "auth_method": auth_method,
    }
    if body.project_id:
        probe_data["project_id"] = str(body.project_id)

    await db.create_probe(probe_data)

    background_tasks.add_task(_run_probe, probe_id, str(body.target_url), user_id, body.probe_type, body.config)

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
    """Return probe status and results. Public — UUID is unguessable."""
    probe = await db.get_probe(probe_id)
    if not probe:
        raise HTTPException(status_code=404, detail="Probe not found")
    return probe


# ------------------------------------------------------------------ #
# GET /api/probe/{probe_id}/findings
# ------------------------------------------------------------------ #


@router.get("/probe/{probe_id}/findings")
@limiter.limit(rate_limit_string())
async def get_probe_findings(probe_id: str, request: Request) -> list[dict]:
    """Return all findings for a probe. Requires auth — detailed findings are gated."""
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to view detailed findings")
    user_id: str = request.state.user_id
    probe = await db.get_probe(probe_id, user_id)
    if not probe:
        raise HTTPException(status_code=404, detail="Probe not found")
    return await db.get_probe_findings(probe_id, user_id)


# ------------------------------------------------------------------ #
# GET /api/probe/quota
# ------------------------------------------------------------------ #


@router.get("/probe/quota")
@limiter.limit(rate_limit_string())
async def probe_quota(request: Request) -> dict:
    """Return remaining free probes. Works for both anonymous and authenticated users."""
    user_id = _get_user_id(request)
    authenticated = _is_authenticated(request)
    if authenticated:
        profile = db.get_user_profile(user_id)
        if profile and profile.get("onboarding_complete"):
            return {"onboarded": True, "remaining": -1, "limit": -1}
    used = len(await db.list_user_probes(user_id, limit=FREE_PROBE_LIMIT + 1))
    return {
        "onboarded": False,
        "remaining": max(0, FREE_PROBE_LIMIT - used),
        "limit": FREE_PROBE_LIMIT,
    }


# ------------------------------------------------------------------ #
# GET /api/user/probes
# ------------------------------------------------------------------ #


@router.get("/user/probes")
@limiter.limit(rate_limit_string())
async def list_probes(request: Request) -> list[dict]:
    """Return the authenticated user's probes. Requires auth."""
    if not _is_authenticated(request):
        raise HTTPException(status_code=401, detail="Sign in to view probe history")
    user_id: str = request.state.user_id
    return await db.list_user_probes(user_id)
