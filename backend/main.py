"""Vibe2Prod API — FastAPI application entry point.

Start with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.middleware.auth import SupabaseAuthMiddleware
from api.middleware.rate_limit import limiter
from api.routes import (
    audit,
    status,
    fix,
    primer,
    onboarding,
    github_oauth,
    user,
    webhook,
    webhook_clerk,
)
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Vibe2Prod API starting up...")
    if settings.tier1_enabled:
        await audit.cleanup_tier1_expired()
    yield
    logger.info("Vibe2Prod API shutting down.")


app = FastAPI(
    title="Vibe2Prod API",
    description=(
        "AI-powered code audit and production-hardening API. "
        "Tier 1 deterministic scanning (free) with FORGE engine "
        "integration for AI-driven remediation."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ------------------------------------------------------------------ #
# CORS
# ------------------------------------------------------------------ #
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$|^https://(www\.)?vibe2prod\.com$|^https://.*\.ngrok-free\.app$|^https://.*\.ngrok-free\.dev$|^https://.*\.ngrok\.io$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(status.router, prefix="/api", tags=["streaming"])
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
# Global error handler
# ------------------------------------------------------------------ #
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
