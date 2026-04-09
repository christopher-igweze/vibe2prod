"""Domain-focused repository modules split from supabase_client.py.

Each module owns a single bounded context. Import from here or from
the individual modules directly.
"""

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
from services.repositories.health_repository import *  # noqa: F401,F403
