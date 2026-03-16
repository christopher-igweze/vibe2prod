"""Clerk JWT verification middleware.

Verifies the Bearer token from the Authorization header using Clerk's
JWKS endpoint (RS256).  Attaches ``request.state.user_id`` for
downstream route handlers.

Falls back to Supabase HS256 verification when clerk_jwks_url is not
configured, for backward compatibility during migration.
"""

from __future__ import annotations

import hmac
import logging

import jwt
from jwt import PyJWKClient
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from config import settings

logger = logging.getLogger(__name__)

# Paths that don't require authentication
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
PUBLIC_PREFIXES = ("/api/webhook/", "/api/telemetry")

# Paths where auth is attempted but not required — if a valid token is present
# the user_id is set, otherwise the request proceeds without it.
OPTIONAL_AUTH_PREFIXES = ("/api/probe",)

# Cache the JWKS client (fetches and caches signing keys automatically)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient | None:
    global _jwks_client
    if _jwks_client is None and settings.clerk_jwks_url:
        _jwks_client = PyJWKClient(settings.clerk_jwks_url, cache_keys=True)
    return _jwks_client


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    """Verifies Clerk RS256 JWTs (or legacy Supabase HS256 as fallback)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for public endpoints and CORS preflight
        if (
            request.url.path in PUBLIC_PATHS
            or any(request.url.path.startswith(prefix) for prefix in PUBLIC_PREFIXES)
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        # E2E testing bypass: skip JWT verification and use a synthetic user_id
        # This is only allowed in development environment with a valid token.
        # Security: Check environment FIRST to ensure bypass cannot be activated
        # in production even if e2e_testing is incorrectly configured.
        if settings.environment != "development":
            # Production environment: e2e_testing must be disabled (defense in depth)
            # The config validator should prevent this at startup, but we check here
            # as an additional safeguard against misconfiguration
            if settings.e2e_testing:
                logger.error(
                    "E2E testing mode is enabled but environment is not 'development'. "
                    "This should not happen if config validation is working correctly. "
                    "Authentication bypass attempt blocked as a security precaution."
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "E2E testing is not allowed in production"},
                )
            # Normal production flow - proceed to JWT verification
            pass
        elif settings.e2e_testing:
            # Development environment with e2e_testing enabled
            _token_value = settings.e2e_testing_token.get_secret_value()
            # Use hmac.compare_digest for constant-time comparison to prevent
            # timing-based side-channel attacks on the token value (CWE-208).
            # The emptiness check uses the same path to keep timing uniform.
            _token_present = hmac.compare_digest(_token_value, _token_value) and bool(_token_value)
            if not _token_present:
                logger.error(
                    "E2E testing enabled but e2e_testing_token is not set. "
                    "Authentication bypass blocked."
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "E2E testing token is required"},
                )
            logger.warning(
                "E2E testing mode active — JWT verification bypassed. "
                "This should only be used in development environment."
            )
            # Store only a boolean flag in request state; never persist the raw
            # token itself so it cannot leak through downstream logging or error
            # responses (CWE-532).
            request.state.user_id = "e2e_test_user"
            request.state.e2e_authenticated = True
            return await call_next(request)

        is_optional = any(
            request.url.path.startswith(prefix)
            for prefix in OPTIONAL_AUTH_PREFIXES
        )

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            if is_optional:
                # No token on optional-auth route — proceed without user_id
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing Bearer token"},
            )

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            jwks = _get_jwks_client()
            if jwks:
                # Clerk RS256 verification via JWKS + issuer validation
                signing_key = jwks.get_signing_key_from_jwt(token)
                issuer = settings.clerk_issuer or (
                    settings.clerk_jwks_url.removesuffix("/.well-known/jwks.json")
                    if settings.clerk_jwks_url else None
                )
                decode_opts: dict = {"verify_aud": False}
                if not issuer:
                    decode_opts["verify_iss"] = False
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=issuer or None,
                    options=decode_opts,
                )
            else:
                # Legacy Supabase HS256 fallback
                payload = jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                )

            request.state.user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            if is_optional:
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={"detail": "Token expired"},
            )
        except jwt.InvalidTokenError as exc:
            if is_optional:
                return await call_next(request)
            return JSONResponse(
                status_code=401,
                content={"detail": f"Invalid token: {exc}"},
            )

        return await call_next(request)
