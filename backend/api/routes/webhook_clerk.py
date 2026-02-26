"""Clerk webhook handler — syncs user profiles on user.created / user.updated."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, HTTPException
from svix.webhooks import Webhook, WebhookVerificationError

from config import settings
from services import supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhook/clerk")
async def handle_clerk_webhook(request: Request):
    """Handle Clerk webhook events (user.created, user.updated).

    Validates the svix signature and upserts the user profile in Supabase.
    """
    if not settings.clerk_webhook_secret:
        raise HTTPException(status_code=503, detail="Clerk webhook secret not configured")

    body = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    try:
        wh = Webhook(settings.clerk_webhook_secret)
        payload = wh.verify(body, headers)
    except WebhookVerificationError:
        logger.warning("Clerk webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = payload.get("type", "")
    data = payload.get("data", {})

    if event_type in ("user.created", "user.updated"):
        user_id = data.get("id", "")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user id in webhook data")

        # Extract primary email
        email_addresses = data.get("email_addresses", [])
        primary_email_id = data.get("primary_email_address_id")
        email = ""
        for addr in email_addresses:
            if addr.get("id") == primary_email_id:
                email = addr.get("email_address", "")
                break

        display_name = " ".join(
            filter(None, [data.get("first_name", ""), data.get("last_name", "")])
        ).strip() or None

        avatar_url = data.get("image_url") or None

        # Extract GitHub username if connected via OAuth
        github_username = None
        for account in data.get("external_accounts", []):
            if account.get("provider") == "oauth_github":
                github_username = account.get("username")
                break

        await db.upsert_profile_from_clerk(
            user_id=user_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            github_username=github_username,
        )

        logger.info("Clerk webhook %s: synced profile for user %s", event_type, user_id)

    return {"status": "ok"}
