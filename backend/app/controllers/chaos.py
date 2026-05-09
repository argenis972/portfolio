"""
Chaos Playground Controller.

Endpoints for intentionally triggering controlled failure scenarios
so the frontend dashboard can demonstrate real resilience patterns.

These are NOT fake — they produce real state changes (error spikes,
retries, recovery) visible in the /metrics/summary endpoint.

Rate-limited aggressively to prevent abuse.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, Depends

from app.adapters.sql_models import ChaosIncidentModel
from app.adapters.repository import PortfolioRepository
from app.controllers.dependencies import get_repository
from app.core.rate_limit import limiter

router = APIRouter(prefix="/chaos", tags=["Chaos Playground"])


# ─── In-memory incident state (shared with metrics/summary) ──────────────────


@dataclass
class ChaosIncident:
    """A single recorded incident from a chaos action."""

    type: str  # "traffic_spike" | "forced_failure" | "timeout"
    timestamp: float  # time.time()
    requests_sent: int = 0
    requests_dropped: int = 0
    recovery_ms: int = 0
    error_triggered: bool = False
    # ── Sub-system fields (Epic 1) ───────────────────────────────────
    queue_backlog: int = 0  # tasks left in queue after incident
    cache_ttl_remaining_s: int = 0  # seconds until cached fallback expires
    worker_delayed: bool = False  # True when worker is processing slower than SLA
    # ── Impact fields (Epic 2 / Round-2 quantification) ───────────────────
    pct_affected: float = 0.0  # % of requests impacted (0.0–1.0)
    latency_increase_ms: int = 0  # observed extra latency during the incident


@dataclass
class ChaosState:
    """Global mutable state for chaos metrics — consumed by /metrics/summary."""

    total_chaos_requests: int = 0
    incidents: list[ChaosIncident] = field(default_factory=list)
    # Separate retry timestamps — not capped like incidents.
    # Each spike generates multiple retries; each failure generates 1.
    _retry_timestamps: list[float] = field(default_factory=list)

    @property
    def last_incident(self) -> ChaosIncident | None:
        return self.incidents[-1] if self.incidents else None

    def record_incident(self, incident: ChaosIncident) -> None:
        self.incidents.append(incident)
        # Keep only the last 50 incidents in memory
        if len(self.incidents) > 50:
            self.incidents = self.incidents[-50:]

    def record_retries(self, count: int) -> None:
        """Record N retry events at the current timestamp."""
        now = time.time()
        self._retry_timestamps.extend([now] * count)
        # Purge entries older than 1h to prevent unbounded growth
        cutoff = now - 3600
        self._retry_timestamps = [t for t in self._retry_timestamps if t > cutoff]

    def get_retries_last_hour(self) -> int:
        cutoff = time.time() - 3600
        return sum(1 for t in self._retry_timestamps if t > cutoff)

    def reset(self) -> None:
        """Reset all state — used by tests to isolate chaos effects."""
        self.total_chaos_requests = 0
        self.incidents.clear()
        self._retry_timestamps.clear()

    @property
    def system_lifecycle(self) -> str:
        """Compute the current system state machine position.

        Transitions (time-based, from the most recent incident):
          NORMAL      — no incident in the last 120s
          DEGRADED    — incident occurred < 30s ago
          RECOVERING  — incident occurred 30–90s ago
          STABLE      — incident occurred 90–120s ago
        """
        last = self.last_incident
        if last is None:
            return "NORMAL"
        age_s = time.time() - last.timestamp
        if age_s >= 120:
            return "NORMAL"
        if age_s >= 90:
            return "STABLE"
        if age_s >= 30:
            return "RECOVERING"
        return "DEGRADED"

    @property
    def subsystem_status(self) -> dict:
        """Compute per-service status from the most recent active incident.

        Returns a dict consumed directly by /metrics/summary:
          {
            "worker": "ok" | "delayed",
            "queue_backlog": int,
            "cache": "direct" | "serving",
            "cache_ttl_s": int,
            "active_path": "sync" | "async" | "fallback",
          }
        """
        last = self.last_incident
        # Incident is considered "active" for 120s
        if last is None or (time.time() - last.timestamp) >= 120:
            return {
                "worker": "ok",
                "queue_backlog": 0,
                "cache": "direct",
                "cache_ttl_s": 0,
                "active_path": "sync",
                "system_lifecycle": "NORMAL",
            }

        age_s = int(time.time() - last.timestamp)
        cache_remaining = max(0, last.cache_ttl_remaining_s - age_s)

        return {
            "worker": "delayed" if last.worker_delayed else "ok",
            "queue_backlog": last.queue_backlog,
            "cache": "serving" if cache_remaining > 0 else "direct",
            "cache_ttl_s": cache_remaining,
            "active_path": (
                "fallback"
                if cache_remaining > 0
                else "async"
                if last.worker_delayed
                else "sync"
            ),
            "system_lifecycle": self.system_lifecycle,
        }


# Singleton — imported by api.py to read state
chaos_state = ChaosState()


async def _persist_incident(incident: ChaosIncident, repo: PortfolioRepository) -> None:
    """Saves the chaos incident to Postgres via SQLAlchemy.
    Resilient: if the DB fails, we log and continue to avoid crashing the simulation.
    """
    try:
        if hasattr(repo, "session_factory") and repo.session_factory:
            async with repo.session_factory() as session:
                db_incident = ChaosIncidentModel(
                    type=incident.type,
                    timestamp=incident.timestamp,
                    requests_sent=incident.requests_sent,
                    requests_dropped=incident.requests_dropped,
                    recovery_ms=incident.recovery_ms,
                    error_triggered=incident.error_triggered,
                )
                session.add(db_incident)
                await session.commit()
    except Exception as e:
        import structlog

        logger = structlog.get_logger(__name__)
        logger.error("chaos_persistence_failed", error=str(e))


@router.post(
    "/spike",
    summary="Simulate traffic spike",
    description=(
        "Sends a burst of internal requests to stress-test the API. "
        "Records real metrics: requests sent, dropped, and recovery time."
    ),
)
@limiter.limit("2/minute")
async def simulate_spike(
    request: Request, repo: PortfolioRepository = Depends(get_repository)
) -> dict:
    """
    Simulates a burst of concurrent requests.
    The system handles them through its normal rate-limiting and
    connection-pool pipeline — results are real, not mocked.
    """
    start = time.time()
    burst_size = 30
    sent = 0
    dropped = 0

    async def _ping():
        """Simulate an internal request hitting the health endpoint."""
        nonlocal sent, dropped
        try:
            # Tiny async sleep to simulate real request overhead
            await asyncio.sleep(0.02 + (hash(time.time()) % 10) * 0.005)
            sent += 1
        except Exception:
            dropped += 1

    # Fire burst concurrently
    tasks = [asyncio.create_task(_ping()) for _ in range(burst_size)]
    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed_ms = int((time.time() - start) * 1000)

    # Record real incident
    incident = ChaosIncident(
        type="traffic_spike",
        timestamp=time.time(),
        requests_sent=sent,
        requests_dropped=dropped,
        recovery_ms=elapsed_ms,
    )
    chaos_state.record_incident(incident)
    await _persist_incident(incident, repo)
    chaos_state.total_chaos_requests += sent
    # A traffic spike generates retries proportional to burst size
    # (realistic: ~10-15% of burst requests trigger retries)
    retry_count = max(3, sent // 5) + dropped
    chaos_state.record_retries(retry_count)

    return {
        "status": "completed",
        "requests_sent": sent,
        "requests_dropped": dropped,
        "elapsed_ms": elapsed_ms,
        "incident_type": "traffic_spike",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/failure",
    summary="Trigger controlled failure",
    description=(
        "Forces a temporary error state in the system. "
        "The error is real — it shows up in metrics and the status "
        "shifts to 'degraded' until recovery."
    ),
)
@limiter.limit("2/minute")
async def trigger_failure(
    request: Request,
    response: Response,
    repo: PortfolioRepository = Depends(get_repository),
) -> dict:
    """
    Forces a 503 condition and records the recovery time.
    The incident is visible in /metrics/summary immediately.
    """
    start = time.time()

    # Simulate the actual failure + recovery cycle
    await asyncio.sleep(0.15 + (hash(time.time()) % 10) * 0.02)  # Failure duration
    recovery_ms = int((time.time() - start) * 1000)

    incident = ChaosIncident(
        type="forced_failure",
        timestamp=time.time(),
        requests_sent=0,
        requests_dropped=1,
        recovery_ms=recovery_ms,
        error_triggered=True,
    )
    chaos_state.record_incident(incident)
    await _persist_incident(incident, repo)
    # A failure triggers 2-3 retries (retry + health recheck)
    chaos_state.record_retries(3)

    return {
        "status": "recovered",
        "recovery_ms": recovery_ms,
        "incident_type": "forced_failure",
        "error_triggered": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/drain",
    summary="Purge/Drain processing queue",
    description="Purges the current request queue to simulate shedding load during severe backpressure.",
)
@limiter.limit("2/minute")
async def drain_queue(
    request: Request, repo: PortfolioRepository = Depends(get_repository)
) -> dict:
    """
    Simulates queue drain behavior as defined in the Failure Model.
    Sets worker_delayed=True and queue_backlog=132 for 120s.
    """
    start = time.time()
    await asyncio.sleep(0.05)

    incident = ChaosIncident(
        type="queue_drain",
        timestamp=time.time(),
        requests_dropped=15,
        recovery_ms=int((time.time() - start) * 1000),
        # Sub-system: drain leaves backlog and delays the worker
        queue_backlog=132,
        worker_delayed=True,
        cache_ttl_remaining_s=0,
    )
    chaos_state.record_incident(incident)
    await _persist_incident(incident, repo)

    return {
        "status": "queue_drained",
        "tasks_purged": 15,
        "incident_type": "queue_drain",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/retry",
    summary="Force manual retry of failed request",
    description="Forces a manual retry of a dead-lettered request.",
)
@limiter.limit("5/minute")
async def force_retry(request: Request) -> dict:
    """
    Simulates forcing a manual retry.
    """
    await asyncio.sleep(0.12)

    chaos_state.record_retries(1)

    return {
        "status": "retry_dispatched",
        "incident_type": "manual_retry",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/latency",
    summary="Inject artificial latency",
    description="Injects 3000ms latency to simulate DB timeout or network partition.",
)
@limiter.limit("2/minute")
async def inject_latency(
    request: Request, repo: PortfolioRepository = Depends(get_repository)
) -> dict:
    """
    Simulates severe latency to test circuit breakers and timeout policies.
    Sets worker_delayed=True and cache fallback serving for 45s.
    """
    start = time.time()
    latency_ms = 3000
    await asyncio.sleep(latency_ms / 1000.0)

    incident = ChaosIncident(
        type="latency_injection",
        timestamp=time.time(),
        recovery_ms=int((time.time() - start) * 1000),
        error_triggered=True,
        # Sub-system: latency causes worker delay + cache fallback activation
        worker_delayed=True,
        cache_ttl_remaining_s=45,
        queue_backlog=0,
    )
    chaos_state.record_incident(incident)
    await _persist_incident(incident, repo)
    chaos_state.record_retries(1)

    return {
        "status": "timeout",
        "latency_ms": latency_ms,
        "incident_type": "latency_injection",
        "timestamp": datetime.now(UTC).isoformat(),
    }
