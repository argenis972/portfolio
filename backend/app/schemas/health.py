"""
Pydantic schemas for health endpoint.

Defines input/output contracts for automatic validation.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Health check response schema.

    Attributes:
        status: API Status ("ok" or "error").
        message: Human-readable status description.
        api_version: API Version.
        environment: Execution environment.
        uptime_seconds: Time since startup (optional).
        details: Optional component details.
    """

    status: str = Field(
        ...,
        examples=["ok"],
        description="API status",
    )
    message: str = Field(
        ...,
        examples=["API functioning normally"],
        description="Human-readable status message",
    )
    api_version: str = Field(
        ...,
        examples=["1.0.0"],
        description="API version",
    )
    environment: str = Field(
        ...,
        examples=["local", "staging", "production"],
        description="Execution environment",
    )
    uptime_seconds: int | None = Field(
        default=None,
        examples=[3600],
        description="Seconds since initialization",
    )
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Component status details",
    )


class MetricsSummary(BaseModel):
    """
    Simplified schema for frontend evidence dashboard.
    """

    p95_ms: int = Field(..., examples=[43], description="P95 latency in ms")
    p95_status: str = Field(..., examples=["healthy"], description="Latency status")
    requests_24h: int = Field(..., examples=[987], description="Total requests (24h)")
    error_rate: float = Field(..., examples=[0.0131], description="Decimal error rate")
    error_rate_pct: str = Field(
        ..., examples=["1.31%"], description="Formatted error rate"
    )
    error_rate_status: str = Field(
        ..., examples=["stable"], description="Error rate status"
    )
    system_status: str = Field(
        ..., examples=["operational"], description="Overall system state"
    )
    uptime: str = Field(..., examples=["2h 14m"], description="Formatted activity time")
    window: str = Field(..., examples=["last_24h"], description="Metrics time window")
    timestamp: str = Field(..., description="ISO 8601 reading timestamp")
    retries_1h: int = Field(
        default=0, examples=[3], description="Retries triggered in the last hour"
    )
    last_incident: str = Field(
        default="none",
        examples=["traffic_spike", "forced_failure", "none"],
        description="Type of last incident recorded",
    )
    last_incident_ago: str = Field(
        default="none",
        examples=["12m ago", "none"],
        description="Time since last incident (human-readable)",
    )
    # ── Sub-system status fields (Epic 1: degraded state detail) ──────────────
    worker_status: str = Field(
        default="ok",
        examples=["ok", "delayed"],
        description="Worker/queue processor status",
    )
    queue_backlog: int = Field(
        default=0,
        examples=[132, 0],
        description="Number of tasks currently in the queue backlog",
    )
    cache_status: str = Field(
        default="direct",
        examples=["direct", "serving"],
        description="Cache serving mode: 'direct' (passthrough) or 'serving' (cached fallback)",
    )
    cache_ttl_s: int = Field(
        default=0,
        examples=[45, 0],
        description="Remaining TTL in seconds when cache is serving",
    )
    active_path: str = Field(
        default="sync",
        examples=["sync", "async", "fallback"],
        description="Active execution path: sync (FastAPI direct), async (Queue+Worker), fallback (Cache)",
    )
    system_lifecycle: str = Field(
        default="NORMAL",
        examples=["NORMAL", "DEGRADED", "RECOVERING", "STABLE"],
        description="Current state machine position based on time-since-last-incident",
    )
    total_incidents_24h: int = Field(
        default=0,
        examples=[12],
        description="Total number of chaos incidents recorded in the last 24h window",
    )
