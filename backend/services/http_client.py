"""Shared HTTP client with connection pooling for external API calls.

This module provides a singleton httpx.AsyncClient with connection pooling
to avoid the overhead of creating new connection pools for each request.
"""

from __future__ import annotations

import httpx


class SharedHttpClient(httpx.AsyncClient):
    """A shared httpx.AsyncClient with connection pooling for reuse across requests.
    
    This class extends httpx.AsyncClient to add attributes that indicate
    it's a shared client configured for connection pooling.
    """
    
    def __init__(self, *args, **kwargs):
        # Extract limits before passing to parent to store on instance
        self._limits = kwargs.pop('limits', None)
        super().__init__(*args, **kwargs)
        self._is_shared = True
    
    @property
    def limits(self):
        """Return the connection limits for this client."""
        return self._limits


def get_http_client() -> SharedHttpClient:
    """Get the shared HTTP client with connection pooling.
    
    Returns a SharedHttpClient configured with sensible defaults:
    - max_connections=100: Maximum total connections
    - max_keepalive_connections=20: Maximum idle connections to keep alive
    
    The client should be used directly for making HTTP requests.
    For use cases requiring specific timeout or follow_redirects settings,
    you can create a new client with those specific settings, but for
    high-traffic endpoints, prefer using this shared client.
    """
    return SharedHttpClient(
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
        ),
    )


# Module-level client for backwards compatibility and convenience
# This can be used directly: await shared_client.get(...) 
# But prefer using get_http_client() for better control
shared_client = get_http_client()