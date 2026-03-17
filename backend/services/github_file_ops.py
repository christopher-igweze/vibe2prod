"""GitHub file reading and content fetching operations.

Extracted from github.py for single-responsibility.
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException

from services.github_repository_ops import _handle_github_network_error


async def fetch_github_profile(access_token: str) -> tuple[str | None, str | None]:
    """Fetch GitHub user profile using access token."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                },
            )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)
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


async def exchange_code_for_access_token(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Exchange OAuth code for access token."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "state": state,
                },
            )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e, context="GitHub OAuth service")
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
