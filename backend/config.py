"""Application configuration loaded from environment variables."""

from __future__ import annotations

import base64
import logging
import re

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Vibe2Prod backend."""

    # --- API Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # --- Supabase ---
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    supabase_jwt_secret: str = Field(..., description="Supabase JWT secret for token verification")

    # --- OpenRouter (LLM routing) ---
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # --- GitHub Integration ---
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_oauth_scope: str = "repo read:user user:email"
    github_oauth_state_ttl_minutes: int = 15
    github_oauth_state_secret: str | None = None
    github_webhook_secret: str | None = None
    github_oauth_allowed_redirect_origins: str = ""  # Comma-separated, e.g. "https://vibe2prod.com,http://localhost:3000"
    webhook_replay_window_seconds: int = 600
    # 32-byte AES-256 key encoded as URL-safe base64 (required).
    # Generate with:
    #   python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
    #
    # Key rotation procedure:
    #   1. Generate a new key using the command above.
    #   2. Set GITHUB_TOKEN_ENCRYPTION_KEY to the new key in .env / secrets.
    #   3. Deploy the change. New tokens will be encrypted with the new key.
    #   4. Previously encrypted tokens will fail to decrypt — users will need
    #      to re-connect GitHub OAuth (disconnect + reconnect) to re-encrypt
    #      their token with the new key.
    #   5. For zero-downtime rotation, implement a key-list approach: try
    #      decrypting with the new key first, fall back to the old key, and
    #      re-encrypt with the new key on successful fallback decryption.
    github_token_encryption_key: str = Field(
        ...,
        description=(
            "URL-safe base64-encoded 32-byte AES-256 key used to encrypt "
            "GitHub OAuth access tokens before storing them in the database."
        ),
    )

    # --- Daytona (sandbox) ---
    daytona_api_key: str = Field(..., description="Daytona API key")
    daytona_api_url: str = "https://app.daytona.io/api"
    daytona_target: str | None = None

    # --- LLM Models ---
    model_scanner: str = "google/gemini-2.0-flash-001"

    # --- LLM Runtime Limits ---
    llm_max_output_tokens: int = 4096

    # --- Sandbox Limits ---
    sandbox_timeout_minutes: int = 30
    sandbox_cpu: int = 2
    sandbox_memory_gb: int = 4
    sandbox_disk_gb: int = 8

    # --- Clerk Auth ---
    clerk_jwks_url: str = ""  # e.g. https://your-app.clerk.accounts.dev/.well-known/jwks.json
    clerk_issuer: str = ""    # e.g. https://your-app.clerk.accounts.dev — derived from jwks_url if empty
    clerk_webhook_secret: str = ""

    # --- Stripe ---
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # --- User Defaults ---
    default_user_role: str = "user"
    beta_access_code: str = ""

    # --- Environment ---
    environment: str = "production"  # "development" or "production"

    # --- Frontend ---
    frontend_url: str = "http://localhost:3000"

    # --- CORS ---
    cors_allowed_origins: str = ""  # Comma-separated explicit origins for production
    cors_vercel_projects: str = ""  # Comma-separated Vercel project names (for preview deployments)

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 10

    # --- Supabase Connection Pooling ---
    supabase_pool_size: int = 10  # Max connections in the httpx pool
    supabase_pool_timeout: float = 30.0  # Seconds to wait for a pooled connection

    # --- FORGE Sandbox ---
    forge_sandbox_cpu: int = 2
    forge_sandbox_memory_gb: int = 4
    forge_sandbox_disk_gb: int = 10
    forge_sandbox_timeout_minutes: int = 75
    forge_sandbox_exec_timeout: int = 3600
    forge_package_source: str = "vibe2prod"
    forge_deploy_token: str | None = None  # GitHub PAT for private forge-engine repo access

    # --- Live Probe ---
    probe_enabled: bool = False
    probe_max_concurrent: int = 5
    probe_request_timeout_seconds: int = 10
    probe_max_urls_per_probe: int = 100
    probe_rate_limit_per_target: int = 10

    # --- Security Probe Service ---
    probe_service_url: str = ""  # e.g. http://security-probe:8080
    probe_service_api_key: str = ""

    # --- FORGE Engine ---
    forge_enabled: bool = False
    forge_agentfield_url: str = "http://localhost:8080"
    forge_node_id: str = "forge-engine"
    agentfield_api_key: str = ""
    forge_default_model: str = ""
    forge_poll_interval_seconds: int = 10
    forge_remediate_timeout_seconds: int = 2700
    forge_webhook_base_url: str = ""  # Public URL of backend, e.g. https://api.vibe2prod.com

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _normalize_optional_secrets(self) -> "Settings":
        """Coerce empty-string secrets to None and warn about missing webhook secret."""
        if self.github_webhook_secret is not None and not self.github_webhook_secret.strip():
            self.github_webhook_secret = None
        if self.github_webhook_secret is None:
            logging.getLogger(__name__).warning(
                "GITHUB_WEBHOOK_SECRET is empty — webhook endpoint will return 503"
            )
        return self

    @model_validator(mode="after")
    def _validate_jwt_secret_encoding(self) -> "Settings":
        """Warn if supabase_jwt_secret looks like base64 but is not valid.

        This is informational only — Supabase JWT secrets may or may not be
        base64 encoded depending on the project configuration.
        """
        secret = self.supabase_jwt_secret
        if secret and re.fullmatch(r"[A-Za-z0-9+/=\-_]+", secret):
            try:
                base64.b64decode(secret, validate=True)
            except Exception:
                try:
                    base64.urlsafe_b64decode(secret + "==")
                except Exception:
                    logging.getLogger(__name__).warning(
                        "SUPABASE_JWT_SECRET looks like base64 but failed to decode. "
                        "Verify the value is correct."
                    )
        return self

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        """Ensure debug mode is only enabled in development."""
        if self.debug and self.environment != "development":
            raise ValueError(
                "debug=True is only allowed when environment='development'. "
                f"Current environment is '{self.environment}'. "
                "Set environment='development' or set debug=False."
            )
        return self

    @model_validator(mode="after")
    def _validate_clerk_issuer(self) -> "Settings":
        """Warn if clerk_jwks_url is set but clerk_issuer is empty.

        The auth middleware derives the issuer from the JWKS URL when
        clerk_issuer is not set, but explicit configuration is preferred
        for defense-in-depth.
        """
        if self.clerk_jwks_url and not self.clerk_issuer:
            logging.getLogger(__name__).warning(
                "clerk_jwks_url is set but clerk_issuer is empty. "
                "The issuer will be derived from the JWKS URL. "
                "Set CLERK_ISSUER explicitly for stronger validation."
            )
        return self

    @model_validator(mode="after")
    def _validate_encryption_key(self) -> "Settings":
        """Validate github_token_encryption_key is valid base64 and 32 bytes at startup."""
        key = self.github_token_encryption_key
        if key:
            try:
                key_bytes = base64.urlsafe_b64decode(key + "==")
            except Exception:
                raise ValueError(
                    "GITHUB_TOKEN_ENCRYPTION_KEY is not valid URL-safe base64. "
                    "Generate a new key with: "
                    'python -c "import secrets, base64; '
                    'print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"'
                )
            if len(key_bytes) != 32:
                raise ValueError(
                    f"GITHUB_TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes "
                    f"(got {len(key_bytes)}). Generate a new key with: "
                    'python -c "import secrets, base64; '
                    'print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"'
                )
        return self

    @model_validator(mode="after")
    def _validate_cors_production(self) -> "Settings":
        """Warn if production environment lacks explicit CORS origins."""
        if self.environment == "production" and not self.cors_allowed_origins:
            logging.getLogger(__name__).warning(
                "Running in production without explicit CORS origins. "
                "Set CORS_ALLOWED_ORIGINS for security. "
                "Falling back to regex-based matching which is less secure."
            )
        return self


settings = Settings()
