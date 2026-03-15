"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator


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

    # --- E2E Testing ---
    e2e_testing: bool = False
    e2e_testing_token: str = ""  # Required secret token when e2e_testing is enabled

    # --- CORS ---
    cors_allowed_origins: str = ""  # Comma-separated explicit origins for production
    cors_vercel_projects: str = ""  # Comma-separated Vercel project names (for preview deployments)

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 10

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
    def _validate_e2e_testing_environment(self) -> "Settings":
        """Ensure e2e_testing can only be enabled in development environment with a valid token."""
        if self.e2e_testing:
            if self.environment != "development":
                raise ValueError(
                    "e2e_testing=True is not allowed in production. "
                    "Set environment='development' to enable e2e_testing."
                )
            if not self.e2e_testing_token:
                raise ValueError(
                    "e2e_testing_token is required when e2e_testing is enabled. "
                    "Set a secure token value (e.g., E2E_TESTING_TOKEN=your-secret-token)."
                )
        return self

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        """Ensure debug mode is never enabled in any environment."""
        if self.debug:
            raise ValueError(
                "debug=True is not allowed in any environment. "
                "Set debug=False explicitly."
            )
        return self


settings = Settings()
