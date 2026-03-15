"""Clerk webhook handler — syncs user profiles on user.created / user.updated."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, HTTPException
from svix.webhooks import Webhook, WebhookVerificationError

from config import settings
from services import supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()

# Required Svix signature headers that must be present on every inbound event.
_REQUIRED_SVIX_HEADERS = ("svix-id", "svix-timestamp", "svix-signature")


@router.post("/webhook/clerk")
async def handle_clerk_webhook(request: Request):
    """Handle Clerk webhook events (user.created, user.updated).

    Validates the svix signature and upserts the user profile in Supabase.
    """
    if not settings.clerk_webhook_secret:
        raise HTTPException(status_code=503, detail="Clerk webhook secret not configured")

    # Validate that all required Svix signature headers are present before
    # attempting cryptographic verification.  Missing headers indicate a
    # malformed request rather than an authentic Clerk delivery.
    missing_headers = [h for h in _REQUIRED_SVIX_HEADERS if not request.headers.get(h)]
    if missing_headers:
        logger.warning(
            "Clerk webhook request missing required headers: %s",
            ", ".join(missing_headers),
        )
        raise HTTPException(
            status_code=400,
            detail=f"Missing required webhook headers: {', '.join(missing_headers)}",
        )

    body = await request.body()

    if not body:
        logger.warning("Clerk webhook received empty request body")
        raise HTTPException(status_code=400, detail="Request body must not be empty")

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

    # wh.verify() should always return a dict, but guard defensively so that
    # unexpected Svix library behaviour never causes an AttributeError.
    if not isinstance(payload, dict):
        logger.error(
            "Clerk webhook payload has unexpected type %s after verification",
            type(payload).__name__,
        )
        raise HTTPException(status_code=400, detail="Invalid webhook payload format")

    event_type = payload.get("type", "")
    data = payload.get("data")

    # Guard against a missing or non-dict data field to prevent downstream
    # AttributeError / TypeError when accessing nested keys.
    if not isinstance(data, dict):
        logger.warning(
            "Clerk webhook event=%s has missing or non-dict data field", event_type
        )
        data = {}

    if event_type in ("user.created", "user.updated"):
        user_id = data.get("id", "")
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing user id in webhook data")

        # Extract primary email — guard the list type so a non-list value
        # from a malformed payload does not raise TypeError during iteration.
        email_addresses = data.get("email_addresses", [])
        if not isinstance(email_addresses, list):
            logger.warning(
                "Clerk webhook event=%s has non-list email_addresses field; ignoring",
                event_type,
            )
            email_addresses = []

        primary_email_id = data.get("primary_email_address_id")
        email = ""
        for addr in email_addresses:
            if isinstance(addr, dict) and addr.get("id") == primary_email_id:
                email = addr.get("email_address", "")
                break

        display_name = " ".join(
            filter(None, [data.get("first_name", ""), data.get("last_name", "")])
        ).strip() or None

        avatar_url = data.get("image_url") or None

        # Extract GitHub username if connected via OAuth — guard list type.
        external_accounts = data.get("external_accounts", [])
        if not isinstance(external_accounts, list):
            logger.warning(
                "Clerk webhook event=%s has non-list external_accounts field; ignoring",
                event_type,
            )
            external_accounts = []

        github_username = None
        for account in external_accounts:
            if isinstance(account, dict) and account.get("provider") == "oauth_github":
                github_username = account.get("username")
                break

        try:
            await db.upsert_profile_from_clerk(
                user_id=user_id,
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
                github_username=github_username,
            )
        except Exception:
            logger.exception(
                "Clerk webhook %s: failed to upsert profile for user %s",
                event_type,
                user_id,
            )
            raise HTTPException(
                status_code=500, detail="Failed to process webhook event"
            )

        logger.info("Clerk webhook %s: synced profile for user %s", event_type, user_id)

    return {"status": "ok"}
