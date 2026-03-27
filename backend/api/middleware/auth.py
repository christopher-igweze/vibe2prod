"""Clerk JWT verification middleware.

Verifies the Bearer token from the Authorization header using Clerk's
JWKS endpoint (RS256).  Attaches ``request.state.user_id`` for
downstream route handlers.

Falls back to Supabase HS256 verification when clerk_jwks_url is not
configured, for backward compatibility during migration.
"""

from __future__ import annotations

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
PUBLIC_PREFIXES = ("/api/webhook/", "/api/telemetry", "/api/cli/", "/api/training/")

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
                # Clerk RS256 verification via JWKS + issuer validation.
                # Issuer is always verified when using Clerk JWKS — if
                # clerk_issuer is not explicitly set, derive it from the
                # JWKS URL (strip the /.well-known/jwks.json suffix).
                signing_key = jwks.get_signing_key_from_jwt(token)
                issuer = settings.clerk_issuer or (
                    settings.clerk_jwks_url.removesuffix("/.well-known/jwks.json")
                    if settings.clerk_jwks_url else None
                )
                if not issuer:
                    # This should never happen when jwks is non-None (which
                    # requires clerk_jwks_url to be set), but guard defensively.
                    return JSONResponse(
                        status_code=500,
                        content={"detail": "Clerk issuer could not be determined from configuration"},
                    )
                decode_opts: dict = {"verify_aud": False}
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=issuer,
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

            user_id = payload.get("sub")
            if not user_id:
                if is_optional:
                    return await call_next(request)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing sub claim in token"},
                )
            request.state.user_id = user_id
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
