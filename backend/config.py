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

    # --- E2E Testing ---
    e2e_testing: bool = False

    # --- CORS ---
    cors_allowed_origins: str = ""  # Comma-separated explicit origins for production

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 10

    # --- FORGE Sandbox ---
    forge_sandbox_cpu: int = 2
    forge_sandbox_memory_gb: int = 4
    forge_sandbox_disk_gb: int = 10
    forge_sandbox_timeout_minutes: int = 20
    forge_sandbox_exec_timeout: int = 900
    forge_package_source: str = "vibe2prod"

    # --- FORGE Engine ---
    forge_enabled: bool = False
    forge_agentfield_url: str = "http://localhost:8080"
    forge_node_id: str = "forge-engine"
    agentfield_api_key: str = ""
    forge_default_model: str = "minimax/minimax-m2.5"
    forge_runtime: str = "open_code"
    forge_max_inner_retries: int = 3
    forge_max_outer_replans: int = 1
    forge_poll_interval_seconds: int = 10
    forge_remediate_timeout_seconds: int = 2700

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


settings = Settings()
