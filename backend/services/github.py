"""GitHub API helpers — repo metadata, cloning, PR creation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

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

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

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

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
    return data["sha"]
