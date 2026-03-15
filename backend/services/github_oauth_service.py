"""GitHub OAuth and repository management service.

This service handles the business logic for GitHub OAuth flows,
token exchange, profile fetching, and repository operations.

Usage:
    from services.github_oauth_service import GitHubOAuthService
    
    oauth_service = GitHubOAuthService()
    token = await oauth_service.exchange_code_for_token(code, redirect_uri, state)
    repos = await oauth_service.list_repos(user_id, page, per_page, cursor)
"""

from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
import jwt
from fastapi import HTTPException

from config import settings
from services import supabase_client as db
from services.http_client import shared_client

logger = logging.getLogger(__name__)


class GitHubOAuthService:
    """Service for GitHub OAuth and repository management."""
    
    # GitHub API configuration
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_OAUTH_BASE = "https://github.com/login/oauth"
    
    def _ensure_oauth_configured(self) -> None:
        """Verify GitHub OAuth is configured."""
        if not settings.github_client_id or not settings.github_client_secret:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "github_oauth_not_configured",
                    "message": "GitHub OAuth is not configured on the backend.",
                },
            )

    def _get_state_secret(self) -> str:
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

    def _validate_redirect_uri(self, redirect_uri: str) -> None:
        """Validate redirect_uri origin is in allowlist."""
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

    def _encode_state(self, user_id: str, redirect_uri: str) -> str:
        """Encode OAuth state JWT."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "redirect_uri": redirect_uri,
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=settings.github_oauth_state_ttl_minutes)).timestamp()
            ),
        }
        return jwt.encode(payload, self._get_state_secret(), algorithm="HS256")

    def _decode_state(self, state: str) -> dict:
        """Decode and validate OAuth state JWT."""
        try:
            payload = jwt.decode(state, self._get_state_secret(), algorithms=["HS256"])
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

    def validate_oauth_state(
        self,
        state: str,
        expected_user_id: str,
        expected_redirect_uri: str,
    ) -> None:
        """Validate OAuth state matches expected user_id and redirect_uri.
        
        Uses constant-time comparison to prevent timing attacks.
        """
        state_payload = self._decode_state(state)
        
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(state_payload.get("sub", ""), expected_user_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "oauth_state_user_mismatch",
                    "message": "GitHub OAuth state does not belong to this user.",
                },
            )
        # Use constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(state_payload.get("redirect_uri", ""), expected_redirect_uri):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_redirect_mismatch",
                    "message": "GitHub OAuth redirect URI mismatch.",
                },
            )

    def build_auth_url(self, redirect_uri: str, state: str) -> str:
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

    def get_auth_url(self, user_id: str, redirect_uri: str) -> str:
        """Generate the GitHub OAuth authorization URL for a user.
        
        Args:
            user_id: The user ID to encode in the state
            redirect_uri: The redirect URI after OAuth completion
            
        Returns:
            The full authorization URL
        """
        self._ensure_oauth_configured()
        self._validate_redirect_uri(redirect_uri)
        state = self._encode_state(user_id=user_id, redirect_uri=redirect_uri)
        return self.build_auth_url(redirect_uri, state)

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        state: str,
    ) -> str:
        """Exchange OAuth authorization code for access token."""
        self._ensure_oauth_configured()
        
        try:
            resp = await shared_client.post(
                f"{self.GITHUB_OAUTH_BASE}/access_token",
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

    async def fetch_github_profile(self, access_token: str) -> tuple[str | None, str | None]:
        """Fetch GitHub user profile."""
        try:
            resp = await shared_client.get(
                f"{self.GITHUB_API_BASE}/user",
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

    def _parse_link_header(self, link_header: str | None) -> str | None:
        """Parse GitHub's Link header to extract the next cursor."""
        if not link_header:
            return None
        
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
            parsed = urlparse(next_url)
            query_params = parse_qs(parsed.query)
            cursors = query_params.get("cursor")
            if cursors:
                return cursors[0]
        return None

    async def list_repos(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 30,
        cursor: str | None = None,
        paginated: bool = False,
    ) -> dict | list[dict]:
        """List user's GitHub repositories.
        
        Supports both page-based and cursor-based pagination.
        """
        token = await db.get_github_access_token(user_id)
        if not token:
            raise HTTPException(
                status_code=404,
                detail={"code": "github_not_connected", "message": "GitHub is not connected."},
            )

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
                f"{self.GITHUB_API_BASE}/user/repos",
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
        next_cursor = self._parse_link_header(link_header)
        
        repo_list = self._transform_repos(repos)
        
        if paginated or cursor is not None:
            return {
                "repos": repo_list,
                "pagination": {
                    "next_cursor": next_cursor,
                    "has_more": next_cursor is not None,
                },
            }
        
        return repo_list

    def _transform_repos(self, repos: list[dict]) -> list[dict]:
        """Transform GitHub repo response to internal format."""
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

    async def list_repo_branches(
        self,
        user_id: str,
        owner: str,
        repo: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        """List branches for a specific repository.
        
        Validates repository ownership before fetching branches.
        """
        token = await db.get_github_access_token(user_id)
        if not token:
            raise HTTPException(
                status_code=404,
                detail={"code": "github_not_connected", "message": "GitHub is not connected."},
            )

        # Validate repository ownership
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
            resp = await shared_client.get(
                f"{self.GITHUB_API_BASE}/repos/{owner}/{repo}/branches",
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

    async def get_connection_status(self, user_id: str) -> dict:
        """Check if GitHub is connected and verify token validity."""
        token = await db.get_github_access_token(user_id)
        if not token:
            return {"connected": False}

        try:
            resp = await shared_client.get(
                f"{self.GITHUB_API_BASE}/user",
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
            "github_username": data.get("login"),
            "avatar_url": data.get("avatar_url"),
        }

    async def connect_user(
        self,
        user_id: str,
        access_token: str,
        github_username: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """Persist GitHub OAuth credentials for a user."""
        await db.save_github_connection(
            user_id=user_id,
            access_token=access_token,
            github_username=github_username,
            avatar_url=avatar_url,
        )

    async def disconnect_user(self, user_id: str) -> None:
        """Remove GitHub OAuth credentials for a user."""
        await db.clear_github_connection(user_id=user_id)


# Module-level singleton
github_oauth_service = GitHubOAuthService()
