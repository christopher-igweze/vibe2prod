"""GitHub OAuth service — OAuth flow and GitHub API integration.

This service handles the business logic for GitHub OAuth authentication,
including token exchange, profile fetching, and repository operations.
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlparse, parse_qs

import httpx
import jwt
from fastapi import HTTPException

from config import settings
from services.http_client import shared_client


# ------------------------------------------------------------------ #
# OAuth configuration helpers
# ------------------------------------------------------------------ #


def oauth_not_configured() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "github_oauth_not_configured",
            "message": "GitHub OAuth is not configured on the backend.",
        },
    )


def state_secret() -> str:
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


def ensure_oauth_configured() -> None:
    if not settings.github_client_id or not settings.github_client_secret:
        raise oauth_not_configured()


def validate_redirect_uri(redirect_uri: str) -> None:
    """Ensure redirect_uri origin is in the allowlist (skips if no allowlist configured)."""
    allowed_raw = settings.github_oauth_allowed_redirect_origins
    if not allowed_raw:
        return
    allowed = {o.strip().rstrip("/") for o in allowed_raw.split(",") if o.strip()}
    parsed = urlparse(redirect_uri)
    origin = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        origin += f":{parsed.port}"
    if origin not in allowed:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "redirect_uri_not_allowed",
                "message": "The redirect_uri origin is not in the allowed list.",
            },
        )


# ------------------------------------------------------------------ #
# State token management
# ------------------------------------------------------------------ #


def encode_state(user_id: str, redirect_uri: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "redirect_uri": redirect_uri,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.github_oauth_state_ttl_minutes)).timestamp()
        ),
    }
    return jwt.encode(payload, state_secret(), algorithm="HS256")


def decode_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, state_secret(), algorithms=["HS256"])
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


# ------------------------------------------------------------------ #
# GitHub API operations
# ------------------------------------------------------------------ #


async def exchange_code_for_access_token(
    *,
    code: str,
    redirect_uri: str,
    state: str,
) -> str:
    ensure_oauth_configured()
    try:
        resp = await shared_client.post(
            "https://github.com/login/oauth/access_token",
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


def parse_link_header(link_header: str | None) -> str | None:
    """Parse GitHub's Link header to extract the next cursor.
    
    GitHub returns pagination info in the Link header like:
    <https://api.github.com/user/repos?page=2&per_page=30>; rel="next"
    
    Returns the cursor value for the 'next' page, or None if there's no next page.
    """
    if not link_header:
        return None
    
    # Parse the Link header - format: <url>; rel="rel_type", <url>; rel="rel_type"
    links = {}
    for part in link_header.split(","):
        part = part.strip()
        if ">" in part and 'rel="' in part:
            url_part, rel_part = part.split(";", 1)
            url = url_part.strip().strip("<>")
            rel = rel_part.strip().split("=")[1].strip('"')
            links[rel] = url
    
    next_url = links.get("next")
    if next_url:
        # Extract cursor from URL query params
        parsed = urlparse(next_url)
        query_params = parse_qs(parsed.query)
        cursors = query_params.get("cursor")
        if cursors:
            return cursors[0]
    return None


async def list_repositories(
    token: str,
    page: int = 1,
    per_page: int = 30,
    cursor: str | None = None,
) -> tuple[list[dict], str | None]:
    """List the authenticated user's GitHub repositories.
    
    Returns a tuple of (repo_list, next_cursor).
    """
    params = {
        "sort": "updated",
        "direction": "desc",
        "per_page": min(per_page, 100),
        "affiliation": "owner,collaborator,organization_member",
    }
    
    if cursor:
        params["cursor"] = cursor
    else:
        params["page"] = page

    try:
        resp = await shared_client.get(
            "https://api.github.com/user/repos",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
            params=params,
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

    if resp.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail={"code": "github_token_expired", "message": "GitHub token is invalid or expired. Reconnect in Settings."},
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"code": "github_api_error", "message": "GitHub API error."})

    repos = resp.json()
    
    link_header = resp.headers.get("Link") or resp.headers.get("link")
    next_cursor = parse_link_header(link_header)
    
    repo_list = [
        {
            "full_name": r["full_name"],
            "name": r["name"],
            "owner": r["owner"]["login"],
            "private": r["private"],
            "url": r["html_url"],
            "description": r.get("description") or "",
            "language": r.get("language") or "",
            "updated_at": r.get("updated_at") or "",
            "default_branch": r.get("default_branch", "main"),
        }
        for r in repos
    ]
    
    return repo_list, next_cursor


async def list_branches(
    token: str,
    owner: str,
    repo: str,
    page: int = 1,
    per_page: int = 30,
) -> list[dict]:
    """List branches for a specific GitHub repository."""
    try:
        resp = await shared_client.get(
            f"https://api.github.com/repos/{owner}/{repo}/branches",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
            params={
                "per_page": min(per_page, 100),
                "page": page,
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

    if resp.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "github_token_expired",
                "message": "GitHub token is invalid or expired. Reconnect in Settings.",
            },
        )
    if resp.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail={"code": "repo_not_found", "message": "Repository not found."},
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={"code": "github_api_error", "message": "GitHub API error."},
        )

    branches = resp.json()
    return [
        {
            "name": b["name"],
            "protected": b.get("protected", False),
        }
        for b in branches
    ]


async def check_connection(token: str) -> tuple[bool, str | None, str | None]:
    """Check if GitHub connection is valid.
    
    Returns (connected, github_username, avatar_url).
    """
    try:
        resp = await shared_client.get(
            "https://api.github.com/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
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

    if resp.status_code != 200:
        return False, None, None

    data = resp.json()
    return True, data.get("login"), data.get("avatar_url")
