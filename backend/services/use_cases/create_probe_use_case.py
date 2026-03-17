"""Orchestrate probe creation: validate, authorize domain, create record.

This use case encapsulates the business logic currently in the probe route.
Route files should NOT be modified to use this yet — it exists as the
target architecture for future refactoring.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from config import settings
from constants import DOMAIN_AUTH_EXPIRY_DAYS, PROBE_FREE_LIMIT
from services.repositories.probe_repository import (
    create_probe,
    list_user_probes,
    get_authorized_target,
    save_authorized_target,
)
from services.repositories.user_repository import get_user_profile
from services.target_auth import extract_domain, is_authorized

logger = logging.getLogger(__name__)


class CreateProbeUseCase:
    """Orchestrates the probe creation lifecycle.

    Steps:
    1. Validate probe service is enabled
    2. Determine user identity (authenticated vs anonymous)
    3. Check free-tier quota for non-onboarded users
    4. Validate and authorize target domain
    5. Create probe record
    6. Return probe_id for background execution
    """

    def get_user_id_or_anon(self, user_id: str | None, client_ip: str) -> str:
        """Return authenticated user_id or a deterministic anon ID from IP."""
        if user_id:
            return user_id
        return f"anon:{hashlib.sha256(client_ip.encode()).hexdigest()[:16]}"

    async def validate_and_create(
        self,
        target_url: str,
        probe_type: str,
        config: dict,
        user_id: str,
        authenticated: bool,
        project_id: str | None = None,
    ) -> dict:
        """Validate preconditions, create probe record, return probe data.

        Raises ValueError for validation failures.
        """
        if not settings.probe_enabled:
            raise ValueError("probe_disabled")

        if not settings.probe_service_url:
            raise ValueError("probe_not_configured")

        profile = get_user_profile(user_id) if authenticated else None
        role = profile.get("role", "user") if profile else "user"
        onboarded = bool(profile and profile.get("onboarding_complete"))

        # Enforce free-tier limit
        if not onboarded:
            existing_probes = await list_user_probes(
                user_id, limit=PROBE_FREE_LIMIT + 1
            )
            if len(existing_probes) >= PROBE_FREE_LIMIT:
                raise ValueError("probe_limit_reached")

        domain = extract_domain(target_url)
        if not domain:
            raise ValueError("invalid_target_url")

        # Domain authorization
        auth_method: str | None = None
        if not authenticated:
            auth_method = "anonymous"
        elif role in ("developer", "beta_tester"):
            existing = await get_authorized_target(user_id, domain)
            if not existing:
                expires_at = (
                    datetime.now(timezone.utc)
                    + timedelta(days=DOMAIN_AUTH_EXPIRY_DAYS)
                ).isoformat()
                await save_authorized_target(
                    user_id, domain, "manual_approve", expires_at
                )
            auth_method = "manual_approve"
        else:
            from services import supabase_client as db

            if not await is_authorized(user_id, domain, db):
                raise ValueError("domain_not_authorized")

        from services.probe_service import probe_service

        probe_id = probe_service.create_probe_id()
        probe_data = {
            "id": probe_id,
            "user_id": user_id,
            "target_url": target_url,
            "status": "pending",
            "probe_type": probe_type,
            "config": config,
            "auth_method": auth_method,
        }
        if project_id:
            probe_data["project_id"] = project_id

        await create_probe(probe_data)

        return {
            "probe_id": probe_id,
            "target_url": target_url,
            "probe_type": probe_type,
            "config": config,
        }


create_probe_use_case = CreateProbeUseCase()
