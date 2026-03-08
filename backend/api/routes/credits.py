"""Credit management routes: balance, packages, Stripe checkout, and webhook."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from models.credits import CREDIT_PACKAGES, CheckoutRequest, CreditBalance
from services import supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/credits")
@limiter.limit(rate_limit_string())
async def get_credits(request: Request) -> dict:
    """Return the authenticated user's credit balance and recent transactions."""
    user_id: str = request.state.user_id
    balance = db.get_user_credits(user_id)
    transactions = db.get_credit_transactions(user_id)
    return CreditBalance(scan_credits=balance, transactions=transactions).model_dump()


@router.get("/credits/packages")
@limiter.limit(rate_limit_string())
async def get_packages(request: Request) -> list[dict]:
    """Return available credit packages."""
    return CREDIT_PACKAGES


@router.post("/credits/checkout")
@limiter.limit(rate_limit_string())
async def create_checkout(request_body: CheckoutRequest, request: Request) -> dict:
    """Create a Stripe Checkout Session for the selected credit package."""
    user_id: str = request.state.user_id

    package = next(
        (p for p in CREDIT_PACKAGES if p["id"] == request_body.package_id), None
    )
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package_id")

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    stripe.api_key = settings.stripe_secret_key

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": package["price_cents"],
                    "product_data": {"name": package["label"]},
                },
                "quantity": 1,
            }
        ],
        metadata={"user_id": user_id, "package_id": package["id"]},
        success_url=f"{settings.frontend_url}/pricing?success=true",
        cancel_url=f"{settings.frontend_url}/pricing",
    )

    return {"checkout_url": session.url}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request) -> JSONResponse:
    """Handle Stripe webhook events (no auth required — signature verified)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=503, detail="Stripe webhook not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        package_id = metadata.get("package_id")

        if not user_id or not package_id:
            logger.warning("Stripe webhook missing metadata: %s", metadata)
            return JSONResponse(content={"status": "ignored"})

        package = next(
            (p for p in CREDIT_PACKAGES if p["id"] == package_id), None
        )
        if not package:
            logger.error("Unknown package_id in Stripe webhook: %s", package_id)
            return JSONResponse(content={"status": "ignored"})

        db.add_credits(
            user_id=user_id,
            amount=package["credits"],
            stripe_session_id=session.get("id"),
            package_name=package["label"],
        )
        logger.info(
            "Added %d credits for user %s (package=%s)",
            package["credits"], user_id, package_id,
        )

    return JSONResponse(content={"status": "ok"})
