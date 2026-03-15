"""Rate limiting for API endpoints.

This module provides comprehensive rate limiting using a sliding window algorithm
for accurate request counting, with support for different limits per endpoint type.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class SlidingWindowCounter:
    """Thread-safe sliding window rate limit counter.
    
    Uses a sliding window algorithm to accurately track requests within
    a time window, providing better protection against request bursts
    compared to fixed window algorithms.
    """
    
    requests: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def is_allowed(self, window_seconds: int, max_requests: int) -> tuple[bool, int, int]:
        """Check if a request is allowed under rate limit.
        
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_timestamp)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        with self._lock:
            # Remove expired entries outside the window
            self.requests = [t for t in self.requests if t > window_start]
            
            current_count = len(self.requests)
            remaining = max(0, max_requests - current_count)
            
            if current_count >= max_requests:
                # Calculate when the oldest request expires
                reset_time = int(self.requests[0] + window_seconds)
                return False, remaining, reset_time
            
            # Add current request
            self.requests.append(current_time)
            reset_time = int(current_time + window_seconds)
            return True, remaining - 1, reset_time


class RateLimitStorage:
    """In-memory rate limit storage with sliding window algorithm.
    
    Provides thread-safe rate limiting that can be used across multiple
    worker processes (each process will have its own limits, which is
    acceptable for development/single-instance deployments).
    """
    
    def __init__(self):
        self._counters: dict[str, SlidingWindowCounter] = defaultdict(SlidingWindowCounter)
        self._lock = threading.Lock()
    
    def check_rate_limit(
        self, 
        key: str, 
        window_seconds: int = 60, 
        max_requests: int = 10
    ) -> tuple[bool, int, int]:
        """Check and update rate limit for a key.
        
        Args:
            key: Unique identifier (user_id or IP)
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed in window
            
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_timestamp)
        """
        with self._lock:
            counter = self._counters[key]
            return counter.is_allowed(window_seconds, max_requests)
    
    def clear_expired(self):
        """Clear expired entries to prevent memory growth."""
        current_time = time.time()
        with self._lock:
            for key, counter in self._counters.items():
                with counter._lock:
                    counter.requests = [t for t in counter.requests if t > current_time - 3600]
                    if not counter.requests:
                        del self._counters[key]


# Global storage instance
_rate_limit_storage = RateLimitStorage()


def _get_rate_limit_key(request: Request) -> str:
    """Return rate limit key: user_id if authenticated, otherwise IP address.

    This prevents attackers behind NAT or using IP spoofing from bypassing
    rate limits by rotating IPs, while also ensuring legitimate users
    sharing an IP (corporate networks, mobile carriers) are not unfairly
    rate limited together when authenticated.
    
    Note: Returns raw user_id/IP for backward compatibility with slowapi.
    Use rate_limit_key_with_category() for tiered rate limiting.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return user_id
    return get_remote_address(request)


def _get_endpoint_category(request: Request) -> str:
    """Categorize endpoint for different rate limit tiers.
    
    Different endpoint types may have different rate limits:
    - "read": GET requests for data retrieval (higher limits)
    - "write": POST/PUT/DELETE requests (stricter limits)
    - "auth": Authentication endpoints (strictest limits)
    """
    path = request.url.path
    method = request.method
    
    # Authentication endpoints get strictest limits
    if "/auth/" in path or "/login" in path or "/oauth" in path:
        return "auth"
    
    # Write operations get stricter limits
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "write"
    
    return "read"


def get_rate_limit_config(request: Request) -> tuple[int, int]:
    """Get rate limit configuration based on endpoint type.
    
    Returns:
        Tuple of (max_requests, window_seconds)
    """
    category = _get_endpoint_category(request)
    base_limit = settings.rate_limit_per_minute
    
    # Different limits based on endpoint category
    if category == "auth":
        # Stricter limits for auth endpoints to prevent brute force
        return max(5, base_limit // 4), 60
    elif category == "write":
        # Moderate limits for write operations
        return max(10, base_limit // 2), 60
    else:
        # Higher limits for read operations
        return base_limit, 60


def rate_limit_key_with_category(request: Request) -> str:
    """Generate rate limit key including endpoint category for tiered limiting."""
    base_key = _get_rate_limit_key(request)
    category = _get_endpoint_category(request)
    return f"{base_key}:{category}"


def check_rate_limit(request: Request) -> tuple[bool, int, int]:
    """Check if request is within rate limits.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Tuple of (is_allowed, remaining_requests, reset_timestamp)
    """
    key = rate_limit_key_with_category(request)
    max_requests, window_seconds = get_rate_limit_config(request)
    
    return _rate_limit_storage.check_rate_limit(key, window_seconds, max_requests)


def get_rate_limit_headers(request: Request) -> dict[str, str]:
    """Generate rate limit headers for response.
    
    Adds standard rate limit headers:
    - X-RateLimit-Limit: Maximum requests allowed in window
    - X-RateLimit-Remaining: Remaining requests in current window
    - X-RateLimit-Reset: Unix timestamp when the window resets
    """
    max_requests, window_seconds = get_rate_limit_config(request)
    key = rate_limit_key_with_category(request)
    _, remaining, reset = _rate_limit_storage.check_rate_limit(key, window_seconds, max_requests)
    
    return {
        "X-RateLimit-Limit": str(max_requests),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset),
    }


# Create slowapi Limiter instance for decorator-based rate limiting
limiter = Limiter(key_func=_get_rate_limit_key)


def rate_limit_string() -> str:
    """Return the default rate limit string for the configured limit."""
    return f"{settings.rate_limit_per_minute}/minute"


def get_custom_rate_limit(requests: int, window_seconds: int = 60) -> str:
    """Generate a custom rate limit string for specific configurations.
    
    Args:
        requests: Number of requests allowed
        window_seconds: Time window in seconds
        
    Returns:
        Rate limit string in format "requests/period"
    """
    if window_seconds == 60:
        return f"{requests}/minute"
    elif window_seconds == 3600:
        return f"{requests}/hour"
    else:
        return f"{requests}/{window_seconds}second"
