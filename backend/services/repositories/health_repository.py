"""Health check and score computation utilities."""

from __future__ import annotations

from services.repositories._base import _client


async def check_database_health() -> bool:
    """Verify database connectivity by executing a simple query."""
    try:
        client = _client()
        client.table("projects").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _compute_scores_from_discovery(discovery_report: dict) -> dict[str, int]:
    """Derive health/security/reliability/scalability scores from findings.

    Starts each dimension at 100 and deducts based on finding severity.
    Maps FORGE categories to frontend score dimensions:
      security -> security_score
      quality + architecture -> health_score
      reliability -> reliability_score
      performance -> scalability_score
    """
    severity_weights = {"critical": 15, "high": 8, "medium": 4, "low": 1, "info": 0}
    category_map: dict[str, str] = {
        "security": "security_score",
        "quality": "health_score",
        "architecture": "health_score",
        "reliability": "reliability_score",
        "performance": "scalability_score",
    }

    deductions: dict[str, int] = {
        "health_score": 0,
        "security_score": 0,
        "reliability_score": 0,
        "scalability_score": 0,
    }

    for finding in discovery_report.get("findings", []):
        severity = finding.get("severity", "medium")
        category = finding.get("category", "quality")
        weight = severity_weights.get(severity, 4)
        score_key = category_map.get(category, "health_score")
        deductions[score_key] += weight

    return {k: max(0, 100 - v) for k, v in deductions.items()}
