"""Beta access activation endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, HTTPException

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from services import supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/beta/activate")
@limiter.limit(rate_limit_string())
async def activate_beta(request: Request) -> dict:
    """Activate beta access for the authenticated user.

    Validates the beta code, auto-creates profile if missing,
    then upgrades user role to 'beta_tester'.
    """
    user_id: str = request.state.user_id

    body = await request.json()
    code = body.get("code", "")

    if not settings.beta_access_code:
        raise HTTPException(status_code=503, detail="Beta activation not configured")

    if code != settings.beta_access_code:
        raise HTTPException(status_code=403, detail="Invalid beta code")

    profile = db.get_user_profile(user_id)

    # Auto-create profile if Clerk webhook hasn't fired yet
    if not profile:
        logger.info("Beta activate: creating missing profile for user %s", user_id)
        await db.upsert_profile_from_clerk(user_id=user_id, email="")
        profile = db.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=500, detail="Failed to create profile")

    current_role = profile.get("role", "user")
    if current_role in ("beta_tester", "developer"):
        return {"status": "already_active", "role": current_role}

    upgraded = await db.upgrade_user_role(user_id, "beta_tester")
    if not upgraded:
        raise HTTPException(status_code=500, detail="Failed to upgrade role")

    logger.info("Beta activated for user %s", user_id)
    return {"status": "activated", "role": "beta_tester"}
