"""Wallet-based pricing models and constants."""

from __future__ import annotations

from pydantic import BaseModel

# Pricing constants
INFRA_COST_PER_SCAN: float = 0.14  # Container + storage per scan (~1hr)
COST_MARKUP: float = 4.0           # 4x markup on raw costs
MIN_DEPOSIT_CENTS: int = 500       # $5.00 minimum deposit

# Pre-set deposit options shown on the pricing page
DEPOSIT_OPTIONS = [
    {"id": "deposit_5", "amount_cents": 500, "label": "$5"},
    {"id": "deposit_20", "amount_cents": 2000, "label": "$20"},
    {"id": "deposit_50", "amount_cents": 5000, "label": "$50"},
]


def compute_scan_charge(llm_cost_usd: float) -> dict:
    """Compute the total charge for a scan.

    Returns dict with raw_cost, infra_cost, total_before_markup, charged_amount.
    """
    infra_cost = INFRA_COST_PER_SCAN
    total_raw = llm_cost_usd + infra_cost
    charged = round(total_raw * COST_MARKUP, 4)
    return {
        "llm_cost": round(llm_cost_usd, 4),
        "infra_cost": round(infra_cost, 4),
        "total_raw": round(total_raw, 4),
        "markup": COST_MARKUP,
        "charged_amount": charged,
    }


class DepositRequest(BaseModel):
    amount_cents: int  # Must be >= MIN_DEPOSIT_CENTS


class WalletBalance(BaseModel):
    balance_usd: float
    transactions: list[dict] = []
