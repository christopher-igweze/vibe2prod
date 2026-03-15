"""Rate limiting for API endpoints."""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings


def _get_rate_limit_key(request: Request) -> str:
    """Return rate limit key: user_id if authenticated, otherwise IP address.

    This prevents attackers behind NAT or using IP spoofing from bypassing
    rate limits by rotating IPs, while also ensuring legitimate users
    sharing an IP (corporate networks, mobile carriers) are not unfairly
    rate limited together when authenticated.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return user_id
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key)


def rate_limit_string() -> str:
    """Return the rate limit string for the configured limit."""
    return f"{settings.rate_limit_per_minute}/minute"
