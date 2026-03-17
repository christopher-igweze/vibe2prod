"""GitHub commit operations and SHA lookup.

Extracted from github.py for single-responsibility.
"""

from __future__ import annotations

import httpx
from fastapi import HTTPException

from services.github_repository_ops import _handle_github_network_error


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
        raise _handle_github_network_error(e)
    return data["sha"]


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
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "github_api_error", "message": f"GitHub API error: {e.response.status_code}"},
        )
    except httpx.RequestError as e:
        raise _handle_github_network_error(e)
