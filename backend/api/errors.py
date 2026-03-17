"""Standardized error response helpers for API routes.

These helpers provide consistent error response formatting across all
route handlers. Use them instead of inline HTTPException/JSONResponse
to ensure uniform error codes, messages, and HTTP status codes.

Usage:
    from api.errors import not_found, forbidden, bad_request

    raise not_found("Scan not found")
    raise forbidden("You do not have access to this resource")
    raise bad_request("Invalid target URL", code="invalid_url")
"""

from __future__ import annotations

from fastapi import HTTPException


def not_found(message: str = "Not found", *, code: str = "not_found") -> HTTPException:
    """Return a 404 HTTPException with a structured detail payload."""
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def forbidden(message: str = "Forbidden", *, code: str = "forbidden") -> HTTPException:
    """Return a 403 HTTPException with a structured detail payload."""
    return HTTPException(status_code=403, detail={"code": code, "message": message})


def bad_request(message: str = "Bad request", *, code: str = "bad_request") -> HTTPException:
    """Return a 400 HTTPException with a structured detail payload."""
    return HTTPException(status_code=400, detail={"code": code, "message": message})


def conflict(message: str = "Conflict", *, code: str = "conflict") -> HTTPException:
    """Return a 409 HTTPException with a structured detail payload."""
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def unauthorized(message: str = "Unauthorized", *, code: str = "unauthorized") -> HTTPException:
    """Return a 401 HTTPException with a structured detail payload."""
    return HTTPException(status_code=401, detail={"code": code, "message": message})


def service_unavailable(
    message: str = "Service unavailable", *, code: str = "service_unavailable",
) -> HTTPException:
    """Return a 503 HTTPException with a structured detail payload."""
    return HTTPException(status_code=503, detail={"code": code, "message": message})


def server_error(
    message: str = "Internal server error", *, code: str = "internal_error",
) -> HTTPException:
    """Return a 500 HTTPException with a structured detail payload."""
    return HTTPException(status_code=500, detail={"code": code, "message": message})


def bad_gateway(
    message: str = "Bad gateway", *, code: str = "bad_gateway",
) -> HTTPException:
    """Return a 502 HTTPException with a structured detail payload."""
    return HTTPException(status_code=502, detail={"code": code, "message": message})


def github_timeout(
    context: str = "GitHub API", *, retry_after: int = 30,
) -> HTTPException:
    """Return a 503 HTTPException for GitHub timeout errors."""
    return HTTPException(
        status_code=503,
        detail={
            "code": "github_timeout",
            "message": f"{context} is temporarily unavailable. Please try again later.",
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


def github_unreachable(*, retry_after: int = 60) -> HTTPException:
    """Return a 503 HTTPException for GitHub connection errors."""
    return HTTPException(
        status_code=503,
        detail={
            "code": "github_unreachable",
            "message": "Unable to reach GitHub. Please check your connection and try again in a few moments.",
            "retry_after": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )


def forge_disabled() -> HTTPException:
    """Return a 503 HTTPException when FORGE engine is disabled."""
    return HTTPException(
        status_code=503,
        detail={
            "code": "forge_disabled",
            "message": "Auto-fix is not currently available. FORGE engine is disabled.",
        },
    )
