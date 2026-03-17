"""GitHub OAuth exchange and connection lifecycle routes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.middleware.rate_limit import limiter, rate_limit_string
from services.github_oauth_service import github_oauth_service

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


@router.post("/github-oauth", response_model=GithubOAuthResponse)
@limiter.limit(rate_limit_string())
async def github_oauth(request_body: GithubOAuthRequest, request: Request) -> GithubOAuthResponse:
    user_id: str = request.state.user_id

    if request_body.action == "disconnect":
        await github_oauth_service.disconnect_user(user_id=user_id)
        return GithubOAuthResponse(connected=False, message="GitHub disconnected.")

    if request_body.action == "get_auth_url":
        if not request_body.redirect_uri:
            raise HTTPException(
                status_code=400,
                detail={"code": "redirect_uri_required", "message": "redirect_uri is required."},
            )
        # Delegate to service for full OAuth URL generation
        auth_url = github_oauth_service.get_auth_url(
            user_id=user_id,
            redirect_uri=request_body.redirect_uri,
        )
        return GithubOAuthResponse(
            auth_url=auth_url,
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

        # Validate redirect_uri origin before proceeding with token exchange
        github_oauth_service._validate_redirect_uri(request_body.redirect_uri)

        # Delegate to service for state validation (includes user, redirect_uri,
        # and one-time-use / replay-prevention checks).
        await github_oauth_service.validate_oauth_state(
            state=request_body.state,
            expected_user_id=user_id,
            expected_redirect_uri=request_body.redirect_uri,
        )

        # Delegate token exchange and profile fetching to service
        access_token = await github_oauth_service.exchange_code_for_token(
            code=request_body.code,
            redirect_uri=request_body.redirect_uri,
            state=request_body.state,
        )
        github_username, avatar_url = await github_oauth_service.fetch_github_profile(access_token)
        
        # Delegate connection persistence to service
        await github_oauth_service.connect_user(
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
    
    # Delegate to service - it handles token retrieval and API calls
    result = await github_oauth_service.list_repos(
        user_id=user_id,
        page=page,
        per_page=per_page,
        cursor=cursor,
        paginated=paginated,
    )
    
    return result


@router.get("/github/repos/{owner}/{repo}/branches")
@limiter.limit(rate_limit_string())
async def list_repo_branches(
    owner: str, repo: str, request: Request, page: int = 1, per_page: int = 30
):
    """List branches for a specific GitHub repository."""
    user_id: str = request.state.user_id
    
    # Delegate to service - it handles token retrieval, ownership validation, and API calls
    branches = await github_oauth_service.list_repo_branches(
        user_id=user_id,
        owner=owner,
        repo=repo,
        page=page,
        per_page=per_page,
    )
    return branches


@router.get("/github/status")
async def github_connection_status(request: Request):
    """Check if GitHub is connected for the current user."""
    user_id: str = request.state.user_id
    
    # Delegate to service for connection status check
    return await github_oauth_service.get_connection_status(user_id)
