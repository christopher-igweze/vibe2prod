"""Sandbox interface protocols — define clear boundaries for sandbox operations.

These Protocol classes formalize the contracts that SandboxExecutor and
SandboxManager implement. Downstream consumers can depend on these
protocols rather than concrete classes, enabling testing with mocks
and future alternative implementations.

Note: CommandResult is referenced via TYPE_CHECKING to avoid importing
daytona at module level (it may not be installed in test environments).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from sandbox.executor import CommandResult


@dataclass
class CommandResultLike:
    """Lightweight stand-in for CommandResult in protocol signatures.

    This allows protocol consumers to work without importing daytona.
    The actual CommandResult from sandbox.executor is a superset.
    """

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int = 0


@runtime_checkable
class ExecutorProtocol(Protocol):
    """Contract for command execution inside a sandbox."""

    async def execute(
        self,
        *,
        sandbox: object,
        command: str,
        cwd: str,
        timeout: int = 120,
    ) -> CommandResultLike:
        """Execute a command and return the result."""
        ...

    async def execute_streaming(
        self,
        *,
        sandbox: object,
        command: str,
        cwd: str,
        timeout: int = 900,
        on_output: Callable[[str], None] | None = None,
    ) -> CommandResultLike:
        """Execute a command with real-time output streaming."""
        ...


@runtime_checkable
class SandboxManagerProtocol(Protocol):
    """Contract for sandbox lifecycle management."""

    async def exec(
        self,
        scan_id: UUID,
        command: str,
        cwd: str | None = None,
        timeout: int = 120,
    ) -> CommandResultLike:
        """Execute a command inside a scan's sandbox."""
        ...

    async def exec_streaming(
        self,
        scan_id: UUID,
        command: str,
        cwd: str | None = None,
        timeout: int = 900,
        on_output: Callable[[str], None] | None = None,
    ) -> CommandResultLike:
        """Execute a command with streaming output."""
        ...

    async def read_file(self, scan_id: UUID, path: str) -> str:
        """Read a file's contents from the sandbox."""
        ...

    async def upload_file(self, scan_id: UUID, path: str, content: bytes) -> None:
        """Upload a file into the sandbox."""
        ...

    async def get_file_tree(self, scan_id: UUID) -> str:
        """Return a recursive file listing of the repo directory."""
        ...

    async def destroy(self, scan_id: UUID) -> bool:
        """Tear down the sandbox. Returns True if destroyed successfully."""
        ...
