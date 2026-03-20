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
    """Map v3 evaluation dimension scores to frontend score columns.

    Dimension mapping (forge v3 -> frontend):
      security -> security_score
      maintainability -> health_score
      reliability -> reliability_score
      performance -> scalability_score
    """
    evaluation = discovery_report.get("evaluation")
    if isinstance(evaluation, dict):
        scores = evaluation.get("scores")
        if isinstance(scores, dict):
            dims = scores.get("dimensions", {})
            if dims:
                return {
                    "security_score": _dim_score(dims, "security"),
                    "health_score": _dim_score(dims, "maintainability"),
                    "reliability_score": _dim_score(dims, "reliability"),
                    "scalability_score": _dim_score(dims, "performance"),
                }

    # No evaluation data — default all to 100
    return {
        "health_score": 100,
        "security_score": 100,
        "reliability_score": 100,
        "scalability_score": 100,
    }


def _dim_score(dims: dict, key: str, default: int = 100) -> int:
    """Extract a dimension score, defaulting to 100 if absent."""
    dim = dims.get(key)
    if isinstance(dim, dict):
        return dim.get("score", default)
    return default
