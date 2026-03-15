"""GitHub OAuth exchange and connection lifecycle routes."""

from __future__ import annotations

import hmac
from typing import Literal
from urllib.parse import urlencode, urlparse

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from urllib.parse import urlencode

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from services import supabase_client as db
from services import github as github_service

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
        github_oauth_service.ensure_oauth_configured()
        github_oauth_service.validate_redirect_uri(request_body.redirect_uri)
        state = github_oauth_service.encode_state(user_id=user_id, redirect_uri=request_body.redirect_uri)
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

        state_payload = github_oauth_service.decode_state(request_body.state)
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(state_payload.get("sub", ""), user_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "oauth_state_user_mismatch",
                    "message": "GitHub OAuth state does not belong to this user.",
                },
            )
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(state_payload.get("redirect_uri", ""), request_body.redirect_uri):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_redirect_mismatch",
                    "message": "GitHub OAuth redirect URI mismatch.",
                },
            )

        _ensure_oauth_configured()
        access_token = await github_service.exchange_code_for_access_token(
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            code=request_body.code,
            redirect_uri=request_body.redirect_uri,
            state=request_body.state,
        )
        github_username, avatar_url = await github_service.fetch_github_profile(access_token)
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
async def list_github_repos(
    request: Request,
    page: int = 1,
    per_page: int = 30,
    cursor: str | None = None,
    paginated: bool = False,
):
    """List the authenticated user's GitHub repositories.
    
    Supports both page-based and cursor-based pagination.
    For large result sets, prefer using cursor-based pagination for better performance.
    
    Args:
        page: Page number for page-based pagination (used when cursor is not provided)
        per_page: Number of repos per page (max 100)
        cursor: Cursor for cursor-based pagination (preferred for large result sets)
        paginated: If true, returns a paginated response with next_cursor and has_more
    """
    user_id: str = request.state.user_id
    token = await db.get_github_access_token(user_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail={"code": "github_not_connected", "message": "GitHub is not connected."},
        )

    repos, pagination = await github_service.list_user_repos(
        token=token,
        page=page,
        per_page=per_page,
        cursor=cursor,
    )
    
    repo_list = [
        {
            "full_name": r.full_name,
            "name": r.name,
            "owner": r.owner,
            "private": r.private,
            "url": r.url,
            "description": r.description,
            "language": r.language,
            "updated_at": r.updated_at,
            "default_branch": r.default_branch,
        }
        for r in repos
    ]
    
    # Return paginated format if requested, otherwise return list for backward compatibility
    if paginated or cursor is not None:
        return {
            "repos": repo_list,
            "pagination": {
                "next_cursor": pagination.next_cursor if pagination else None,
                "has_more": pagination.has_more if pagination else False,
            },
        }
    
    return repo_list


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

    branches = await github_service.list_repo_branches(
        owner=owner,
        repo=repo,
        token=token,
        page=page,
        per_page=per_page,
    )
    return [
        {
            "name": b.name,
            "protected": b.protected,
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
    github_username, avatar_url = await github_service.verify_token(token)
    
    if not github_username:
        return {"connected": False, "error": "token_expired"}

    return {
        "connected": True,
        "github_username": github_username,
        "avatar_url": avatar_url,
    }
