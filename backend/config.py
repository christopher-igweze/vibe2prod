"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


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
    webhook_replay_window_seconds: int = 600

    # --- Daytona (sandbox) ---
    daytona_api_key: str = Field(..., description="Daytona API key")
    daytona_api_url: str = "https://app.daytona.io/api"
    daytona_target: str | None = None

    # --- LLM Runtime Limits ---
    llm_max_output_tokens: int = 4096

    # --- Sandbox Limits ---
    sandbox_timeout_minutes: int = 30
    sandbox_cpu: int = 2
    sandbox_memory_gb: int = 4
    sandbox_disk_gb: int = 8

    # --- Tier 1 (Free) ---
    tier1_enabled: bool = True
    tier1_assistant_model: str = "google/gemini-2.5-flash-lite"
    tier1_loc_cap: int = 50000
    tier1_monthly_report_cap: int = 10
    tier1_project_cap: int = 3
    tier1_index_ttl_days: int = 30
    tier1_report_ttl_days: int = 7

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 10

    # --- FORGE Engine ---
    forge_enabled: bool = False
    forge_agentfield_url: str = "http://localhost:8080"
    forge_default_model: str = "minimax/minimax-m2.5"
    forge_runtime: str = "open_code"
    forge_max_inner_retries: int = 3
    forge_max_outer_replans: int = 1

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
