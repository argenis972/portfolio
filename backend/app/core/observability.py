"""
Central Observability Module.

Configures three pillars of observability:
  1. Sentry        — Error tracking and performance monitoring in production
  2. Prometheus    — Automatic HTTP metrics (via prometheus-fastapi-instrumentator)
  3. OpenTelemetry — Distributed tracing (end-to-end spans per request)

Deploy:
  - Koyeb (backend): exposes /metrics and sends traces via OTLP_ENDPOINT (optional)
  - Vercel (frontend): not affected by this module
"""

from typing import Any

import structlog
from fastapi import FastAPI

logger = structlog.get_logger(__name__)


# ===========================================================================
# 1. SENTRY — Error Tracking
# ===========================================================================


def _setup_sentry(dsn: str, environment: str, traces_sample_rate: float) -> None:
    """
    Initializes the Sentry SDK.

    Only activates if SENTRY_DSN is configured — safe in development
    and in test environments where the variable does not exist.

    Args:
        dsn: Sentry project connection URL.
        environment: Environment name (local, staging, production).
        traces_sample_rate: Percentage of transactions captured (0.0 to 1.0).
    """
    if not dsn:
        logger.info("sentry_disabled", reason="SENTRY_DSN not configured")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            # Capture headers and request data to facilitate debug
            send_default_pii=False,  # False: does not capture user data by default
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            # Ignores errors that are expected behavior (not bugs)
            ignore_errors=[
                KeyboardInterrupt,
            ],
        )
        logger.info(
            "sentry_configured",
            environment=environment,
            traces_sample_rate=traces_sample_rate,
        )
    except ImportError:
        logger.warning("sentry_sdk_not_installed")


# ===========================================================================
# 2. PROMETHEUS — HTTP Metrics
# ===========================================================================


def _setup_prometheus(app: FastAPI) -> None:
    """
    Instruments FastAPI with automatic Prometheus metrics.

    Exposes the GET /metrics endpoint with the following metrics per route:
      - http_requests_total          (counter)   — total requests by status/method
      - http_request_size_bytes      (histogram) — request size
      - http_response_size_bytes     (histogram) — response size
      - http_request_duration_seconds (histogram) — latency (P50, P95, P99)

    The /metrics endpoint is compatible with direct Prometheus scraping.
    On Koyeb, it becomes publicly accessible at https://<app>.koyeb.app/metrics.
    """
    try:
        from prometheus_fastapi_instrumentator import Instrumentator, metrics
        from app import __version__

        instrumentator = Instrumentator(
            should_group_status_codes=True,  # groups 2xx, 4xx, 5xx
            should_ignore_untemplated=True,  # ignores routes without template (invalid 404s)
            should_respect_env_var=False,  # always active
            excluded_handlers=["/metrics"],  # do not auto-instrument /metrics itself
        )

        # Custom metrics configuration for version 7.x
        instrumentator.add(metrics.requests())
        instrumentator.add(
            metrics.latency(
                buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.5, 5.0, 10.0)
            )
        )

        # Application version metric (Info type)
        try:
            from prometheus_client import Info

            i = Info("app_version", "Current application version")
            i.info({"version": __version__})
        except Exception:
            # Avoid crashing if Info is already registered (re-imports)
            pass

        instrumentator.instrument(app).expose(
            app,
            endpoint="/metrics",
            include_in_schema=False,  # do not show in /docs
            tags=["Observability"],
        )

        logger.info("prometheus_configured", endpoint="/metrics")
    except ImportError:
        logger.warning("prometheus_fastapi_instrumentator_not_installed")


# ===========================================================================
# 3. OPENTELEMETRY — Distributed Tracing
# ===========================================================================


def _setup_opentelemetry(
    app: FastAPI,
    service_name: str,
    version: str,
    environment: str,
    otlp_endpoint: str,
    sentry_dsn: str = "",
) -> None:
    """
    Configures the OpenTelemetry SDK for distributed tracing.

    In development (without OTLP_ENDPOINT): uses ConsoleSpanExporter to
    print spans to stdout — useful for local debug.

    In production (with OTLP_ENDPOINT): exports spans via OTLP/HTTP to
    any compatible backend (Jaeger, Grafana Tempo, Honeycomb, etc).

    IMPORTANT: Do not use Sentry's OTLP endpoint here!
    The Sentry SDK (initialized in _setup_sentry) already captures tracing
    automatically via traces_sample_rate. Using Sentry's OTLP_ENDPOINT
    results in 401 errors as it requires special authentication not supported
    by the default OTLP exporter. Use only for standalone backends:
    Jaeger, Grafana Tempo, Honeycomb, etc.

    Args:
        service_name: Service name for identification in traces.
        version: Application version.
        environment: Execution environment.
        otlp_endpoint: OTLP collector URL (ex: http://jaeger:4318).
                       Leave empty if using Sentry — the SDK already handles tracing.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Resource with service metadata
        resource = Resource.create(
            {
                SERVICE_NAME: service_name,
                SERVICE_VERSION: version,
                "deployment.environment": environment,
            }
        )

        provider = TracerProvider(resource=resource)

        # Exporter based on environment
        import io
        import os
        import sys

        if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            # During tests, we do not use BatchSpanProcessor to avoid
            # the "ValueError: I/O operation on closed file." error at the end.
            from opentelemetry.sdk.trace.export import (
                ConsoleSpanExporter,
                SimpleSpanProcessor,
            )

            exporter: Any = ConsoleSpanExporter(out=io.StringIO())
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            logger.info("otel_exporter_mock", reason="Test execution detected")
        elif otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_endpoint = otlp_endpoint.strip().rstrip("/")

            if "sentry.io" in otlp_endpoint:
                logger.warning(
                    "otel_exporter_sentry_endpoint_ignored",
                    reason="The Sentry SDK already handles tracing natively. "
                    "Use OTLP_ENDPOINT only for Jaeger/Grafana Tempo. ",
                    endpoint=otlp_endpoint,
                )
            else:
                final_endpoint = (
                    f"{otlp_endpoint}/v1/traces"
                    if not otlp_endpoint.endswith("/v1/traces")
                    else otlp_endpoint
                )

                exporter = OTLPSpanExporter(endpoint=final_endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("otel_exporter_otlp", endpoint=final_endpoint)

        else:
            if environment == "production":
                logger.info(
                    "otel_exporter_console_skip",
                    reason="Empty OTLP_ENDPOINT in production; tracing spans will not be exported",
                )
                return

            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("otel_exporter_console", reason="OTLP_ENDPOINT not configured")

        # Register as global provider
        trace.set_tracer_provider(provider)

        # Auto-instrument FastAPI (captures spans per endpoint automatically)
        FastAPIInstrumentor().instrument_app(
            app,
            tracer_provider=provider,
            server_request_hook=_request_hook,
        )

        logger.info(
            "opentelemetry_configured",
            service=service_name,
            environment=environment,
        )
    except ImportError:
        logger.warning("opentelemetry_sdk_not_installed")


def _request_hook(span, scope: dict) -> None:
    """
    Hook executed when starting each request span.

    Adds extra attributes to the span to facilitate filtering in the tracing backend
    (Jaeger, Grafana Tempo, etc).

    Args:
        span: Current OpenTelemetry span.
        scope: ASGI scope of the request.
    """
    if span and span.is_recording():
        headers = dict(scope.get("headers", []))
        # X-Request-ID already generated by our middleware
        request_id = headers.get(b"x-request-id", b"").decode("utf-8")
        if request_id:
            span.set_attribute("http.request_id", request_id)


# ===========================================================================
# ENTRY POINT — called in main.py startup
# ===========================================================================


def setup_observability(app: FastAPI, settings) -> None:
    """
    Single entry point to configure the entire observability stack.

    Deliberate order:
      1. Sentry first — captures errors that may occur during initialization
    """
    from app import __version__

    logger.info("observability_initializing", environment=settings.environment)

    _setup_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )

    _setup_prometheus(app)

    _setup_opentelemetry(
        app=app,
        service_name=settings.app_name,
        version=__version__,
        environment=settings.environment,
        otlp_endpoint=settings.otlp_endpoint,
        sentry_dsn=settings.sentry_dsn,
    )

    logger.info("observability_ready")
