"""Shared HTTP client with connection pooling for external API calls.

This module provides a singleton httpx.AsyncClient with connection pooling
to avoid the overhead of creating new connection pools for each request.

It also exposes ``safe_request`` — a wrapper that catches common network
exceptions (timeout, connect error, generic request error) and converts them
to FastAPI ``HTTPException`` responses with appropriate status codes and
structured log messages, so callers don't have to repeat that boilerplate.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException

from constants import (
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE_CONNECTIONS,
    HTTP_TIMEOUT_CONNECT_SECONDS,
    HTTP_TIMEOUT_DEFAULT_SECONDS,
)

logger = logging.getLogger(__name__)


class SharedHttpClient(httpx.AsyncClient):
    """A shared httpx.AsyncClient with connection pooling for reuse across requests.

    This class extends httpx.AsyncClient to add attributes that indicate
    it's a shared client configured for connection pooling.

    It also provides ``safe_request`` — a wrapper around the underlying
    ``request`` method that catches common network failures and raises
    structured ``HTTPException`` errors instead of letting raw ``httpx``
    exceptions propagate to callers.
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

    async def safe_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with global exception handling for network failures.

        Wraps ``httpx.AsyncClient.request`` and converts the three most common
        network-level failure modes into FastAPI ``HTTPException`` instances so
        that unhandled exceptions never propagate to the ASGI framework:

        * ``httpx.TimeoutException``  → 504 Gateway Timeout
        * ``httpx.ConnectError``      → 503 Service Unavailable
        * ``httpx.RequestError``      → 502 Bad Gateway  (catch-all for other
                                        transport-level errors)

        HTTP-level errors (4xx / 5xx response status codes) are **not** caught
        here — callers should inspect ``response.status_code`` or call
        ``response.raise_for_status()`` as appropriate for their context.

        Args:
            method: HTTP method string (``"GET"``, ``"POST"``, etc.).
            url:    Full URL for the request.
            **kwargs: Any additional keyword arguments accepted by
                      ``httpx.AsyncClient.request`` (``headers``, ``json``,
                      ``params``, ``timeout``, etc.).

        Returns:
            The ``httpx.Response`` object on success.

        Raises:
            HTTPException: With status 504 on timeout, 503 on connection
                           failure, or 502 on any other transport error.
        """
        try:
            return await self.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            logger.warning("Request timeout for %s %s: %s", method, url, exc)
            raise HTTPException(
                status_code=504,
                detail="Request timed out",
            ) from exc
        except httpx.ConnectError as exc:
            logger.warning("Connection error for %s %s: %s", method, url, exc)
            raise HTTPException(
                status_code=503,
                detail="Service unavailable",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Request error for %s %s: %s", method, url, exc)
            raise HTTPException(
                status_code=502,
                detail="Bad gateway",
            ) from exc


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
        timeout=httpx.Timeout(HTTP_TIMEOUT_DEFAULT_SECONDS, connect=HTTP_TIMEOUT_CONNECT_SECONDS),
        limits=httpx.Limits(
            max_connections=HTTP_MAX_CONNECTIONS,
            max_keepalive_connections=HTTP_MAX_KEEPALIVE_CONNECTIONS,
        ),
    )


# Module-level client for backwards compatibility and convenience
# This can be used directly: await shared_client.get(...)
# But prefer using get_http_client() for better control
shared_client = get_http_client()


async def safe_request(method: str, url: str, **kwargs) -> httpx.Response:
    """Module-level convenience wrapper around ``shared_client.safe_request``.

    Delegates directly to :py:meth:`SharedHttpClient.safe_request` on the
    module-level ``shared_client`` singleton.  Import and use this when you
    want the shortest possible call-site:

    .. code-block:: python

        from services.http_client import safe_request

        response = await safe_request("GET", "https://api.example.com/data")

    See :py:meth:`SharedHttpClient.safe_request` for full documentation on
    exception semantics.
    """
    return await shared_client.safe_request(method, url, **kwargs)
