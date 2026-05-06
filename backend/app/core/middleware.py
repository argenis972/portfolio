"""
HTTP request middleware with structured logging.

Adds:
- Unique Request ID for tracking
- Structured logging with structlog
- Response time measurement
- Custom response headers
"""

import base64
import hmac
import json
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.adapters.logger_adapter import configure_structlog
from app.settings import settings
from app.core.rate_limit import get_client_ip
from app.utils.email import mask_email

# Configure structlog in the module
configure_structlog()
logger = structlog.get_logger(__name__)


def _get_loggable_identity(request: Request) -> str:
    identity = getattr(request.state, "identity", None)
    if not identity:
        return "ip"

    if identity.startswith("email:"):
        return f"email:{mask_email(identity.split(':', 1)[1])}"

    return identity


def _is_metrics_auth_valid(authorization_header: str | None) -> bool:
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False

    try:
        encoded_credentials = authorization_header.split(" ", 1)[1]
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return False

    return hmac.compare_digest(
        username, settings.metrics_basic_auth_username
    ) and hmac.compare_digest(
        password,
        settings.metrics_basic_auth_password,
    )


def _get_trace_id() -> str:
    """
    Extracts trace_id from active span in OpenTelemetry.

    Returns empty string if OTel is not configured or if there is no active span
    (e.g., during unit tests).
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.is_valid:
            return format(ctx.trace_id, "032x")
    except Exception:
        pass
    return ""


class RequestMiddleware(BaseHTTPMiddleware):
    """
    Middleware to process all HTTP requests.

    Features:
        - Generates unique request_id (UUID4)
        - Adds request_id to structlog context
        - Measures response time
        - Logs method, path, status, and duration
        - Adds headers: X-Request-ID, X-Response-Time
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Processes request and adds metadata.

        Args:
            request: Received HTTP request.
            call_next: Next handler in the chain.

        Returns:
            Response: Response with additional headers.
        """
        # Generate unique ID for tracking
        request_id = str(uuid.uuid4())

        # Add request_id to request state
        request.state.request_id = request_id

        # Add request_id to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # Start timestamp
        start_time = time.time()

        # Log received request
        logger.info(
            "request_received",
            query=str(request.url.query) if request.url.query else None,
            client_ip=get_client_ip(request),
            identity=_get_loggable_identity(request),
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise for handlers to catch
            logger.error(
                "request_processing_error",
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise

        # Calculate response time
        duration_ms = (time.time() - start_time) * 1000

        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Propagate OpenTelemetry trace_id (link with Jaeger/Grafana Tempo)
        trace_id = _get_trace_id()
        if trace_id:
            response.headers["X-Trace-ID"] = trace_id
            # Enrich log with trace_id to correlate logs + traces
            structlog.contextvars.bind_contextvars(trace_id=trace_id)

        # Log sent response
        logger.info(
            "response_sent",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Clear context
        structlog.contextvars.clear_contextvars()

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    Reflects protections configured in vercel.json for the backend.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        if not (
            request.url.path.startswith("/docs")
            or request.url.path.startswith("/redoc")
        ):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
            )

        return response


class MetricsAccessMiddleware(BaseHTTPMiddleware):
    """Restricts /metrics in production using basic auth."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path != "/metrics" or not settings.is_production:
            return await call_next(request)

        if _is_metrics_auth_valid(request.headers.get("authorization")):
            return await call_next(request)

        logger.warning(
            "metrics_access_denied",
            client_ip=get_client_ip(request),
        )
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="metrics"'},
        )


class ChaosMonkeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to simulate error and resilience scenarios.
    Activated via 'X-Debug-Mode' header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only active in non-production environments (settings.debug == True).
        # In production, X-Debug-Mode headers are unconditionally ignored to prevent
        # external actors from inducing synthetic 429/500 responses.
        if not settings.debug:
            return await call_next(request)

        # Simulate Rate Limit (429)
        if request.headers.get("X-Debug-Mode") == "simulate-429":
            logger.warning(
                "chaos_monkey_triggered",
                simulation="rate_limit_429",
                path=request.url.path,
            )
            return Response(
                status_code=429,
                content=json.dumps(
                    {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Chaos Monkey: Simulated rate limit exceeded",
                            "details": {"retry_after": 30},
                        }
                    }
                ),
                media_type="application/json",
                headers={"Retry-After": "30"},
            )

        # Simulate Internal Error (500)
        if request.headers.get("X-Debug-Mode") == "simulate-500":
            logger.error(
                "chaos_monkey_triggered",
                simulation="internal_error_500",
                path=request.url.path,
            )
            return Response(
                status_code=500,
                content=json.dumps(
                    {
                        "error": {
                            "code": "UNEXPECTED_ERROR",
                            "message": "Chaos Monkey: Simulated internal server error",
                        }
                    }
                ),
                media_type="application/json",
            )

        return await call_next(request)
