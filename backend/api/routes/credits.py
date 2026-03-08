"""Wallet management routes: balance, deposits, Stripe checkout, and webhook."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, HTTPException, Request
from starlette.responses import JSONResponse

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from models.credits import (
    DEPOSIT_OPTIONS,
    MIN_DEPOSIT_CENTS,
    DepositRequest,
    WalletBalance,
)
import services.supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/credits")
@limiter.limit(rate_limit_string())
async def get_balance(request: Request) -> dict:
    """Return the authenticated user's wallet balance and recent transactions."""
    user_id: str = request.state.user_id
    balance = db.get_user_balance(user_id)
    transactions = db.get_credit_transactions(user_id)
    return WalletBalance(balance_usd=balance, transactions=transactions).model_dump()


@router.get("/credits/packages")
@limiter.limit(rate_limit_string())
async def get_deposit_options(request: Request) -> list[dict]:
    """Return suggested deposit amounts."""
    return DEPOSIT_OPTIONS


@router.post("/credits/checkout")
@limiter.limit(rate_limit_string())
async def create_checkout(request_body: DepositRequest, request: Request) -> dict:
    """Create a Stripe Checkout Session for a wallet deposit."""
    user_id: str = request.state.user_id

    if request_body.amount_cents < MIN_DEPOSIT_CENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum deposit is ${MIN_DEPOSIT_CENTS / 100:.2f}",
        )

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    stripe.api_key = settings.stripe_secret_key

    amount_dollars = request_body.amount_cents / 100

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": request_body.amount_cents,
                    "product_data": {
                        "name": f"Vibe2Prod Wallet — ${amount_dollars:.2f}",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "user_id": user_id,
            "deposit_amount_cents": str(request_body.amount_cents),
        },
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
        amount_cents_str = metadata.get("deposit_amount_cents")

        if not user_id or not amount_cents_str:
            logger.warning("Stripe webhook missing metadata: %s", metadata)
            return JSONResponse(content={"status": "ignored"})

        amount_usd = int(amount_cents_str) / 100

        db.add_balance(
            user_id=user_id,
            amount_usd=amount_usd,
            stripe_session_id=session.get("id"),
            description=f"Deposit: ${amount_usd:.2f}",
        )
        logger.info(
            "Added $%.2f to wallet for user %s",
            amount_usd, user_id,
        )

    return JSONResponse(content={"status": "ok"})
