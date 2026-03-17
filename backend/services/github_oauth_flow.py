"""GitHub OAuth flow logic — state generation, validation, code exchange.

Extracted from github_oauth_service.py for single-responsibility.
"""

from __future__ import annotations

import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from fastapi import HTTPException

from config import settings
from services.http_client import shared_client
from services import supabase_client as db

logger = logging.getLogger(__name__)

# GitHub API endpoints
GITHUB_OAUTH_BASE = "https://github.com/login/oauth"


def ensure_oauth_configured() -> None:
    """Verify GitHub OAuth is configured."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_oauth_not_configured",
                "message": "GitHub OAuth is not configured on the backend.",
            },
        )


def _get_state_secret() -> str:
    """Get the OAuth state secret."""
    if not settings.github_oauth_state_secret:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_oauth_state_secret_missing",
                "message": "GitHub OAuth state secret is not configured. "
                "Set GITHUB_OAUTH_STATE_SECRET in the environment.",
            },
        )
    return settings.github_oauth_state_secret


def validate_redirect_uri(redirect_uri: str) -> None:
    """Validate redirect_uri origin is in allowlist.

    Requires ``github_oauth_allowed_redirect_origins`` to be configured.
    An empty allowlist blocks all redirect URIs to prevent open-redirect
    abuse (CWE-601).
    """
    allowed_raw = settings.github_oauth_allowed_redirect_origins
    if not allowed_raw:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "redirect_origins_not_configured",
                "message": "GitHub OAuth redirect origins are not configured on the backend.",
            },
        )
    allowed = {o.strip().rstrip("/") for o in allowed_raw.split(",") if o.strip()}
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "redirect_origins_not_configured",
                "message": "GitHub OAuth redirect origins are not configured on the backend.",
            },
        )
    parsed = urlparse(redirect_uri)
    if not parsed.scheme or not parsed.hostname:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "redirect_uri_invalid",
                "message": "The redirect_uri is not a valid URL.",
            },
        )
    # Enforce HTTPS in production; allow HTTP only for localhost development
    is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1")
    if parsed.scheme != "https" and not is_localhost:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "redirect_uri_scheme_invalid",
                "message": "redirect_uri must use HTTPS for non-localhost origins.",
            },
        )
    origin = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        origin += f":{parsed.port}"
    # Use constant-time comparison against each allowed origin to prevent
    # timing side-channel attacks that could reveal the allowlist (CWE-208).
    if not any(hmac.compare_digest(origin, a) for a in allowed):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "redirect_uri_not_allowed",
                "message": "The redirect_uri origin is not in the allowed list.",
            },
        )


def encode_state(user_id: str, redirect_uri: str) -> str:
    """Encode OAuth state JWT.

    A unique ``jti`` (JWT ID) nonce is embedded so that each state token
    can be individually tracked and marked as consumed after first use,
    preventing replay attacks within the TTL window (CWE-613).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "redirect_uri": redirect_uri,
        "jti": secrets.token_urlsafe(32),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.github_oauth_state_ttl_minutes)).timestamp()
        ),
    }
    return jwt.encode(payload, _get_state_secret(), algorithm="HS256")


def decode_state(state: str) -> dict:
    """Decode and validate OAuth state JWT."""
    try:
        payload = jwt.decode(state, _get_state_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_expired",
                "message": "GitHub OAuth state has expired. Start the flow again.",
            },
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_invalid",
                "message": "GitHub OAuth state is invalid.",
            },
        ) from exc
    return payload


async def validate_oauth_state(
    state: str,
    expected_user_id: str,
    expected_redirect_uri: str,
) -> None:
    """Validate OAuth state matches expected user_id and redirect_uri.

    Performs three layers of validation:
    1. JWT signature and expiry (prevents forgery and stale tokens).
    2. Constant-time ``sub`` / ``redirect_uri`` comparison (prevents timing
       attacks and IDOR / open-redirect abuse).
    3. One-time-use enforcement via a per-``jti`` consumption record stored
       in the database (prevents replay attacks within the TTL window,
       addressing CWE-613).
    """
    if not expected_user_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_missing_user",
                "message": "Cannot validate OAuth state without an authenticated user.",
            },
        )

    state_payload = decode_state(state)

    if not hmac.compare_digest(state_payload.get("sub", ""), expected_user_id):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "oauth_state_user_mismatch",
                "message": "GitHub OAuth state does not belong to this user.",
            },
        )
    if not hmac.compare_digest(state_payload.get("redirect_uri", ""), expected_redirect_uri):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_redirect_mismatch",
                "message": "GitHub OAuth redirect URI mismatch.",
            },
        )

    jti = state_payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_missing_nonce",
                "message": "GitHub OAuth state is missing a required nonce. "
                "Please restart the authorization flow.",
            },
        )

    # Atomic check-and-consume: a single INSERT with a UNIQUE constraint on
    # jti ensures that concurrent requests cannot both succeed.  If the row
    # already exists the INSERT raises a unique-violation which we translate
    # to "already used".  This eliminates the TOCTOU race between the old
    # SELECT-then-INSERT pattern (F-ac4b695e).
    consumed = await db.consume_oauth_state_atomic(
        jti=jti,
        user_id=expected_user_id,
        ttl_minutes=settings.github_oauth_state_ttl_minutes,
    )
    if not consumed:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "oauth_state_already_used",
                "message": "This GitHub OAuth state has already been used. "
                "Please restart the authorization flow.",
            },
        )


def build_auth_url(redirect_uri: str, state: str) -> str:
    """Build the GitHub OAuth authorization URL."""
    query = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": redirect_uri,
            "scope": settings.github_oauth_scope,
            "state": state,
        }
    )
    return f"https://github.com/login/oauth/authorize?{query}"


def get_auth_url(user_id: str, redirect_uri: str) -> str:
    """Generate the GitHub OAuth authorization URL for a user."""
    ensure_oauth_configured()
    validate_redirect_uri(redirect_uri)
    state = encode_state(user_id=user_id, redirect_uri=redirect_uri)
    return build_auth_url(redirect_uri, state)


async def exchange_code_for_token(
    code: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Exchange OAuth authorization code for access token."""
    ensure_oauth_configured()

    try:
        resp = await shared_client.post(
            f"{GITHUB_OAUTH_BASE}/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "state": state,
            },
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_timeout",
                "message": "GitHub OAuth service is temporarily unavailable. Please try again later.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_unreachable",
                "message": "Unable to reach GitHub. Please check your connection and try again in a few moments.",
                "retry_after": 60,
            },
            headers={"Retry-After": "60"},
        )

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "github_token_exchange_failed",
                "message": "GitHub token exchange failed. Please try again.",
            },
        )

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "github_token_missing",
                "message": data.get("error_description")
                or "GitHub did not return an access token.",
            },
        )
    return token


async def fetch_github_profile(access_token: str) -> tuple[str | None, str | None]:
    """Fetch GitHub user profile."""
    try:
        resp = await shared_client.get(
            "https://api.github.com/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_timeout",
                "message": "GitHub API is temporarily unavailable. Please try again later.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_unreachable",
                "message": "Unable to reach GitHub. Please check your connection and try again in a few moments.",
                "retry_after": 60,
            },
            headers={"Retry-After": "60"},
        )

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "github_profile_fetch_failed",
                "message": "Failed to fetch GitHub profile after OAuth exchange.",
            },
        )

    data = resp.json()
    return data.get("login"), data.get("avatar_url")
