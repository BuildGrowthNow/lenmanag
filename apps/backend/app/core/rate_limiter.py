from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Simple in-memory rate limiter with sliding window.

    For production, consider using Redis-backed rate limiting with
    libraries like slowapi or fastapi-limiter.
    """

    def __init__(self):
        # Store: {ip: [(timestamp, endpoint), ...]}
        self._requests: Dict[str, list[Tuple[float, str]]] = defaultdict(list)
        self._cleanup_counter = 0

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header first (for proxies/load balancers)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()

        # Fallback to direct client
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_old_entries(self, ip: str, window_seconds: int) -> None:
        """Remove entries older than the window."""
        now = time.time()
        cutoff = now - window_seconds
        self._requests[ip] = [
            (ts, endpoint)
            for ts, endpoint in self._requests[ip]
            if ts > cutoff
        ]

    def check_rate_limit(
        self,
        request: Request,
        endpoint: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Check if request should be rate limited.

        Args:
            request: The FastAPI request object
            endpoint: Identifier for the endpoint (e.g., "auth:login")
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        ip = self._get_client_ip(request)
        now = time.time()

        # Periodic cleanup to prevent memory growth
        self._cleanup_counter += 1
        if self._cleanup_counter % 100 == 0:
            self._cleanup_old_entries(ip, window_seconds)

        # Clean up old entries for this IP
        self._cleanup_old_entries(ip, window_seconds)

        # Count recent requests for this endpoint
        recent_requests = [
            ts for ts, ep in self._requests[ip]
            if ep == endpoint and ts > now - window_seconds
        ]

        if len(recent_requests) >= max_requests:
            # Calculate retry-after header
            oldest_request = min(recent_requests)
            retry_after = int(window_seconds - (now - oldest_request)) + 1

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        self._requests[ip].append((now, endpoint))


# Global instance
_rate_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the global rate limiter instance."""
    return _rate_limiter


def check_auth_rate_limit(request: Request, endpoint: str) -> None:
    """Check rate limit for authentication endpoints.

    More restrictive limits for auth endpoints to prevent brute force.
    - 5 attempts per 15 minutes per IP
    """
    limiter = get_rate_limiter()
    limiter.check_rate_limit(
        request=request,
        endpoint=endpoint,
        max_requests=5,
        window_seconds=900,  # 15 minutes
    )


def check_api_rate_limit(request: Request, endpoint: str) -> None:
    """Check rate limit for general API endpoints.

    - 100 requests per minute per IP
    """
    limiter = get_rate_limiter()
    limiter.check_rate_limit(
        request=request,
        endpoint=endpoint,
        max_requests=100,
        window_seconds=60,
    )
