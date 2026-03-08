"""Credit package definitions and request/response models."""

from __future__ import annotations

from pydantic import BaseModel

CREDIT_PACKAGES = [
    {"id": "single", "credits": 1, "price_cents": 1000, "label": "1 Scan Credit"},
    {"id": "pack", "credits": 5, "price_cents": 4000, "label": "5 Scan Credits"},
    {"id": "bulk", "credits": 15, "price_cents": 9900, "label": "15 Scan Credits"},
]


class CheckoutRequest(BaseModel):
    package_id: str


class CreditBalance(BaseModel):
    scan_credits: int
    transactions: list[dict] = []
