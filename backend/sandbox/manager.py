"""Daytona sandbox lifecycle manager.

Provisions ephemeral Docker sandboxes for each audit session.  Agents
clone repos, run commands, and inspect output inside these sandboxes.
Sandboxes auto-delete after ``sandbox_timeout_minutes`` of inactivity.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from uuid import UUID

import httpx
from daytona import (
    Daytona,
    DaytonaConfig,
    CreateSandboxFromImageParams,
    Image,
    Resources,
    Sandbox,
)
from daytona.common.errors import DaytonaError

from config import settings
from collections.abc import Callable

from sandbox.executor import CommandResult, SandboxExecutor

logger = logging.getLogger(__name__)


async def _resolve_forge_sha(
    forge_source: str, github_token: str | None
) -> str | None:
    """Resolve latest commit SHA from the forge-engine GitHub repo.

    Used to bust Daytona's 24hr declarative image cache — appending
    ``@<sha>`` to the pip install URL makes the image spec unique
    whenever a new commit is pushed.

    Returns a 7-char short SHA, or None on any failure (graceful fallback).
    """
    if "github.com" not in forge_source or not github_token:
        return None

    m = re.search(r"github\.com/([^/]+)/([^/.]+)", forge_source)
    if not m:
        return None

    owner, repo = m.group(1), m.group(2)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits/main",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "Authorization": f"token {github_token}",
                },
            )
            resp.raise_for_status()
            sha = resp.json()["sha"][:7]
            logger.info("Resolved forge-engine SHA: %s", sha)
            return sha
    except Exception:
        logger.warning("Failed to resolve forge-engine SHA; using unpinned URL", exc_info=True)
        return None


@dataclass
class SandboxSession:
    """Tracks a live sandbox and its associated scan."""

    scan_id: UUID
    sandbox: Sandbox
    repo_path: str = "/home/daytona/repo"


_SANDBOX_MAX_RETRIES = 3
_SANDBOX_RETRY_EXCEPTIONS = (DaytonaError, httpx.TimeoutException, httpx.ConnectError, ConnectionError)


class SandboxManager:
    """Creates, manages, and tears down Daytona sandboxes."""

    def __init__(self) -> None:
        # NOTE: If target is None, Daytona will pick the org default.
        # Passing an unsupported target yields errors like:
        # "Region us is not available to the organization".
        target = settings.daytona_target or None
        if isinstance(target, str) and not target.strip():
            target = None
        config = DaytonaConfig(
            api_key=settings.daytona_api_key,
            api_url=settings.daytona_api_url,
            target=target,
        )
        try:
            self._daytona = Daytona(config)
        except Exception as exc:
            logger.warning(
                "Daytona client initialization failed — sandbox unavailable: %s",
                exc,
                exc_info=True,
            )
            raise RuntimeError(
                f"Sandbox service unavailable: Daytona client could not be initialized ({exc})"
            ) from exc
        self._sessions: dict[UUID, SandboxSession] = {}
        self._executor = SandboxExecutor()

    async def provision(self, scan_id: UUID, clone_url: str) -> SandboxSession:
        """Spin up a sandbox, clone the repo, and return a session handle."""
        logger.info("Provisioning sandbox for scan %s", scan_id)

        image = (
            Image.debian_slim("3.12")
            .pip_install(["semgrep"])
            .workdir("/home/daytona")
        )

        params = CreateSandboxFromImageParams(
            image=image,
            resources=Resources(
                cpu=settings.sandbox_cpu,
                memory=settings.sandbox_memory_gb,
                disk=settings.sandbox_disk_gb,
            ),
            auto_stop_interval=settings.sandbox_timeout_minutes,
            ephemeral=True,
            labels={"scan_id": str(scan_id)},
            env_vars={"SCAN_ID": str(scan_id)},
        )

        for attempt in range(1, _SANDBOX_MAX_RETRIES + 1):
            try:
                sandbox = self._daytona.create(params)
                break
            except _SANDBOX_RETRY_EXCEPTIONS as exc:
                if attempt == _SANDBOX_MAX_RETRIES:
                    raise
                delay = 5 * attempt
                logger.warning(
                    "Sandbox creation attempt %d/%d failed for scan %s: %s — retrying in %ds",
                    attempt, _SANDBOX_MAX_RETRIES, scan_id, exc, delay,
                )
                await asyncio.sleep(delay)

        repo_path = "/home/daytona/repo"
        sandbox.git.clone(clone_url, repo_path)

        session = SandboxSession(
            scan_id=scan_id, sandbox=sandbox, repo_path=repo_path
        )
        self._sessions[scan_id] = session
        logger.info("Sandbox ready for scan %s", scan_id)
        return session

    async def provision_forge(
        self,
        scan_id: UUID,
        clone_url: str,
        *,
        openrouter_api_key: str,
        github_token: str | None = None,
    ) -> SandboxSession:
        """Spin up an isolated sandbox for a FORGE discovery scan.

        Installs the FORGE engine, clones the repo, and locks down
        network egress to only the hosts FORGE needs (LLM API, PyPI,
        GitHub for cloning).
        """
        logger.info("Provisioning FORGE sandbox for scan %s", scan_id)

        forge_source = settings.forge_package_source

        # Use dedicated deploy token (not the user's OAuth token) for private repo access.
        deploy_token = settings.forge_deploy_token

        # Pin to latest commit SHA so Daytona rebuilds the image on new pushes.
        sha = await _resolve_forge_sha(forge_source, deploy_token or github_token)
        if sha and "@" not in forge_source:
            forge_source = f"{forge_source}@{sha}"

        if deploy_token and "github.com" in forge_source:
            forge_source = forge_source.replace(
                "https://github.com/",
                f"https://x-access-token:{deploy_token}@github.com/",
            )
        elif github_token and "github.com" in forge_source:
            forge_source = forge_source.replace(
                "https://github.com/",
                f"https://x-access-token:{github_token}@github.com/",
            )

        image = (
            Image.debian_slim("3.12")
            .run_commands("apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*")
            # Install Opengrep BEFORE forge-engine so the binary is on PATH
            # when FORGE's deterministic scan phase runs. Without this the
            # sandbox silently skips the entire SAST pass (~16 rules worth
            # of findings) and composite scores get wildly inflated.
            .pip_install(["opengrep", forge_source])
            .workdir("/home/daytona")
        )

        env_vars = {
            "SCAN_ID": str(scan_id),
            "OPENROUTER_API_KEY": openrouter_api_key,
        }

        # NOTE: Daytona network_allow_list only supports CIDR IP ranges,
        # not domain names. Since FORGE needs CDN-backed services
        # (OpenRouter, GitHub, PyPI) with dynamic IPs, we rely on
        # ephemeral containers + command-level NetworkPolicy for safety.
        params = CreateSandboxFromImageParams(
            image=image,
            resources=Resources(
                cpu=settings.forge_sandbox_cpu,
                memory=settings.forge_sandbox_memory_gb,
                disk=settings.forge_sandbox_disk_gb,
            ),
            auto_stop_interval=settings.forge_sandbox_timeout_minutes,
            ephemeral=True,
            labels={"scan_id": str(scan_id), "type": "forge"},
            env_vars=env_vars,
        )

        for attempt in range(1, _SANDBOX_MAX_RETRIES + 1):
            try:
                sandbox = self._daytona.create(params)
                break
            except _SANDBOX_RETRY_EXCEPTIONS as exc:
                if attempt == _SANDBOX_MAX_RETRIES:
                    raise
                delay = 5 * attempt
                logger.warning(
                    "FORGE sandbox creation attempt %d/%d failed for scan %s: %s — retrying in %ds",
                    attempt, _SANDBOX_MAX_RETRIES, scan_id, exc, delay,
                )
                await asyncio.sleep(delay)

        repo_path = "/home/daytona/repo"
        sandbox.git.clone(clone_url, repo_path)

        session = SandboxSession(
            scan_id=scan_id, sandbox=sandbox, repo_path=repo_path
        )
        self._sessions[scan_id] = session
        logger.info("FORGE sandbox ready for scan %s", scan_id)
        return session

    async def exec(
        self, scan_id: UUID, command: str, cwd: str | None = None, timeout: int = 120
    ) -> CommandResult:
        """Execute a command inside the scan's sandbox."""
        session = self._sessions.get(scan_id)
        if session is None:
            raise RuntimeError(f"No sandbox session for scan {scan_id}")

        work_dir = cwd or session.repo_path
        return await self._executor.execute(
            sandbox=session.sandbox,
            command=command,
            cwd=work_dir,
            timeout=timeout,
        )

    async def exec_streaming(
        self,
        scan_id: UUID,
        command: str,
        cwd: str | None = None,
        timeout: int = 900,
        on_output: Callable[[str], None] | None = None,
    ) -> CommandResult:
        """Execute a command with real-time log streaming."""
        session = self._sessions.get(scan_id)
        if session is None:
            raise RuntimeError(f"No sandbox session for scan {scan_id}")

        work_dir = cwd or session.repo_path
        return await self._executor.execute_streaming(
            sandbox=session.sandbox,
            command=command,
            cwd=work_dir,
            timeout=timeout,
            on_output=on_output,
        )

    async def read_file(self, scan_id: UUID, path: str) -> str:
        """Download a file's contents from the sandbox."""
        session = self._sessions.get(scan_id)
        if session is None:
            raise RuntimeError(f"No sandbox session for scan {scan_id}")
        try:
            content = session.sandbox.fs.download_file(path)
            return content.decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("download_file failed for %s: %s; falling back to cat", path, exc)
            result = await self.exec(scan_id, f"cat {path}", cwd="/home/daytona", timeout=120)
            if result.exit_code != 0:
                raise RuntimeError(f"Failed to read file via fallback cat: {path}") from exc
            return result.stdout

    async def upload_file(self, scan_id: UUID, path: str, content: bytes) -> None:
        """Upload a file into the sandbox."""
        session = self._sessions.get(scan_id)
        if session is None:
            raise RuntimeError(f"No sandbox session for scan {scan_id}")
        session.sandbox.fs.upload_file(content, path)

    async def get_file_tree(self, scan_id: UUID) -> str:
        """Return a recursive listing of the repo directory."""
        result = await self.exec(
            scan_id,
            "find . -type f -not -path './.git/*' -not -path './node_modules/*' | head -500 | sort",
        )
        return result.stdout

    async def destroy(self, scan_id: UUID) -> bool:
        """Tear down the sandbox for a scan. Returns True if destroyed successfully."""
        session = self._sessions.pop(scan_id, None)
        if session is None:
            return False
        try:
            session.sandbox.delete()
            logger.info("Sandbox destroyed for scan %s", scan_id)
            return True
        except Exception:
            logger.exception("Failed to destroy sandbox for scan %s", scan_id)
            return False
