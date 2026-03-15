"""GitHub API helpers — repo metadata, cloning, PR creation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

import httpx
from fastapi import HTTPException

_GITHUB_HOSTS = {"github.com", "www.github.com"}
_VALID_SEGMENT = re.compile(r"^[a-zA-Z0-9._-]+$")


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
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_request_error",
                "message": "GitHub service is temporarily unavailable. Please try again later.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )

    return RepoInfo(
        owner=owner,
        name=repo,
        full_name=data["full_name"],
        default_branch=data.get("default_branch", "main"),
        clone_url=data["clone_url"],
        private=data.get("private", False),
    )


async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str,
    token: str,
) -> str:
    """Create a PR and return the HTML URL."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "Authorization": f"token {token}",
                },
                json={"title": title, "body": body, "head": head, "base": base},
            )
            resp.raise_for_status()
            return resp.json()["html_url"]
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
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "github_api_error", "message": f"GitHub API error: {e.response.status_code}"},
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_request_error",
                "message": "GitHub service is temporarily unavailable. Please try again later.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )


async def get_head_sha(
    owner: str,
    repo: str,
    branch: str,
    token: str | None = None,
) -> str:
    """Resolve the latest commit SHA for a branch."""
    headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
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
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail={"code": "branch_not_found", "message": f"Branch '{branch}' not found in {owner}/{repo}."},
            )
        else:
            raise HTTPException(
                status_code=502,
                detail={"code": "github_api_error", "message": f"GitHub API error: {e.response.status_code}"},
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "github_request_error",
                "message": "GitHub service is temporarily unavailable. Please try again later.",
                "retry_after": 30,
            },
            headers={"Retry-After": "30"},
        )
    return data["sha"]


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


async def list_user_repos(
    token: str,
    page: int = 1,
    per_page: int = 30,
    cursor: str | None = None,
) -> tuple[list[GitHubRepo], RepoPagination | None]:
    """List the authenticated user's GitHub repositories.
    
    Supports both page-based and cursor-based pagination.
    Returns tuple of (repos, pagination_info).
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
        async with httpx.AsyncClient() as client:
            resp = await client.get(
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
    
    # Parse Link header for pagination metadata
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


def _parse_link_header(link_header: str | None) -> str | None:
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
        GitHubBranch(
            name=b["name"],
            protected=b.get("protected", False),
        )
        for b in branches
    ]


async def verify_token(token: str) -> tuple[str | None, str | None]:
    """Verify GitHub token is still valid and return user info.
    
    Returns (github_username, avatar_url) or (None, None) if invalid.
    """
    try:
        async with httpx.AsyncClient() as client:
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
        return None, None

    data = resp.json()
    return data.get("login"), data.get("avatar_url")
