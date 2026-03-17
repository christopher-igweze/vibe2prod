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
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import httpx
import jwt
from fastapi import HTTPException

from config import settings
from services import supabase_client as db
from services.http_client import shared_client
from services.token_encryption import decrypt_token, encrypt_token, is_encrypted

logger = logging.getLogger(__name__)


class GitHubOAuthService:
    """Service for GitHub OAuth and repository management."""

    # GitHub API configuration
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_OAUTH_BASE = "https://github.com/login/oauth"

    # Simple in-memory TTL cache for repo listings to avoid hammering
    # GitHub's API on repeated dashboard loads.
    _REPO_CACHE_TTL_SECONDS = 60
    _repo_cache: dict[str, tuple[float, Any]] = {}  # key -> (expiry, data)
    
    async def _get_decrypted_token(self, user_id: str) -> str | None:
        """Retrieve and decrypt the stored GitHub access token for a user.

        Handles legacy plaintext tokens gracefully: if the stored value does
        not look encrypted it is returned as-is (migration path).
        """
        raw = await db.get_github_access_token(user_id)
        if not raw:
            return None
        if is_encrypted(raw):
            try:
                return decrypt_token(raw, settings.github_token_encryption_key)
            except Exception:
                logger.exception(
                    "Failed to decrypt GitHub token for user %s — token may be corrupt",
                    user_id,
                )
                return None
        # Legacy plaintext token — return as-is
        return raw

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
        """Encode OAuth state JWT.

        A unique ``jti`` (JWT ID) nonce is embedded so that each state token
        can be individually tracked and marked as consumed after first use,
        preventing replay attacks within the TTL window (CWE-613).
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "redirect_uri": redirect_uri,
            # Cryptographically random nonce — used as the consumption key.
            "jti": secrets.token_urlsafe(32),
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=settings.github_oauth_state_ttl_minutes)).timestamp()
            ),
        }
        return jwt.encode(payload, self._get_state_secret(), algorithm="HS256")

    # Public alias so tests and module-level shims can call encode_state directly.
    def encode_state(self, user_id: str, redirect_uri: str) -> str:
        """Public alias for :meth:`_encode_state`."""
        return self._encode_state(user_id=user_id, redirect_uri=redirect_uri)

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

    # Public alias so tests and module-level shims can call decode_state directly.
    def decode_state(self, state: str) -> dict:
        """Public alias for :meth:`_decode_state`."""
        return self._decode_state(state)

    async def validate_oauth_state(
        self,
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

        The state token is marked consumed *after* all field checks pass so
        that a mismatch error does not silently burn the nonce.
        """
        if not expected_user_id:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_missing_user",
                    "message": "Cannot validate OAuth state without an authenticated user.",
                },
            )

        state_payload = self._decode_state(state)

        # Use constant-time comparison to prevent timing attacks.
        if not hmac.compare_digest(state_payload.get("sub", ""), expected_user_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "oauth_state_user_mismatch",
                    "message": "GitHub OAuth state does not belong to this user.",
                },
            )
        # Use constant-time comparison to prevent timing attacks.
        if not hmac.compare_digest(state_payload.get("redirect_uri", ""), expected_redirect_uri):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_redirect_mismatch",
                    "message": "GitHub OAuth redirect URI mismatch.",
                },
            )

        # Replay-attack prevention: each state token may only be used once.
        jti = state_payload.get("jti")
        if not jti:
            # Tokens without a jti were issued before this fix — reject them to
            # enforce forward-only security posture.
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_missing_nonce",
                    "message": "GitHub OAuth state is missing a required nonce. "
                    "Please restart the authorization flow.",
                },
            )

        already_consumed = await db.is_oauth_state_consumed(jti)
        if already_consumed:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "oauth_state_already_used",
                    "message": "This GitHub OAuth state has already been used. "
                    "Please restart the authorization flow.",
                },
            )

        # Mark the nonce as consumed.  TTL mirrors the JWT expiry so the row
        # is automatically eligible for cleanup after the token would have
        # expired anyway.
        await db.consume_oauth_state(
            jti=jti,
            user_id=expected_user_id,
            ttl_minutes=settings.github_oauth_state_ttl_minutes,
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

    def _repo_cache_key(
        self, user_id: str, page: int, per_page: int, cursor: str | None
    ) -> str:
        """Build a deterministic cache key for a repo list request."""
        return f"{user_id}:{page}:{per_page}:{cursor or ''}"

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
        Results are cached in-memory for 60 seconds to reduce GitHub API load.
        """
        # Check TTL cache
        cache_key = self._repo_cache_key(user_id, page, per_page, cursor)
        cached = self._repo_cache.get(cache_key)
        if cached:
            expiry, data = cached
            if time.monotonic() < expiry:
                return data
            else:
                del self._repo_cache[cache_key]

        token = await self._get_decrypted_token(user_id)
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
            result: dict | list[dict] = {
                "repos": repo_list,
                "pagination": {
                    "next_cursor": next_cursor,
                    "has_more": next_cursor is not None,
                },
            }
        else:
            result = repo_list

        # Populate cache
        self._repo_cache[cache_key] = (
            time.monotonic() + self._REPO_CACHE_TTL_SECONDS,
            result,
        )
        return result

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
        token = await self._get_decrypted_token(user_id)
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
        token = await self._get_decrypted_token(user_id)
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
        """Persist GitHub OAuth credentials for a user.

        The access token is encrypted with AES-256-GCM before storage so that
        a database compromise does not expose usable GitHub tokens.
        """
        encrypted = encrypt_token(access_token, settings.github_token_encryption_key)
        await db.save_github_connection(
            user_id=user_id,
            access_token=encrypted,
            github_username=github_username,
            avatar_url=avatar_url,
        )

    async def disconnect_user(self, user_id: str) -> None:
        """Remove GitHub OAuth credentials for a user."""
        await db.clear_github_connection(user_id=user_id)


# Module-level singleton
github_oauth_service = GitHubOAuthService()

# ---------------------------------------------------------------------------
# Module-level function shims
#
# These thin wrappers delegate to the singleton instance so that other modules
# and tests can import individual helpers from this module without going
# through the class, matching the interface expected by the refactoring tests.
# ---------------------------------------------------------------------------


def ensure_oauth_configured() -> None:
    """Module-level shim for :meth:`GitHubOAuthService._ensure_oauth_configured`."""
    github_oauth_service._ensure_oauth_configured()


def validate_redirect_uri(redirect_uri: str) -> None:
    """Module-level shim for :meth:`GitHubOAuthService._validate_redirect_uri`."""
    github_oauth_service._validate_redirect_uri(redirect_uri)


def encode_state(user_id: str, redirect_uri: str) -> str:
    """Module-level shim for :meth:`GitHubOAuthService.encode_state`."""
    return github_oauth_service.encode_state(user_id=user_id, redirect_uri=redirect_uri)


def decode_state(state: str) -> dict:
    """Module-level shim for :meth:`GitHubOAuthService.decode_state`."""
    return github_oauth_service.decode_state(state)
