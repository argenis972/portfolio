"""
Health check controller.

Simple endpoint to verify if the API is responding.
Used by load balancers, Kubernetes probes, and monitoring.
"""

import time

from fastapi import APIRouter, Depends, Response

from app.adapters.repository import PortfolioRepository
from app.settings import settings
from app.controllers.dependencies import get_repository
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])

# Application initialization timestamp
_APP_START_TIME = time.time()


@router.get(
    "/live",
    summary="API liveness check",
    description="Returns OK when the API process is running without checking external dependencies.",
)
async def check_liveness() -> dict:
    """Cheap liveness endpoint for keep-alive jobs and platform probes."""
    return {"status": "ok", "message": "API alive"}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    description="Returns OK if the API is running. Includes version, environment, and detailed status of database and services.",
    responses={
        200: {"description": "API is healthy and running, or degraded but serving"},
    },
)
async def check_health(
    response: Response,
    repository: PortfolioRepository = Depends(get_repository),
) -> HealthResponse:
    """
    Verifies if the API and its dependencies are healthy.
    """
    uptime = int(time.time() - _APP_START_TIME)

    # Check database
    db_health = await repository.check_health()

    # Check email configuration
    email_configured = bool(settings.resend_api_key and settings.resend_api_key.strip())

    details = {
        "database": db_health["status"],
        "email": "configured" if email_configured else "pending",
        "db_details": db_health["details"],
    }

    is_healthy = db_health["status"] == "ok"

    return HealthResponse(
        status="ok" if is_healthy else "degraded",
        message=(
            "API functioning normally"
            if is_healthy
            else "API degraded (fail-silent mode active)"
        ),
        api_version="1.7.0",
        environment=settings.environment,
        uptime_seconds=uptime,
        details=details,
    )
