"""
Rate Limiter configuration for the application.
"""

import hashlib
import os

from fastapi import Request
from prometheus_client import Counter
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.settings import settings


# Paths where rate limit must fail-closed (reject request) when Redis is unavailable.
# Read-only portfolio endpoints use fail-open (allow through) to remain available.
FAIL_CLOSED_PATHS = frozenset({"/api/v1/contact"})


def get_client_ip(request: Request) -> str:
    """Returns the real client IP.

    - strict_proxy_mode ON (TRUSTED_PROXY_IPS configured): trusts forwarded headers
      only when REMOTE_ADDR is a known proxy. Prevents IP spoofing bypass.
    - strict_proxy_mode OFF (default, Koyeb/dynamic IPs): legacy depth-based mode.
    """
    peer_ip = request.client.host if request.client else None

    if settings.strict_proxy_mode:
        if peer_ip not in settings.trusted_proxy_ip_set:
            # Peer is not a known proxy — ignore spoofed forwarding headers
            return peer_ip or "unknown"

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ips = [ip.strip() for ip in forwarded_for.split(",")]
        trusted_index = max(0, len(ips) - settings.trusted_proxy_depth - 1)
        return ips[trusted_index]

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return get_remote_address(request)


def get_email_or_ip_key(request: Request) -> str:
    """
    Returns the request identity (email) previously set by middleware, or falls
    back to client IP. Synchronous for full compatibility with the Limiter.
    """
    # Identity is populated by MiddlewareRequisicao for POST /api/v1/contact
    identity = getattr(request.state, "identity", None)
    if identity:
        return identity

    return get_client_ip(request)


def get_contact_fingerprint_key(request: Request) -> str:
    """Combines IP and user-agent to limit unauthenticated bursts."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    fingerprint = hashlib.sha256(f"{client_ip}:{user_agent}".encode()).hexdigest()[:16]
    return f"fingerprint:{fingerprint}"


# Initialize limiter using client IP as the default key.
# When REDIS_URL is set, uses Redis as the backend storage for horizontal scaling.
_storage_uri = (
    "memory://"
    if os.environ.get("PYTEST_CURRENT_TEST")
    else (settings.redis_url or "memory://")
)

limiter = Limiter(
    key_func=get_client_ip,
    strategy="fixed-window",
    storage_uri=_storage_uri,
)

# Fallback in-memory limiter used when the primary backend (Redis) is
# unavailable.  Sensitive paths degrade to local rate limiting instead
# of returning a hard HTTP 503, keeping the contact form functional
# while still providing single-instance anti-abuse protection.
_fallback_limiter = Limiter(
    key_func=get_client_ip,
    strategy="fixed-window",
    storage_uri="memory://",
)

REDIS_UNAVAILABLE_COUNTER = Counter(
    "rate_limit_backend_unavailable_total",
    "Redis unavailable during rate limit evaluation",
    ["path", "mode"],
)


def check_rate_limit(request: Request, limit_string: str, key_func=get_email_or_ip_key):
    """
    Manually applies a rate limit hit and raises RateLimitExceeded if the limit is reached.

    Fail strategy:
    - Sensitive paths (FAIL_CLOSED_PATHS): degraded mode via in-memory fallback
      when Redis is unavailable.
    - Read-only paths: fail-open (allows request through) to keep portfolio data available.
    """
    from limits import parse_many
    from slowapi.errors import RateLimitExceeded

    # Mock to satisfy RateLimitExceeded constructor (expects an object with `error_message`)
    class MockLimit:
        def __init__(self, msg):
            self.error_message = msg

    key = key_func(request)
    is_sensitive = request.url.path in FAIL_CLOSED_PATHS

    # Parse the limit string (e.g. "10/day" -> [Limit(...)])
    for limit in parse_many(limit_string):
        try:
            if not limiter.limiter.hit(limit, key):
                raise RateLimitExceeded(MockLimit(str(limit)))  # type: ignore
        except RateLimitExceeded:
            raise
        except Exception as e:
            import structlog

            logger = structlog.get_logger(__name__)

            # Emit Prometheus metric for alerting on Redis degradation
            _mode = "degraded" if is_sensitive else "fail_open"
            try:
                REDIS_UNAVAILABLE_COUNTER.labels(
                    path=request.url.path,
                    mode=_mode,
                ).inc()
            except Exception:
                pass  # Never fail the request due to a metrics error

            if is_sensitive:
                # Degraded mode: fall back to in-memory rate limiting so the
                # contact form remains functional during Redis outages while
                # still providing single-instance anti-abuse protection.
                logger.warning(
                    "rate_limiter_degraded_mode",
                    error=str(e),
                    error_type=type(e).__name__,
                    limit=str(limit),
                    path=request.url.path,
                    mode="degraded_memory_fallback",
                )
                try:
                    if not _fallback_limiter.limiter.hit(limit, key):
                        raise RateLimitExceeded(MockLimit(str(limit)))  # type: ignore
                except RateLimitExceeded:
                    raise
                except Exception:
                    # Even memory fallback failed — allow through as last resort
                    pass
                continue

            # Fail-open: allow through on read-only portfolio and chaos endpoints
            logger.error(
                "rate_limiter_backend_unavailable",
                error=str(e),
                limit=str(limit),
                path=request.url.path,
                mode="fail_open",
            )
            continue
