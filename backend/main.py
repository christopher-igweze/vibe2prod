"""Vibe2Prod API — FastAPI application entry point.

Start with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import logging
import re as _re
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.middleware.auth import SupabaseAuthMiddleware
from api.middleware.rate_limit import limiter
from config import settings
from api.routes import (
    audit,
    cli,
    credits,
    primer,
    onboarding,
    github_oauth,
    telemetry,
    training,
    user,
    webhook,
    webhook_clerk,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Vibe2Prod API starting up...")

    # Verify database connectivity before attempting any database operations.
    # This ensures we fail fast if critical services are unavailable.
    try:
        from services import supabase_client as db

        db_available = await db.check_database_health()
        if not db_available:
            logger.error("Database connectivity check failed on startup. Cannot proceed.")
            raise RuntimeError("Database unavailable: critical service failure")
        logger.info("Database connectivity verified")
    except Exception:
        # Re-raise to fail fast - database is a critical service
        logger.exception("Failed to verify database connectivity on startup.")
        raise RuntimeError("Database connectivity check failed - cannot start in degraded state")

    # Mark scans orphaned by a previous container lifecycle as failed.
    # If we just booted, no background tasks can be running for them.
    try:
        count = await db.fail_orphaned_scans()
        if count:
            logger.warning("Marked %d orphaned scan(s) as failed on startup.", count)
    except Exception:
        logger.exception("Failed to clean up orphaned scans on startup.")
        # Don't re-raise - cleanup failure is not critical to startup

    # Initialize shared HTTP client with connection pooling
    try:
        from services.http_client import shared_client
        await shared_client.__aenter__()
        logger.info("Shared HTTP client initialized with connection pooling")
    except Exception as e:
        logger.warning("Failed to initialize shared HTTP client: %s", e)
        # Continue startup - some features may work without it

    yield

    # Close shared HTTP client
    await shared_client.__aexit__(None, None, None)
    logger.info("Shared HTTP client closed")

    logger.info("Vibe2Prod API shutting down.")


app = FastAPI(
    title="Vibe2Prod API",
    description=(
        "AI-powered code audit and production-hardening API. "
        "FORGE engine integration for AI-driven discovery and remediation."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------ #
# CORS
# ------------------------------------------------------------------ #
_cors_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]

# Known Vercel production projects (comma-separated). If set, only these project
# subdomains on vercel.app will be allowed. This restricts the overly permissive
# wildcard pattern for security (CWE-346).
_vercel_projects = [p.strip() for p in settings.cors_vercel_projects.split(",") if p.strip()]

if _cors_origins:
    # Production: explicit origin allowlist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
elif _vercel_projects:
    # Development with known Vercel projects: restrict to explicit project list
    # Build regex: ^https://project1\.vercel\.app$|^https://project2\.vercel\.app$, etc.
    _vercel_pattern = "|".join(
        rf"^https://{_re.escape(project)}\.vercel\.app$" for project in _vercel_projects
    )
    # Security fix: Only allow HTTP for localhost to reduce attack surface (CWE-346)
    # HTTPS localhost is not needed for development and creates bypass risk
    _cors_regex = (
        r"^http://(localhost|127\.0\.0\.1)(:\d+)?$|"
        + _vercel_pattern
        + r"|^https://(www\.)?vibe2prod\.com$|^https://(app|staging|preview)\.verstandai\.site$"
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=_cors_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
else:
    # Development fallback: only localhost over HTTP.
    # Production and staging MUST set CORS_ALLOWED_ORIGINS or CORS_VERCEL_PROJECTS
    # explicitly. No staging/preview domains in the fallback to prevent
    # accidental exposure (CWE-346).
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

# ------------------------------------------------------------------ #
# Rate limiting
# ------------------------------------------------------------------ #
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------------------------------------------------------ #
# JWT Auth (skip for health + docs)
# ------------------------------------------------------------------ #
app.add_middleware(SupabaseAuthMiddleware)


# ------------------------------------------------------------------ #
# Security headers middleware (OWASP best practices)
# ------------------------------------------------------------------ #
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # X-XSS-Protection: 0 disables the buggy legacy XSS filter in older
        # browsers; modern CSP is the correct replacement.
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ------------------------------------------------------------------ #
# Request ID middleware for traceability
# ------------------------------------------------------------------ #
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Generate a unique request ID for each request and add it to state."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


# ------------------------------------------------------------------ #
# Access logging middleware — sanitize URLs on every request
# ------------------------------------------------------------------ #
class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log every incoming request with a sanitized URL.

    Applying _sanitize_url here ensures that *all* request paths —
    not only error paths — are logged without exposing sensitive query
    parameters (CWE-532 / OWASP A09:2021).
    """

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.info(
            "Incoming request: %s %s | request_id=%s",
            request.method,
            _sanitize_url(request.url),
            request_id,
        )
        response = await call_next(request)
        logger.info(
            "Completed request: %s %s | status=%s | request_id=%s",
            request.method,
            _sanitize_url(request.url),
            response.status_code,
            request_id,
        )
        return response


app.add_middleware(AccessLogMiddleware)

# ------------------------------------------------------------------ #
# Routers
# ------------------------------------------------------------------ #
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(cli.router, prefix="/api", tags=["cli"])
app.include_router(credits.router, prefix="/api", tags=["credits"])
app.include_router(primer.router, prefix="/api", tags=["primer"])
app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
app.include_router(github_oauth.router, prefix="/api", tags=["github"])
app.include_router(telemetry.router, prefix="/api", tags=["telemetry"])
app.include_router(training.router, prefix="/api", tags=["training"])
app.include_router(user.router, prefix="/api", tags=["user"])
app.include_router(webhook.router, prefix="/api", tags=["webhook"])
app.include_router(webhook_clerk.router, prefix="/api", tags=["webhook"])


# ------------------------------------------------------------------ #
# Health & root
# ------------------------------------------------------------------ #
@app.get("/", tags=["meta"])
async def root():
    return {"service": "Vibe2Prod API", "status": "ok", "version": "2.0.0"}


@app.get("/health", tags=["meta"])
async def health():
    """Health check endpoint that verifies database connectivity.

    Returns healthy status only if all critical services are available.
    This allows load balancers and orchestration systems to detect
    degraded states and take appropriate action.
    """
    from services import supabase_client as db

    # Verify database connectivity
    try:
        db_healthy = await db.check_database_health()
    except Exception as e:
        logger.exception("Health check failed with exception")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "error"},
        )

    if not db_healthy:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "unavailable"},
        )

    return {"status": "healthy", "database": "available"}


# ------------------------------------------------------------------ #
# URL sanitization for logging
# ------------------------------------------------------------------ #

# Allowlist of query-parameter names that are safe to appear in logs.
# Every parameter whose name is NOT in this set will be redacted to "***".
# This whitelist approach (CWE-532) ensures that any new or unknown query
# parameters — including user_id, email, session_id, or future secrets —
# are redacted automatically rather than accidentally exposed.
_SAFE_QUERY_PARAMS: frozenset[str] = frozenset(
    {
        # Pagination / filtering
        "page",
        "limit",
        "offset",
        "sort",
        "order",
        "filter",
        "q",
        "search",
        # Resource identifiers that carry no PII
        "format",
        "version",
        "lang",
        "locale",
        # Caching / HTTP semantics
        "v",
        "cb",
    }
)

# Pre-compiled pattern that matches any query-parameter assignment.
# Used to iterate over all key=value pairs in the query string.
_QUERY_PARAM_RE = _re.compile(r"([^&=\s]+)=([^&\s]*)")


def _sanitize_url(url: object) -> str:
    """Redact all non-allowlisted query parameters from a URL before logging.

    Uses a whitelist approach: only parameters explicitly listed in
    _SAFE_QUERY_PARAMS are preserved; every other parameter value is
    replaced with "***".  This prevents accidental exposure of sensitive
    data (e.g. token, key, email, user_id, session_id) that may appear
    in query strings but are not included in the explicit denylist.

    Args:
        url: Any object whose ``str()`` representation is a URL.

    Returns:
        The URL string with all non-allowlisted query-parameter values
        replaced by "***".
    """

    def _redact_param(match: _re.Match) -> str:  # type: ignore[type-arg]
        param_name = match.group(1)
        if param_name.lower() in _SAFE_QUERY_PARAMS:
            return match.group(0)  # preserve name=value unchanged
        return f"{param_name}=***"

    return _QUERY_PARAM_RE.sub(_redact_param, str(url))


# ------------------------------------------------------------------ #
# Global error handler
# ------------------------------------------------------------------ #
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Starlette BaseHTTPMiddleware wraps HTTPExceptions in ExceptionGroups.
    # Unwrap them so FastAPI returns the correct status code.
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            if isinstance(inner, HTTPException):
                # Log the root cause before returning the HTTPException response
                _log_exception(request, exc, inner)
                return JSONResponse(
                    status_code=inner.status_code,
                    content={"detail": inner.detail},
                )
        # Log the root cause for unhandled exceptions in the group
        _log_exception(request, exc, None)
    elif isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    else:
        # Log the exception with proper context
        _log_exception(request, exc, None)

    # Return generic error to client without exposing internal request_id
    # This prevents information leakage about internal tracking to unauthenticated users
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Pre-compiled patterns for redacting sensitive data from exception messages
_SENSITIVE_PATTERNS = _re.compile(
    r"(?i)"
    r"((?:token|key|secret|password|bearer|authorization|api[_-]?key|access[_-]?token)"
    r"[\s=:\"']+)"  # label followed by separator
    r"[^\s\"',;}{)]{4,}",  # the actual value (4+ non-whitespace chars)
)


def _redact_exception_message(msg: str) -> str:
    """Redact tokens, keys, and passwords from an exception message."""
    return _SENSITIVE_PATTERNS.sub(r"\1***", msg)


def _log_exception(request: Request, exc: Exception, http_exc: HTTPException | None):
    """Log exception details with appropriate context.

    Only includes user_id in logs when actually authenticated (not None).
    Uses internal request_id for tracing but does not expose it to clients.
    Exception messages are redacted to remove tokens and keys (CWE-532).
    """
    # Capture request context for better diagnostics
    request_id = getattr(request.state, "request_id", "unknown")
    # Only include user_id in logs if the user is authenticated
    user_id = getattr(request.state, "user_id", None)

    # In debug mode, log full exception with stack trace for debugging
    # In production, log a sanitized message without stack trace to avoid
    # exposing sensitive code paths in log files (CWE-532)
    if settings.debug:
        if http_exc:
            # Log the underlying exception that was wrapped in BaseExceptionGroup
            logger.exception(
                "Unhandled exception on %s %s | request_id=%s%s",
                request.method,
                _sanitize_url(request.url),
                request_id,
                f" user_id={user_id}" if user_id else "",
                exc_info=exc,
            )
        else:
            logger.exception(
                "Unhandled exception on %s %s | request_id=%s%s",
                request.method,
                _sanitize_url(request.url),
                request_id,
                f" user_id={user_id}" if user_id else "",
            )
    else:
        redacted_msg = _redact_exception_message(str(exc))
        if http_exc:
            # Log the underlying exception that was wrapped
            logger.error(
                "Unhandled exception on %s %s | request_id=%s%s | wrapped_exc=%s: %s",
                request.method,
                _sanitize_url(request.url),
                request_id,
                f" user_id={user_id}" if user_id else "",
                type(exc).__name__,
                redacted_msg,
            )
        else:
            logger.error(
                "Unhandled exception on %s %s | request_id=%s%s | error=%s: %s",
                request.method,
                _sanitize_url(request.url),
                request_id,
                f" user_id={user_id}" if user_id else "",
                type(exc).__name__,
                redacted_msg,
            )


# NOTE: CancelledError and KeyboardInterrupt are BaseException subclasses.
# Starlette rejects exception handlers for non-Exception classes, and
# ASGI servers (uvicorn) handle these signals natively.
