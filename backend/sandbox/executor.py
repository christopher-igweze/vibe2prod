"""Command execution abstraction for Daytona sandboxes."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from daytona import Sandbox
from daytona.common.errors import DaytonaError

from sandbox.network_policy import DEFAULT_POLICY, NetworkPolicy

logger = logging.getLogger(__name__)

_LOG_FILE = "/tmp/forge_stderr.log"


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
        on_output: Callable[[str], None] | None = None,
    ) -> CommandResult:
        """Execute a command with real-time log streaming via file polling.

        Runs the command with stderr redirected to a log file, then polls
        that file in parallel for new lines and passes them to ``on_output``.
        Uses the proven ``process.exec()`` for the actual execution.
        """
        self._policy.validate_command(command)

        # Redirect stderr to a log file so we can tail it in parallel.
        wrapped_cmd = f"{command} 2>{_LOG_FILE}"

        # Clear any stale log file
        sandbox.process.exec(f"rm -f {_LOG_FILE} && touch {_LOG_FILE}", cwd=cwd, timeout=10)

        # Run the command in a thread (proven reliable path)
        exec_future = asyncio.to_thread(
            sandbox.process.exec,
            wrapped_cmd,
            cwd=cwd,
            timeout=timeout,
        )

        # Poll the log file for new lines while the command runs
        last_offset = 0

        async def _tail_logs() -> None:
            nonlocal last_offset
            while True:
                await asyncio.sleep(2)
                try:
                    tail_resp = sandbox.process.exec(
                        f"tail -c +{last_offset + 1} {_LOG_FILE}",
                        cwd="/tmp",
                        timeout=10,
                    )
                    chunk = tail_resp.result or ""
                    if chunk and on_output:
                        last_offset += len(chunk.encode("utf-8", errors="replace"))
                        for line in chunk.splitlines():
                            line = line.strip()
                            if line:
                                on_output(line)
                except Exception:
                    logger.debug("Log tail failed (file may not exist yet or sandbox busy)")

        tail_task = asyncio.create_task(_tail_logs())

        outer_timeout = max(30, int(timeout) + 30)
        try:
            resp = await asyncio.wait_for(exec_future, timeout=outer_timeout)
        except asyncio.TimeoutError as exc:
            tail_task.cancel()
            raise RuntimeError(
                f"Sandbox exec response timeout after {outer_timeout}s for command: {command[:120]}"
            ) from exc
        except DaytonaError as exc:
            tail_task.cancel()
            status = getattr(exc, "status_code", None)
            detail = f"DaytonaError (HTTP {status}): {exc}" if status else f"DaytonaError: {exc}"
            logger.error("Sandbox command failed: %s | command: %s", detail, command[:120])
            raise RuntimeError(detail) from exc

        # Stop tailing and do one final read to catch remaining lines
        tail_task.cancel()
        try:
            final_resp = sandbox.process.exec(
                f"tail -c +{last_offset + 1} {_LOG_FILE}",
                cwd="/tmp",
                timeout=10,
            )
            final_chunk = final_resp.result or ""
            if final_chunk and on_output:
                for line in final_chunk.splitlines():
                    line = line.strip()
                    if line:
                        on_output(line)
        except Exception:
            logger.debug("Final log read failed for %s", _LOG_FILE)

        # Read full stderr for the result
        stderr = ""
        try:
            stderr_resp = sandbox.process.exec(f"cat {_LOG_FILE}", cwd="/tmp", timeout=10)
            stderr = stderr_resp.result or ""
        except Exception:
            logger.debug("Stderr read failed for %s", _LOG_FILE)

        return CommandResult(
            command=command,
            exit_code=resp.exit_code,
            stdout=resp.result or "",
            stderr=stderr,
        )
