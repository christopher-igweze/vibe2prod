"""GitHub repository info, metadata, and listing operations.

Extracted from github.py for single-responsibility.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

import httpx
from fastapi import HTTPException

from constants import GITHUB_RETRY_AFTER_CONNECT, GITHUB_RETRY_AFTER_TIMEOUT

_GITHUB_HOSTS = {"github.com", "www.github.com"}
_VALID_SEGMENT = re.compile(r"^[a-zA-Z0-9._-]+$")


def _handle_github_network_error(exc: httpx.RequestError, context: str = "GitHub API") -> HTTPException:
    """Convert common httpx network exceptions to structured HTTPException responses."""
    if isinstance(exc, httpx.TimeoutException):
        return HTTPException(
            status_code=503,
            detail={
                "code": "github_timeout",
                "message": f"{context} is temporarily unavailable. Please try again later.",
                "retry_after": int(GITHUB_RETRY_AFTER_TIMEOUT),
            },
            headers={"Retry-After": GITHUB_RETRY_AFTER_TIMEOUT},
        )
    if isinstance(exc, httpx.ConnectError):
        return HTTPException(
            status_code=503,
            detail={
                "code": "github_unreachable",
                "message": "Unable to reach GitHub. Please check your connection and try again in a few moments.",
                "retry_after": int(GITHUB_RETRY_AFTER_CONNECT),
            },
            headers={"Retry-After": GITHUB_RETRY_AFTER_CONNECT},
        )
    return HTTPException(
        status_code=503,
        detail={
            "code": "github_request_error",
            "message": f"{context} is temporarily unavailable. Please try again later.",
            "retry_after": int(GITHUB_RETRY_AFTER_TIMEOUT),
        },
        headers={"Retry-After": GITHUB_RETRY_AFTER_TIMEOUT},
    )


@dataclass
class RepoInfo:
    owner: str
    name: str
    full_name: str
    default_branch: str
    clone_url: str
    private: bool


async def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL with validation."""
    parsed = urlparse(str(url))
    if parsed.hostname and parsed.hostname not in _GITHUB_HOSTS:
        raise ValueError(f"Only github.com URLs are supported, got: {parsed.hostname}")

    pattern = r"github\.com[/:](?P<owner>[^/]+)/(?P<repo>[^/.]+)"
    m = re.search(pattern, str(url))
    if not m:
        raise ValueError(f"Cannot parse GitHub repo from URL: {url}")

    owner, repo = m.group("owner"), m.group("repo")
    if not _VALID_SEGMENT.match(owner) or not _VALID_SEGMENT.match(repo):
        raise ValueError(f"Invalid characters in owner or repo name: {owner}/{repo}")

    return owner, repo


async def get_repo_info(
    owner: str, repo: str, token: str | None = None
) -> RepoInfo:
    """Fetch repository metadata from the GitHub API."""
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail={"code": "repo_not_found", "message": f"Repository {owner}/{repo} not found."},
            )
        elif e.response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail={"code": "github_rate_limited", "message": "GitHub API rate limit exceeded."},
            )
        else:
            raise HTTPException(
                status_code=502,
                detail={"code": "github_api_error", "message": f"GitHub API error: {e.response.status_code}"},
            )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)

    return RepoInfo(
        owner=owner,
        name=repo,
        full_name=data["full_name"],
        default_branch=data.get("default_branch", "main"),
        clone_url=data["clone_url"],
        private=data.get("private", False),
    )


@dataclass
class GitHubRepo:
    """GitHub repository information."""
    full_name: str
    name: str
    owner: str
    private: bool
    url: str
    description: str
    language: str
    updated_at: str
    default_branch: str


@dataclass
class RepoPagination:
    """Pagination info for repository listing."""
    next_cursor: str | None
    has_more: bool


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


async def list_user_repos(
    token: str,
    page: int = 1,
    per_page: int = 30,
    cursor: str | None = None,
) -> tuple[list[GitHubRepo], RepoPagination | None]:
    """List the authenticated user's GitHub repositories."""
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
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user/repos",
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

    repo_list = [
        GitHubRepo(
            full_name=r["full_name"],
            name=r["name"],
            owner=r["owner"]["login"],
            private=r["private"],
            url=r["html_url"],
            description=r.get("description") or "",
            language=r.get("language") or "",
            updated_at=r.get("updated_at") or "",
            default_branch=r.get("default_branch", "main"),
        )
        for r in repos
    ]

    pagination = RepoPagination(next_cursor=next_cursor, has_more=next_cursor is not None) if next_cursor or cursor else None

    return repo_list, pagination


@dataclass
class GitHubBranch:
    """GitHub branch information."""
    name: str
    protected: bool


async def list_repo_branches(
    owner: str,
    repo: str,
    token: str,
    page: int = 1,
    per_page: int = 30,
) -> list[GitHubBranch]:
    """List branches for a specific GitHub repository."""
    try:
        async with httpx.AsyncClient() as client:
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
        GitHubBranch(
            name=b["name"],
            protected=b.get("protected", False),
        )
        for b in branches
    ]


async def verify_token(token: str) -> tuple[str | None, str | None]:
    """Verify GitHub token is still valid and return user info."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)

    if resp.status_code != 200:
        return None, None

    data = resp.json()
    return data.get("login"), data.get("avatar_url")
