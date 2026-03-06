"""Command execution abstraction for Daytona sandboxes."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from daytona import Sandbox, SessionExecuteRequest

from sandbox.network_policy import DEFAULT_POLICY, NetworkPolicy

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Normalised result of a command execution inside a sandbox."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int = 0


class SandboxExecutor:
    """Executes commands with fail-closed policy enforcement."""

    def __init__(self, policy: NetworkPolicy | None = None) -> None:
        self._policy = policy or DEFAULT_POLICY

    async def execute(
        self,
        *,
        sandbox: Sandbox,
        command: str,
        cwd: str,
        timeout: int = 120,
    ) -> CommandResult:
        self._policy.validate_command(command)

        outer_timeout = max(30, int(timeout) + 30)
        try:
            resp = await asyncio.wait_for(
                asyncio.to_thread(
                    sandbox.process.exec,
                    command,
                    cwd=cwd,
                    timeout=timeout,
                ),
                timeout=outer_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                f"Sandbox exec response timeout after {outer_timeout}s for command: {command[:120]}"
            ) from exc

        return CommandResult(
            command=command,
            exit_code=resp.exit_code,
            stdout=resp.result or "",
            stderr="",
        )

    async def execute_streaming(
        self,
        *,
        sandbox: Sandbox,
        command: str,
        cwd: str,
        timeout: int = 900,
        on_stdout: Callable[[str], None] | None = None,
    ) -> CommandResult:
        """Execute a long-running command with real-time stdout streaming.

        Uses the Daytona session API to run the command asynchronously and
        stream logs via WebSocket. Each stdout chunk is passed to ``on_stdout``.
        """
        self._policy.validate_command(command)

        session_id = f"forge-{uuid.uuid4().hex[:8]}"
        full_cmd = f"cd {cwd} && {command}"
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        try:
            await asyncio.to_thread(sandbox.process.create_session, session_id)

            resp = await asyncio.to_thread(
                sandbox.process.execute_session_command,
                session_id,
                SessionExecuteRequest(command=full_cmd, run_async=True),
            )
            cmd_id = resp.cmd_id

            def _on_stdout(chunk: str) -> None:
                stdout_lines.append(chunk)
                if on_stdout:
                    for line in chunk.splitlines():
                        line = line.strip()
                        if line:
                            on_stdout(line)

            def _on_stderr(chunk: str) -> None:
                stderr_lines.append(chunk)

            # Stream logs — this blocks until the command finishes or the
            # WebSocket closes. Run in a thread to respect our timeout.
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        sandbox.process.get_session_command_logs_async,
                        session_id,
                        cmd_id,
                        on_stdout=_on_stdout,
                        on_stderr=_on_stderr,
                    ),
                    timeout=timeout + 30,
                )
            except asyncio.TimeoutError as exc:
                raise RuntimeError(
                    f"Streaming exec timeout after {timeout}s for command: {command[:120]}"
                ) from exc

            # Get final exit code
            cmd_status = await asyncio.to_thread(
                sandbox.process.get_session_command, session_id, cmd_id
            )

            return CommandResult(
                command=command,
                exit_code=cmd_status.exit_code if cmd_status.exit_code is not None else 1,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
            )
        finally:
            try:
                await asyncio.to_thread(sandbox.process.delete_session, session_id)
            except Exception:
                logger.debug("Failed to delete session %s (may already be gone)", session_id)

