"""GitHub repository listing and access checking.

Extracted from github_oauth_service.py for single-responsibility.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse, parse_qs

import httpx
from fastapi import HTTPException

from services import supabase_client as db
from services.github_repository_ops import _handle_github_network_error
from services.github_token_manager import get_decrypted_token
from services.http_client import shared_client

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


def _parse_link_header(link_header: str | None) -> str | None:
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


def _transform_repos(repos: list[dict]) -> list[dict]:
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


async def list_repos(
    user_id: str,
    page: int = 1,
    per_page: int = 30,
    cursor: str | None = None,
    paginated: bool = False,
) -> dict | list[dict]:
    """List user's GitHub repositories.

    Supports both page-based and cursor-based pagination.
    """
    token = await get_decrypted_token(user_id)
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
            f"{GITHUB_API_BASE}/user/repos",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
            params=params,
        )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)

    if resp.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail={"code": "github_token_expired", "message": "GitHub token is invalid or expired. Reconnect in Settings."},
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"code": "github_api_error", "message": "GitHub API error."})

    repos = resp.json()

    link_header = resp.headers.get("Link") or resp.headers.get("link")
    next_cursor = _parse_link_header(link_header)

    repo_list = _transform_repos(repos)

    if paginated or cursor is not None:
        return {
            "repos": repo_list,
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": next_cursor is not None,
            },
        }

    return repo_list


async def list_repo_branches(
    user_id: str,
    owner: str,
    repo: str,
    page: int = 1,
    per_page: int = 30,
) -> list[dict]:
    """List branches for a specific repository.

    Validates repository ownership before fetching branches.
    """
    token = await get_decrypted_token(user_id)
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
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
            params={
                "per_page": min(per_page, 100),
                "page": page,
            },
        )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)

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


async def get_connection_status(user_id: str) -> dict:
    """Check if GitHub is connected and verify token validity."""
    token = await get_decrypted_token(user_id)
    if not token:
        return {"connected": False}

    try:
        resp = await shared_client.get(
            f"{GITHUB_API_BASE}/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
            },
        )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)

    if resp.status_code != 200:
        return {"connected": False, "error": "token_expired"}

    data = resp.json()
    return {
        "connected": True,
        "github_username": data.get("login"),
        "avatar_url": data.get("avatar_url"),
    }
