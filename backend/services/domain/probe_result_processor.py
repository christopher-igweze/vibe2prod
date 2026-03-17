"""Probe result processing — score computation and result compilation.

Extracted from probe_engine.py to separate concerns.
"""

from __future__ import annotations

from models.probe import ProbeFinding, ProbeResult

# Severity deductions for probe_score calculation
SEVERITY_DEDUCTIONS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
    "info": 1,
}


def compile_result(findings: list[ProbeFinding], duration: float) -> ProbeResult:
    """Compute probe_score from findings and build the ProbeResult."""
    score = 100
    for f in findings:
        score -= SEVERITY_DEDUCTIONS.get(f.severity, 0)
    score = max(0, score)
    return ProbeResult(
        findings=findings,
        probe_score=score,
        duration_seconds=round(duration, 2),
    )
