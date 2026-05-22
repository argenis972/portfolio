from prometheus_client import Counter, Gauge, Histogram

_processed = Counter(
    "worker_jobs_processed_total",
    "Total jobs processed by worker",
    ["status", "reason"],
)
_duration = Histogram("worker_job_duration_seconds", "Worker job duration in seconds")
_dlq = Counter("worker_dlq_total", "Jobs moved to DLQ", ["reason"])
_lag = Gauge("worker_consumer_lag", "Estimated consumer lag")
_retries = Counter("worker_retries_total", "Worker retries", ["reason"])
_pel = Gauge(
    "worker_pel_size", "Worker pending entries list size", ["group", "consumer"]
)
_recovery_runs = Counter(
    "worker_recovery_runs_total", "Recovery loop executions", ["pending_count"]
)
_reclaimed = Counter("worker_messages_reclaimed_total", "Messages reclaimed from PEL")
_quota_blocks = Counter(
    "worker_quota_blocks_total", "Times circuit breaker blocked Redis usage"
)


def observe_job_duration(value: float) -> None:
    _duration.observe(value)


def inc_processed(status: str, reason: str) -> None:
    _processed.labels(status=status, reason=reason).inc()


def inc_dlq(reason: str) -> None:
    _dlq.labels(reason=reason).inc()


def inc_retry(reason: str) -> None:
    _retries.labels(reason=reason).inc()


def inc_recovery_run(pending_count: int) -> None:
    _recovery_runs.labels(pending_count=str(pending_count)).inc()


def inc_reclaimed(count: int = 1) -> None:
    _reclaimed.inc(count)


def inc_quota_block() -> None:
    _quota_blocks.inc()


def set_lag(value: int) -> None:
    _lag.set(value)


def set_pel_size(group: str, consumer: str, value: int) -> None:
    _pel.labels(group=group, consumer=consumer).set(value)
