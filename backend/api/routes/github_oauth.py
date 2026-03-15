"""GitHub OAuth exchange and connection lifecycle routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode, urlparse

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from services import supabase_client as db

router = APIRouter()


class GithubOAuthRequest(BaseModel):
    action: Literal["get_auth_url", "exchange_code", "disconnect"]
    code: str | None = None
    redirect_uri: str | None = None
    state: str | None = None


class GithubOAuthResponse(BaseModel):
    auth_url: str | None = None
    github_username: str | None = None
    avatar_url: str | None = None
    connected: bool = False
    message: str | None = None


def _oauth_not_configured() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "github_oauth_not_configured",
            "message": "GitHub OAuth is not configured on the backend.",
        },
    )


def _state_secret() -> str:
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


def _ensure_oauth_configured() -> None:
    if not settings.github_client_id or not settings.github_client_secret:
        raise _oauth_not_configured()


def _validate_redirect_uri(redirect_uri: str) -> None:
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


def _encode_state(user_id: str, redirect_uri: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "redirect_uri": redirect_uri,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.github_oauth_state_ttl_minutes)).timestamp()
        ),
    }
    return jwt.encode(payload, _state_secret(), algorithm="HS256")


def _decode_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, _state_secret(), algorithms=["HS256"])
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


async def _exchange_code_for_access_token(
    *,
    code: str,
    redirect_uri: str,
    state: str,
) -> str:
    _ensure_oauth_configured()
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
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


async def _fetch_github_profile(access_token: str) -> tuple[str | None, str | None]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
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


@router.post("/github-oauth", response_model=GithubOAuthResponse)
@limiter.limit(rate_limit_string())
async def github_oauth(request_body: GithubOAuthRequest, request: Request) -> GithubOAuthResponse:
    user_id: str = request.state.user_id

    if request_body.action == "disconnect":
        await db.clear_github_connection(user_id=user_id)
        return GithubOAuthResponse(connected=False, message="GitHub disconnected.")

    if request_body.action == "get_auth_url":
        if not request_body.redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={"code": "redirect_uri_required", "message": "redirect_uri is required."},
            )
        _ensure_oauth_configured()
        _validate_redirect_uri(request_body.redirect_uri)
        state = _encode_state(user_id=user_id, redirect_uri=request_body.redirect_uri)
        query = urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": request_body.redirect_uri,
                "scope": settings.github_oauth_scope,
                "state": state,
            }
        )
        return GithubOAuthResponse(
            auth_url=f"https://github.com/login/oauth/authorize?{query}",
            connected=False,
        )

    if request_body.action == "exchange_code":
        if not request_body.code:
            raise HTTPException(
                status_code=400,
                detail={"code": "code_required", "message": "code is required."},
            )
        if not request_body.redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={"code": "redirect_uri_required", "message": "redirect_uri is required."},
            )
        if not request_body.state:
            raise HTTPException(
                status_code=400,
                detail={"code": "state_required", "message": "state is required."},
            )

        state_payload = _decode_state(request_body.state)
        if state_payload.get("sub") != user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "oauth_state_user_mismatch",
                    "message": "GitHub OAuth state does not belong to this user.",
                },
            )
        if state_payload.get("redirect_uri") != request_body.redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_redirect_mismatch",
                    "message": "GitHub OAuth redirect URI mismatch.",
                },
            )

        access_token = await _exchange_code_for_access_token(
            code=request_body.code,
            redirect_uri=request_body.redirect_uri,
            state=request_body.state,
        )
        github_username, avatar_url = await _fetch_github_profile(access_token)
        await db.save_github_connection(
            user_id=user_id,
            access_token=access_token,
            github_username=github_username,
            avatar_url=avatar_url,
        )
        return GithubOAuthResponse(
            github_username=github_username,
            avatar_url=avatar_url,
            connected=True,
            message="GitHub connected.",
        )

    raise HTTPException(
        status_code=400,
        detail={"code": "action_invalid", "message": "Unsupported GitHub OAuth action."},
    )


@router.get("/github/repos")
@limiter.limit(rate_limit_string())
async def list_github_repos(request: Request, page: int = 1, per_page: int = 30):
    """List the authenticated user's GitHub repositories."""
    user_id: str = request.state.user_id
    token = await db.get_github_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail={"code": "github_not_connected", "message": "GitHub is not connected."},
        )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                },
                params={
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": min(per_page, 100),
                    "page": page,
                    # Filter to only repos the user owns, is a collaborator on,
                    # or is an organization member of. This prevents IDOR where
                    # a user could access repos their token can see but aren't
                    # linked to their Vibe2Prod account.
                    "affiliation": "owner,collaborator,organization_member",
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
            detail={"code": "github_token_expired", "message": "GitHub token is invalid or expired. Reconnect in Settings."},
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"code": "github_api_error", "message": "GitHub API error."})

    repos = resp.json()
    return [
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


@router.get("/github/repos/{owner}/{repo}/branches")
@limiter.limit(rate_limit_string())
async def list_repo_branches(
    owner: str, repo: str, request: Request, page: int = 1, per_page: int = 30
):
    """List branches for a specific GitHub repository."""
    user_id: str = request.state.user_id
    token = await db.get_github_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail={"code": "github_not_connected", "message": "GitHub is not connected."},
        )

    # Validate repository ownership to prevent IDOR
    repo_url = f"https://github.com/{owner}/{repo}"
    project = await db.get_project_by_repo_url(user_id, repo_url)
    if not project:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "repo_not_authorized",
                "message": "You don't have access to this repository. "
                "Please add the repository to your account first.",
            },
        )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
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


@router.get("/github/status")
async def github_connection_status(request: Request):
    """Check if GitHub is connected for the current user."""
    user_id: str = request.state.user_id
    token = await db.get_github_access_token(user_id)
    if not token:
        return {"connected": False}

    # Verify token is still valid
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
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
        return {"connected": False, "error": "token_expired"}

    data = resp.json()
    return {
        "connected": True,
        "github_username": github_username,
        "avatar_url": avatar_url,
    }

