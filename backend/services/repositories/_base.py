"""Shared Supabase client singleton for all repository modules."""

from __future__ import annotations

from supabase import create_client, Client

from config import settings


def _client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)
