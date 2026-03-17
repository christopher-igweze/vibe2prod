"""Webhook ingestion routes with fail-closed signature + replay checks."""

from __future__ import annotations

import asyncio
import heapq
import hmac
import logging
import time
from collections import OrderedDict
from hashlib import sha256

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.middleware.rate_limit import limiter, get_custom_rate_limit
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Webhook delivery deduplication cache
# ---------------------------------------------------------------------------
# Purpose: Prevent replay attacks by tracking delivery IDs within a TTL window.
#
# Bounds & cleanup:
#   - Hard cap: _MAX_CACHE_ENTRIES (10,000 entries, ~1.2 MB at ~120 bytes each)
#   - TTL: configurable via settings.webhook_replay_window_seconds (default 600s)
#   - FIFO eviction: when at capacity, oldest entries are evicted first
#   - Periodic cleanup: a background asyncio task runs every 60s to expire
#     stale entries via a min-heap for O(log n) identification
#   - Heap is also bounded at _MAX_HEAP_ENTRIES to prevent secondary growth
#
# This is an in-memory cache, not persistent. Server restarts clear it,
# which is acceptable because webhook signatures already provide primary
# authentication. The cache only prevents replay within a single process
# lifecycle.
# ---------------------------------------------------------------------------
_seen_deliveries: OrderedDict[str, tuple[int, int]] = OrderedDict()
_deliveries_lock = asyncio.Lock()
_cleanup_task: asyncio.Task | None = None
_CLEANUP_INTERVAL_SECONDS = 60  # Run cleanup every minute

# Hard cap on the delivery dedup cache to prevent unbounded memory growth.
# At ~120 bytes per entry this caps memory at roughly 1.2 MB.
_MAX_CACHE_ENTRIES = 10_000

# Min-heap for efficient expiration tracking: (expiration_time, delivery_id)
# This allows O(1) access to the earliest expiration instead of O(n) scan.
# Bounded to _MAX_HEAP_ENTRIES to prevent secondary memory growth from
# stale heap entries that reference already-evicted cache entries.
_expiration_heap: list[tuple[int, str]] = []
_MAX_HEAP_ENTRIES = 10_000


class WebhookResponse(BaseModel):
    status: str = "ok"
    message: str = "Webhook accepted."
    event: str | None = None
    action: str | None = None
    delivery_id: str | None = None


def _webhook_not_configured() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "code": "webhook_unauthorized",
            "message": "Webhook authentication failed.",
        },
    )


def _verify_github_signature(*, body: bytes, signature: str) -> bool:
    secret = settings.github_webhook_secret
    if not secret:
        raise _webhook_not_configured()
    if not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _cleanup_expired_entries() -> int:
    """Remove expired entries from the cache and return count of removed entries.
    
    Uses the expiration heap for O(log n) identification of potentially expired entries,
    then verifies each against the actual cache. This is more efficient than scanning
    all entries when the cache is large.
    """
    now_ts = int(time.time())
    removed_count = 0
    
    async with _deliveries_lock:
        # Use heap to efficiently find candidates for expiration
        # Clean up stale heap entries (those not in cache or already expired)
        while _expiration_heap:
            exp_time, delivery_id = heapq.heappop(_expiration_heap)
            
            # Skip if entry no longer exists in cache
            if delivery_id not in _seen_deliveries:
                continue
                
            seen_ts, ttl = _seen_deliveries[delivery_id]
            expiration_time = seen_ts + ttl
            
            # If this heap entry is outdated (different from current), skip
            if expiration_time != exp_time:
                continue
                
            # If not expired, put it back (entries are in order)
            if expiration_time > now_ts:
                heapq.heappush(_expiration_heap, (expiration_time, delivery_id))
                break
                
            # Entry is expired - remove it
            _seen_deliveries.pop(delivery_id, None)
            removed_count += 1
        
        # Log metrics
        if _seen_deliveries or removed_count > 0:
            logger.info(
                "Webhook delivery cache: size=%d, removed_expired=%d",
                len(_seen_deliveries),
                removed_count
            )
        
        return removed_count


async def _periodic_cleanup() -> None:
    """Background task to periodically clean up expired entries."""
    while True:
        try:
            await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
            await _cleanup_expired_entries()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in webhook delivery cache cleanup: %s", e)


def _start_cleanup_task() -> None:
    """Start the background cleanup task if not already running."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_periodic_cleanup())


async def _register_delivery(delivery_id: str) -> bool:
    """Return False when a duplicate delivery ID is observed inside replay window."""
    now_ts = int(time.time())
    ttl_seconds = max(60, int(settings.webhook_replay_window_seconds))

    # Lazily start cleanup task on first request only
    # Use double-check locking pattern to avoid race condition
    global _cleanup_task
    if _cleanup_task is None:
        async with _deliveries_lock:
            if _cleanup_task is None:
                _cleanup_task = asyncio.create_task(_periodic_cleanup())

    async with _deliveries_lock:
        # Check for duplicate or expired
        if delivery_id in _seen_deliveries:
            seen_ts, ttl = _seen_deliveries[delivery_id]
            if (now_ts - seen_ts) <= ttl:
                # Valid entry exists - duplicate within TTL window
                return False
            # Entry expired - remove it (heap entry will be cleaned up later)

        # Evict oldest entries if cache is at capacity (FIFO order).
        while len(_seen_deliveries) >= _MAX_CACHE_ENTRIES:
            _seen_deliveries.popitem(last=False)

        # Add new entry (move to end to maintain order)
        _seen_deliveries[delivery_id] = (now_ts, ttl_seconds)
        _seen_deliveries.move_to_end(delivery_id)

        # Track expiration time in heap for efficient cleanup
        expiration_time = now_ts + ttl_seconds
        if len(_expiration_heap) < _MAX_HEAP_ENTRIES:
            heapq.heappush(_expiration_heap, (expiration_time, delivery_id))

        return True


@router.post("/webhook/github", response_model=WebhookResponse)
@limiter.limit(get_custom_rate_limit(30, 60))
async def github_webhook(request: Request) -> WebhookResponse:
    signature = request.headers.get("X-Hub-Signature-256", "")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    event = request.headers.get("X-GitHub-Event", "unknown")

    if not delivery_id:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "delivery_id_missing",
                "message": "Missing X-GitHub-Delivery header.",
            },
        )

    body = await request.body()
    if not body:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "body_empty",
                "message": "Request body must not be empty.",
            },
        )

    if not _verify_github_signature(body=body, signature=signature):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "webhook_signature_invalid",
                "message": "Webhook signature verification failed.",
            },
        )

    is_fresh = await _register_delivery(delivery_id)
    if not is_fresh:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "webhook_replay_detected",
                "message": "Duplicate webhook delivery detected.",
            },
        )

    action: str | None = None
    try:
        payload = await request.json()
        if isinstance(payload, dict):
            raw_action = payload.get("action")
            if isinstance(raw_action, str):
                action = raw_action
    except Exception:
        logger.warning("Failed to parse webhook JSON for delivery=%s", delivery_id)
        payload = None

    logger.info(
        "GitHub webhook accepted event=%s action=%s delivery=%s",
        event,
        action or "-",
        delivery_id,
    )

    return WebhookResponse(event=event, action=action, delivery_id=delivery_id)

