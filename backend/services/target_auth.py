"""Domain authorization service for live probing.

Generates verification tokens and checks domain ownership via DNS TXT,
meta tag, or well-known file methods.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from config import settings

logger = logging.getLogger(__name__)


def _get_verify_secret() -> bytes:
    """Derive verification secret from the deployment's JWT secret."""
    return f"vibe2prod-probe-verify:{settings.supabase_jwt_secret}".encode()


def generate_verification_token(user_id: str, domain: str) -> str:
    """HMAC-SHA256 hash of user_id + domain, hex-encoded."""
    msg = f"{user_id}:{domain}".encode()
    return hmac.new(_get_verify_secret(), msg, hashlib.sha256).hexdigest()


def extract_domain(url: str) -> str:
    """Extract the domain (host) from a URL string."""
    parsed = urlparse(str(url))
    return parsed.hostname or ""


async def verify_dns_txt(domain: str, token: str) -> bool:
    """Check for a TXT record containing the verification token.

    Uses subprocess `dig` to avoid adding a dnspython dependency.
    """
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["dig", "+short", "TXT", domain],
                capture_output=True,
                text=True,
                timeout=10,
            ),
        )
        if result.returncode != 0:
            logger.warning("dig failed for %s: %s", domain, result.stderr)
            return False
        # dig returns TXT records quoted, e.g. "vibe2prod-verify=abc123"
        for line in result.stdout.strip().splitlines():
            clean = line.strip().strip('"')
            if f"vibe2prod-verify={token}" in clean:
                return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("DNS verification failed for %s: %s", domain, exc)
        return False


async def verify_meta_tag(url: str, token: str) -> bool:
    """HTTP GET the URL and check for <meta name="vibe2prod-verify" content="TOKEN">."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(str(url))
            if resp.status_code != 200:
                return False
            body = resp.text.lower()
            # Look for the meta tag (case-insensitive)
            expected = f'content="{token.lower()}"'
            return 'name="vibe2prod-verify"' in body and expected in body
    except httpx.HTTPError as exc:
        logger.warning("Meta tag verification failed for %s: %s", url, exc)
        return False


async def verify_file(url: str, token: str) -> bool:
    """HTTP GET {url}/.well-known/vibe2prod-verify.txt and check content."""
    parsed = urlparse(str(url))
    base = f"{parsed.scheme}://{parsed.netloc}"
    verify_url = f"{base}/.well-known/vibe2prod-verify.txt"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(verify_url)
            if resp.status_code != 200:
                return False
            return token in resp.text.strip()
    except httpx.HTTPError as exc:
        logger.warning("File verification failed for %s: %s", verify_url, exc)
        return False


async def is_authorized(
    user_id: str, domain: str, db_module: object
) -> bool:
    """Check if the user has a non-expired authorized_targets entry for the domain."""
    record = await db_module.get_authorized_target(user_id, domain)  # type: ignore[attr-defined]
    if not record:
        return False
    expires_at = record.get("expires_at")
    if not expires_at:
        return False
    # Parse ISO timestamp from DB
    if isinstance(expires_at, str):
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    else:
        exp = expires_at
    return exp > datetime.now(timezone.utc)
