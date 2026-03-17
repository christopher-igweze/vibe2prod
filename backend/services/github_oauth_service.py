"""GitHub OAuth and repository management service.

This module is a backward-compatible facade that re-exports from the
split sub-modules:
  - github_oauth_flow: OAuth flow logic (state, validation, code exchange)
  - github_token_manager: Token storage/retrieval/encryption
  - github_repository_service: Repo listing, access checking

Usage:
    from services.github_oauth_service import GitHubOAuthService

    oauth_service = GitHubOAuthService()
    token = await oauth_service.exchange_code_for_token(code, redirect_uri, state)
    repos = await oauth_service.list_repos(user_id, page, per_page, cursor)
"""

from __future__ import annotations

from config import settings  # noqa: F401 — kept for backward compat (tests patch this)

# Re-export everything from split modules for backward compatibility
from services.github_oauth_flow import (  # noqa: F401
    ensure_oauth_configured,
    validate_redirect_uri,
    encode_state,
    decode_state,
    validate_oauth_state,
    build_auth_url,
    get_auth_url,
    exchange_code_for_token,
    fetch_github_profile,
)
from services.github_token_manager import (  # noqa: F401
    get_decrypted_token,
    connect_user,
    disconnect_user,
)
from services.github_repository_service import (  # noqa: F401
    list_repos,
    list_repo_branches,
    get_connection_status,
)


class GitHubOAuthService:
    """Service for GitHub OAuth and repository management.

    Delegates to focused sub-modules. Kept for backward compatibility
    with code that instantiates and calls methods on this class.
    """

    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_OAUTH_BASE = "https://github.com/login/oauth"

    async def _get_decrypted_token(self, user_id: str) -> str | None:
        return await get_decrypted_token(user_id)

    def _ensure_oauth_configured(self) -> None:
        ensure_oauth_configured()

    def _validate_redirect_uri(self, redirect_uri: str) -> None:
        validate_redirect_uri(redirect_uri)

    def _encode_state(self, user_id: str, redirect_uri: str) -> str:
        return encode_state(user_id=user_id, redirect_uri=redirect_uri)

    def encode_state(self, user_id: str, redirect_uri: str) -> str:
        return encode_state(user_id=user_id, redirect_uri=redirect_uri)

    def _decode_state(self, state: str) -> dict:
        return decode_state(state)

    def decode_state(self, state: str) -> dict:
        return decode_state(state)

    async def validate_oauth_state(
        self, state: str, expected_user_id: str, expected_redirect_uri: str,
    ) -> None:
        await validate_oauth_state(state, expected_user_id, expected_redirect_uri)

    def build_auth_url(self, redirect_uri: str, state: str) -> str:
        return build_auth_url(redirect_uri, state)

    def get_auth_url(self, user_id: str, redirect_uri: str) -> str:
        return get_auth_url(user_id, redirect_uri)

    async def exchange_code_for_token(self, code: str, redirect_uri: str, state: str) -> str:
        return await exchange_code_for_token(code, redirect_uri, state)

    async def fetch_github_profile(self, access_token: str) -> tuple[str | None, str | None]:
        return await fetch_github_profile(access_token)

    def _parse_link_header(self, link_header: str | None) -> str | None:
        from services.github_repository_service import _parse_link_header
        return _parse_link_header(link_header)

    async def list_repos(
        self, user_id: str, page: int = 1, per_page: int = 30,
        cursor: str | None = None, paginated: bool = False,
    ) -> dict | list[dict]:
        return await list_repos(user_id, page, per_page, cursor, paginated)

    def _transform_repos(self, repos: list[dict]) -> list[dict]:
        from services.github_repository_service import _transform_repos
        return _transform_repos(repos)

    async def list_repo_branches(
        self, user_id: str, owner: str, repo: str, page: int = 1, per_page: int = 30,
    ) -> list[dict]:
        return await list_repo_branches(user_id, owner, repo, page, per_page)

    async def get_connection_status(self, user_id: str) -> dict:
        return await get_connection_status(user_id)

    async def connect_user(
        self, user_id: str, access_token: str,
        github_username: str | None = None, avatar_url: str | None = None,
    ) -> None:
        await connect_user(user_id, access_token, github_username, avatar_url)

    async def disconnect_user(self, user_id: str) -> None:
        await disconnect_user(user_id)


# Module-level singleton
github_oauth_service = GitHubOAuthService()
