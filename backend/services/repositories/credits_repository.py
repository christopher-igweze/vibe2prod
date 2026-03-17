"""Wallet/credit balance operations."""

from __future__ import annotations

from services.repositories._base import _client


def get_user_balance(user_id: str) -> float:
    """Return the user's current USD wallet balance."""
    client = _client()
    row = (
        client.table("profiles")
        .select("balance_usd")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return 0.0
    return float(row.data[0].get("balance_usd", 0))


def deduct_balance(
    user_id: str,
    amount: float,
    scan_id: str | None = None,
    description: str | None = None,
) -> float:
    """Deduct a USD amount from the user's wallet and log a usage transaction.

    Raises ValueError if the user has insufficient balance.
    Returns the new balance.
    """
    client = _client()
    current = get_user_balance(user_id)
    if current < amount:
        raise ValueError(f"Insufficient balance: ${current:.2f} < ${amount:.2f}")

    new_balance = round(current - amount, 4)
    client.table("profiles").update(
        {"balance_usd": new_balance}
    ).eq("user_id", str(user_id)).execute()

    tx: dict = {
        "user_id": str(user_id),
        "amount": round(-amount, 4),
        "balance_after": new_balance,
        "type": "usage",
    }
    if scan_id:
        tx["scan_id"] = scan_id
    if description:
        tx["description"] = description
    client.table("credit_transactions").insert(tx).execute()

    return new_balance


def add_balance(
    user_id: str,
    amount_usd: float,
    stripe_session_id: str | None = None,
    description: str | None = None,
) -> float:
    """Add USD to a user's wallet balance and log a purchase transaction.

    Returns the new balance.
    """
    client = _client()
    current = get_user_balance(user_id)
    new_balance = round(current + amount_usd, 4)

    client.table("profiles").update(
        {"balance_usd": new_balance}
    ).eq("user_id", str(user_id)).execute()

    tx: dict = {
        "user_id": str(user_id),
        "amount": round(amount_usd, 4),
        "balance_after": new_balance,
        "type": "purchase",
    }
    if stripe_session_id:
        tx["stripe_session_id"] = stripe_session_id
    if description:
        tx["description"] = description
    client.table("credit_transactions").insert(tx).execute()

    return new_balance


def get_credit_transactions(user_id: str, limit: int = 20) -> list[dict]:
    """Return recent credit transactions for a user, newest first."""
    client = _client()
    row = (
        client.table("credit_transactions")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return row.data or []
