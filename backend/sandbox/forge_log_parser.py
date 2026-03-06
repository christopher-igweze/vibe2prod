"""Parse FORGE engine stdout into SSE events for real-time progress."""

from __future__ import annotations

import re
from collections.abc import Callable

from models.agent_log import AgentLogEntry, AgentName, LogLevel, SSEEventType

# Map FORGE agent numbers to our AgentName enum.
_AGENT_MAP: dict[str, AgentName] = {
    "1": AgentName.primer,       # Codebase Analyst
    "2": AgentName.security,     # Security Auditor
    "3": AgentName.scanner,      # Quality Auditor
    "4": AgentName.evolution,    # Architecture Reviewer
    "5": AgentName.planner,      # Fix Strategist
    "6": AgentName.planner,      # Triage Classifier
    "7": AgentName.implementer,  # Coder Tier 2
    "8": AgentName.implementer,  # Coder Tier 3
    "9": AgentName.builder,      # Test Generator
    "10": AgentName.verifier,    # Code Reviewer
    "11": AgentName.verifier,    # Integration Validator
    "12": AgentName.educator,    # Debt Tracker
}

# Patterns that indicate a phase or agent is starting / completing.
_PATTERNS: list[tuple[re.Pattern[str], SSEEventType, LogLevel]] = [
    # Phase starts
    (re.compile(r"Discovery: Running Agent (\d+)"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Discovery: Running Agents (\d+-\d+)"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Discovery \[swarm\]: Running"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Triage: Running Agent (\d+)"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Remediation: routing"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Remediation: executing"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Validation: Running Agent (\d+)"), SSEEventType.agent_start, LogLevel.info),
    # Phase completions
    (re.compile(r"Discovery complete:"), SSEEventType.agent_complete, LogLevel.success),
    (re.compile(r"Discovery \[swarm\]: complete"), SSEEventType.agent_complete, LogLevel.success),
    (re.compile(r"Triage complete:"), SSEEventType.agent_complete, LogLevel.success),
    (re.compile(r"Remediation complete:"), SSEEventType.agent_complete, LogLevel.success),
    (re.compile(r"Validation complete:"), SSEEventType.agent_complete, LogLevel.success),
    # Individual agent messages
    (re.compile(r"Agent (\d+): .+ starting"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"Agent (\d+): Complete"), SSEEventType.agent_complete, LogLevel.success),
    (re.compile(r"Agent (\d+): PASSED"), SSEEventType.agent_complete, LogLevel.success),
    # Session-level
    (re.compile(r"FORGE standalone starting:"), SSEEventType.agent_start, LogLevel.info),
    (re.compile(r"FORGE complete: SUCCESS"), SSEEventType.scan_complete, LogLevel.success),
    (re.compile(r"FORGE complete: FAIL"), SSEEventType.scan_error, LogLevel.error),
]


def _extract_agent(line: str) -> AgentName:
    """Extract the agent from a log line, defaulting to orchestrator."""
    m = re.search(r"Agent (\d+)", line)
    if m:
        return _AGENT_MAP.get(m.group(1), AgentName.orchestrator)
    if "Discovery" in line:
        return AgentName.primer
    if "Triage" in line:
        return AgentName.planner
    if "Remediation" in line:
        return AgentName.implementer
    if "Validation" in line:
        return AgentName.verifier
    return AgentName.orchestrator


def parse_forge_line(line: str) -> AgentLogEntry | None:
    """Parse a single FORGE stdout line into an SSE event, or None if irrelevant."""
    for pattern, event_type, level in _PATTERNS:
        if pattern.search(line):
            return AgentLogEntry(
                event_type=event_type,
                agent=_extract_agent(line),
                message=line.strip(),
                level=level,
            )
    return None


def make_line_handler(emit: Callable[[AgentLogEntry], None]) -> Callable[[str], None]:
    """Create a stdout line handler that parses FORGE output and emits SSE events.

    Returns a callback suitable for ``SandboxExecutor.execute_streaming(on_stdout=...)``.
    """

    def handler(line: str) -> None:
        entry = parse_forge_line(line)
        if entry is not None:
            emit(entry)

    return handler
