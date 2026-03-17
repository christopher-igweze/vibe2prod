"""Sandbox subsystem — ephemeral container management for code analysis.

Key modules:
- sandbox.executor — CommandResult, SandboxExecutor (requires daytona)
- sandbox.interfaces — ExecutorProtocol, SandboxManagerProtocol
- sandbox.network_policy — NetworkPolicy, PolicyViolationError
- sandbox.manager — SandboxManager (requires daytona)
- sandbox.forge_log_parser — FORGE stdout to SSE event parsing

Note: executor and manager require the 'daytona' package, which is only
available in the production environment. Imports are lazy to avoid
breaking test collection when daytona is not installed.
"""
