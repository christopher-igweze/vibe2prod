"""Supabase client — backward-compatible re-exports.

All functions have been split into focused repository modules under
``services/repositories/``. This module re-exports every public name
so that existing imports like ``from services.supabase_client import X``
continue to work without modification.
"""

from services.repositories._base import _client  # noqa: F401
from services.repositories.user_repository import *  # noqa: F401,F403
from services.repositories.scan_repository import *  # noqa: F401,F403
from services.repositories.project_repository import *  # noqa: F401,F403
from services.repositories.findings_repository import *  # noqa: F401,F403
from services.repositories.credits_repository import *  # noqa: F401,F403
from services.repositories.build_repository import *  # noqa: F401,F403
from services.repositories.onboarding_repository import *  # noqa: F401,F403
from services.repositories.oauth_repository import *  # noqa: F401,F403
from services.repositories.primer_repository import *  # noqa: F401,F403
from services.repositories.telemetry_repository import *  # noqa: F401,F403
from services.repositories.training_repository import *  # noqa: F401,F403
from services.repositories.health_repository import *  # noqa: F401,F403
from services.repositories.health_repository import _compute_scores_from_discovery  # noqa: F401
