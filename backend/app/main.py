"""
Main FastAPI application module.

This module configures the FastAPI application with:
- CORS for local development (localhost:5173)
- Request middleware (request_id, logging, response time)
- Global exception handlers
- Health check endpoint (/health)
- Versioned API routes (/api/v1/*)
- API documentation: enabled in local/dev, disabled in production

Architecture: Simplified Clean Architecture
- Controllers (HTTP) → Use Cases (logic) → Entities (domain) → Adapters (external)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import asyncio
import os

from app import __version__
from app.settings import settings
from app.controllers import health_router
from app.controllers.v1 import router_v1
from app.core.handlers import register_exception_handlers
from app.core.infrastructure import dispose_all
from app.core.rate_limit import limiter
from app.core.middleware import (
    ChaosMonkeyMiddleware,
    MetricsAccessMiddleware,
    RequestMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.observability import setup_observability
from app.worker import StreamWorker


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """FastAPI lifespan context: startup → yield → shutdown.

    Starts the background job worker (Redis Streams) if configured.
    Shutdown: disposes the SQLAlchemy connection pool to avoid dangling
    connections during container restarts/rolling deploys.
    """
    worker_task = None
    if settings.redis_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        worker = StreamWorker(settings.redis_url)
        worker_task = asyncio.create_task(worker.run())
        app.state.worker = worker

    yield  # Application running

    # Shutdown
    if worker_task:
        app.state.worker.stop()
        # Give some time for the loop to finish or cancel it
        try:
            await asyncio.wait_for(worker_task, timeout=5.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

    await dispose_all()


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """
    settings.validate_production()

    # Disable interactive docs in production — no red flags for attackers,
    # no accidental schema leaks. Run locally with ENVIRONMENT=local to access /docs.
    _is_prod = settings.is_production
    application = FastAPI(
        title=settings.app_name,
        description=_get_api_description(),
        version=__version__,
        docs_url=None if _is_prod else "/docs",
        redoc_url=None if _is_prod else "/redoc",
        openapi_url=None if _is_prod else "/openapi.json",
        openapi_tags=_get_openapi_tags(),
        debug=settings.debug,
        lifespan=_lifespan,
    )

    # Observability must be initialized BEFORE middlewares and routes
    # to ensure Sentry and Prometheus are active from the beginning.
    setup_observability(application, settings)

    _configure_middleware(application)
    _configure_cors(application)
    _register_handlers(application)
    _register_limiter(application)
    _register_routes(application)

    return application


def _get_api_description() -> str:
    """
    Returns markdown description for OpenAPI documentation.

    Returns:
        str: Formatted markdown description.
    """
    return """
    REST API for a backend developer portfolio.

    ## Architecture
    - **Clean Architecture**: Controllers → Use Cases → Entities → Adapters
    - **Validation**: Pydantic V2
    - **Tests**: pytest with coverage
    - **Logging**: Structured with request_id
    - **i18n**: Text fields available in PT, EN, and ES

    ## Versioning
    - **v1**: `/api/v1/*` (stable)

    ## Response Format
    - **Success**: Returns validated data directly
    - **Error**:
      ```json
      {
        "error": {
          "code": "ERROR_CODE",
          "message": "Human-readable description",
          "details": {...}
        }
      }
      ```

    ## HTTP Status Codes
    - `200`: Success
    - `400`: Business rule error
    - `404`: Resource not found
    - `422`: Input validation failed
    - `429`: Too many requests (rate limited)
    - `500`: Internal server error

    ## Custom Headers
    - `X-Request-ID`: Unique ID for request tracing
    - `X-Response-Time`: Response time in ms
    """


def _get_openapi_tags() -> list[dict]:
    """
    Defines tags to group endpoints in documentation.

    Returns:
        list[dict]: List of tags with descriptions.
    """
    return [
        {
            "name": "Health",
            "description": "Health check and application status",
        },
        {
            "name": "API v1",
            "description": "API version 1 (recommended)",
        },
        {
            "name": "Portfolio",
            "description": "Portfolio data (about, projects, stack, experiences)",
        },
        {
            "name": "Contact",
            "description": "Contact form message submission",
        },
    ]


def _configure_cors(application: FastAPI) -> None:
    """
    Configures CORS (Cross-Origin Resource Sharing).
    """
    # For local development, we allow everything from localhost
    # but still respect the settings list for production-readiness.
    origins = settings.get_allowed_origins()

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=settings.regex_allowed_origins,
        allow_credentials=True,
        # Explicit allowlist instead of ["*"] to reduce attack surface.
        # Methods: GET (portfolio reads), POST (/contact), OPTIONS (CORS preflight).
        # Headers: Content-Type (JSON body), Idempotency-Key (contact dedup),
        #          Authorization (Basic Auth for /metrics), X-Chaos-Preset (telemetry).
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Idempotency-Key",
            "Authorization",
            "X-Chaos-Preset",
            "X-Debug-Mode",
        ],
        expose_headers=["X-Trace-ID", "X-Request-ID", "X-Response-Time"],
    )


def _configure_middleware(application: FastAPI) -> None:
    """
    Configures application middleware.
    """
    # 1. Request ID injection and structured logging
    application.add_middleware(RequestMiddleware)

    # 1.5. Protect the /metrics endpoint in production
    application.add_middleware(ChaosMonkeyMiddleware)
    application.add_middleware(MetricsAccessMiddleware)

    # 2. GZip compression (saves bandwidth, only for responses > 1KB)
    application.add_middleware(GZipMiddleware, minimum_size=1000)

    # 3. Security headers (Clickjacking protection, etc.)
    application.add_middleware(SecurityHeadersMiddleware)


def _register_handlers(application: FastAPI) -> None:
    """
    Registers global exception handlers.
    """
    register_exception_handlers(application)


def _register_limiter(application: FastAPI) -> None:
    """
    Configures the rate limiter in the application.
    """
    application.state.limiter = limiter


def _register_routes(application: FastAPI) -> None:
    """
    Registers all routers in the application.
    """
    # Health check (no prefix, used by probes)
    application.include_router(health_router)

    # Root route to avoid 404 (Koyeb/Public)
    @application.get("/", tags=["Health"])
    async def root():
        payload: dict = {
            "status": "ok",
            "service": settings.app_name,
            "version": __version__,
        }
        # Only advertise docs path in non-production environments.
        if not settings.is_production:
            payload["docs"] = "/docs"
        return payload

    # API v1 (recommended)
    application.include_router(router_v1, prefix="/api")

    # Legacy health check aliases — DEPRECATED since v1.9.2
    # These routes are kept for backward compatibility with any external probes
    # still pointing to the Portuguese/Spanish endpoints.
    # Canonical endpoint: GET /health
    # Planned removal: v1.9.3
    import structlog as _structlog

    _dep_logger = _structlog.get_logger(__name__)

    @application.get("/saude", include_in_schema=False, deprecated=True)
    @application.get("/salud", include_in_schema=False, deprecated=True)
    async def legacy_health_alias():
        _dep_logger.warning(
            "deprecated_endpoint_called",
            path="/saude (or /salud)",
            canonical="/health",
            removal_version="v1.9.3",
        )
        return {"status": "ok", "message": "API alive — deprecated alias, use /health"}


# Global application instance (used by uvicorn)
app = create_app()
