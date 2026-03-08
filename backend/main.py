"""Vibe2Prod API — FastAPI application entry point.

Start with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import re as _re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.middleware.auth import SupabaseAuthMiddleware
from api.middleware.rate_limit import limiter
from config import settings
from api.routes import (
    audit,
    credits,
    fix,
    primer,
    onboarding,
    github_oauth,
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

    # Mark scans orphaned by a previous container lifecycle as failed.
    # If we just booted, no background tasks can be running for them.
    try:
        from services import supabase_client as db

        count = await db.fail_orphaned_scans()
        if count:
            logger.warning("Marked %d orphaned scan(s) as failed on startup.", count)
    except Exception:
        logger.exception("Failed to clean up orphaned scans on startup.")

    yield
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

if _cors_origins:
    # Production: explicit origin allowlist
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
else:
    # Development fallback: regex-based matching
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
            r"|^https://.*\.vercel\.app$"
            r"|^https://(www\.)?vibe2prod\.com$"
            r"|^https://.*\.verstandai\.site$"
        ),
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
# Routers
# ------------------------------------------------------------------ #
app.include_router(audit.router, prefix="/api", tags=["audit"])
app.include_router(credits.router, prefix="/api", tags=["credits"])
app.include_router(fix.router, prefix="/api", tags=["fix"])
app.include_router(primer.router, prefix="/api", tags=["primer"])
app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
app.include_router(github_oauth.router, prefix="/api", tags=["github"])
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
    return {"status": "healthy"}


# ------------------------------------------------------------------ #
# URL sanitization for logging
# ------------------------------------------------------------------ #
_SENSITIVE_PARAM = _re.compile(
    r"(token|key|secret|password|jwt|bearer|access_token|refresh_token)"
    r"=([^\s&]+)",
    _re.IGNORECASE,
)


def _sanitize_url(url: object) -> str:
    """Redact sensitive query parameters from URLs before logging."""
    return _SENSITIVE_PARAM.sub(r"\1=***", str(url))


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
                return JSONResponse(
                    status_code=inner.status_code,
                    content={"detail": inner.detail},
                )
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    logger.exception("Unhandled exception on %s %s", request.method, _sanitize_url(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
