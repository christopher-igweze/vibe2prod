"""Org onboarding routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from api.middleware.rate_limit import limiter, rate_limit_string
from models.onboarding import OrgOnboardingPayload
from services import supabase_client as db

router = APIRouter()

logger = logging.getLogger(__name__)


class OnboardingResponse(BaseModel):
    status: str = "ok"
    message: str = "Org onboarding saved"


@router.post("/onboarding/org", response_model=OnboardingResponse)
@limiter.limit(rate_limit_string())
async def save_org_onboarding(
    request_body: OrgOnboardingPayload,
    request: Request,
) -> OnboardingResponse:
    user_id: str = request.state.user_id
    try:
        await db.save_org_onboarding(user_id=user_id, payload=request_body.model_dump(mode="json"))
    except Exception as e:
        logger.error(f"Error saving org onboarding for user {user_id}: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    return OnboardingResponse()

