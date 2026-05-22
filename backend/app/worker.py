"""
Worker process for consuming jobs from Redis Streams.
"""

import asyncio
import json
import os
import signal
import sys
import time
import random
from datetime import datetime, timezone
from typing import Any, Dict

import sentry_sdk
import structlog
from redis import asyncio as redis

from app.controllers.dependencies import get_send_contact_use_case
from app.core.queue import RedisStreamsQueue
from app.settings import settings
from app.worker_metrics import (
    inc_dlq,
    inc_processed,
    inc_quota_block,
    inc_reclaimed,
    inc_recovery_run,
    inc_retry,
    observe_job_duration,
    set_pel_size,
)

logger = structlog.get_logger(__name__)
MAX_RETRIES = 3
_RECOVERY_INTERVAL = 300
_QUOTA_COOLDOWN_HOURS = 1
_QUOTA_COOLDOWN_SLEEP = 30


class StreamWorker:
    """
    Consumer for Redis Streams jobs with circuit breaker and separate recovery loop.
    """

    def __init__(
        self,
        redis_url: str,
        stream_name: str = "contact_jobs",
        group_name: str = "email_workers",
        consumer_name: str = f"worker-{os.getpid()}",
        recovery_interval: int = 300,
    ):
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.recovery_interval = recovery_interval
        self.running = True
        self._redis: redis.Redis | None = None
        self.redis_disabled_until: float | None = None

    def _is_redis_disabled(self) -> bool:
        if self.redis_disabled_until is None:
            return False
        if time.time() >= self.redis_disabled_until:
            self.redis_disabled_until = None
            return False
        return True

    async def _get_client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=60,
            )
        return self._redis

    async def setup(self) -> bool:
        """Initializes the stream and consumer group.

        Returns True if the worker can start, False if Redis quota is exceeded.
        """
        client = await self._get_client()
        try:
            await client.xgroup_create(
                self.stream_name, self.group_name, id="0", mkstream=True
            )
            logger.info("consumer_group_created", group=self.group_name)
            return True
        except redis.ResponseError as e:
            error_msg = str(e)
            if "BUSYGROUP" in error_msg:
                logger.info("consumer_group_exists", group=self.group_name)
                return True
            if "max requests limit exceeded" in error_msg:
                logger.warning(
                    "worker_setup_quota_exceeded",
                    provider="upstash",
                )
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("failure_type", "quota_exceeded")
                    scope.set_tag("worker_phase", "setup")
                    sentry_sdk.capture_message(
                        "upstash_quota_exceeded", level="warning"
                    )
                return False
            logger.error("worker_setup_failed", error=error_msg)
            return False

    async def _move_to_dlq(
        self, job_id: str, body: dict[str, Any], reason: str, error_type: str
    ):
        queue = RedisStreamsQueue(self.redis_url, stream_name=self.stream_name)
        await queue.enqueue_dlq(
            job_name=body["job_name"],
            payload=body["payload"],
            metadata=body["meta"],
            reason=reason,
            error_type=error_type,
        )
        logger.error(
            "job_moved_to_dlq", job_id=job_id, reason=reason, error_type=error_type
        )
        inc_dlq(reason)

    async def process_job(self, job_id: str, data: Dict[str, Any]):
        """Dispatches the job to the appropriate use case."""
        job_name = data.get("job_name")
        payload_str = data.get("payload")

        if not job_name or not payload_str:
            raise ValueError("invalid_job_data")

        body = json.loads(payload_str)
        payload = body.get("payload")
        meta = body.get("meta") or {}
        meta["retry_count"] = int(meta.get("retry_count", 0))
        meta["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
        body["meta"] = meta

        if job_name == "send_contact_email":
            uc = get_send_contact_use_case()
            logger.info(
                "processing_email_job", job_id=job_id, sender=payload.get("email")
            )

            success = await uc.execute(
                name=payload["name"],
                email=payload["email"],
                subject=payload.get("subject", ""),
                message=payload["message"],
                is_suspicious=payload.get("is_suspicious", False),
                spam_score=payload.get("spam_score"),
            )

            if not success:
                raise RuntimeError("provider_unknown_failure")

    async def _handle_failure(self, job_id: str, body: dict[str, Any], exc: Exception):
        meta = body.get("meta", {})
        retry_count = int(meta.get("retry_count", 0))
        message = str(exc).lower()
        if (
            isinstance(exc, (json.JSONDecodeError, KeyError, ValueError))
            or "4" in message
            or "schema" in message
            or "invalid" in message
        ):
            failure_class = "permanent"
        elif (
            "timeout" in message
            or "connection" in message
            or "5" in message
            or "reset" in message
        ):
            failure_class = "transient"
        else:
            failure_class = "unknown"

        meta["failure_class"] = failure_class
        meta["last_error"] = str(exc)
        meta["last_error_type"] = type(exc).__name__

        max_retries_for_class = (
            MAX_RETRIES
            if failure_class == "transient"
            else (1 if failure_class == "unknown" else 0)
        )

        if retry_count < max_retries_for_class:
            meta["retry_count"] = retry_count + 1
            if failure_class == "transient":
                backoff = (2**retry_count) + random.uniform(0, 0.5)
            else:
                backoff = 0.2

            logger.warning(
                "job_retry_scheduled",
                job_id=job_id,
                retry_count=meta["retry_count"],
                backoff=backoff,
            )
            inc_retry(failure_class)
            await asyncio.sleep(backoff)

            first_seen_at = meta.get("first_seen_at")
            if first_seen_at:
                try:
                    age = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(first_seen_at)
                    ).total_seconds()
                    if age > 900:
                        await self._move_to_dlq(
                            job_id, body, "max_age_exceeded", "TimeoutError"
                        )
                        client = await self._get_client()
                        await client.xack(self.stream_name, self.group_name, job_id)
                        return
                except Exception:
                    pass

            client = await self._get_client()
            body["meta"] = meta
            await client.xadd(
                self.stream_name,
                {
                    "job_name": body.get("job_name", "unknown"),
                    "payload": json.dumps(body),
                },
                maxlen=10000,
                approximate=True,
            )
            await client.xack(self.stream_name, self.group_name, job_id)
            return

        await self._move_to_dlq(job_id, body, str(exc), type(exc).__name__)
        client = await self._get_client()
        await client.xack(self.stream_name, self.group_name, job_id)

    async def _recovery_loop(self):
        """Periodically reclaims messages stuck in PEL.

        Runs every 5 minutes, independent of the main consumption loop.
        This separation keeps the hot path lean and recovery observable.
        """
        while self.running:
            try:
                if self._is_redis_disabled():
                    await asyncio.sleep(self.recovery_interval)
                    continue

                client = await self._get_client()
                pel = await client.xpending(self.stream_name, self.group_name)
                pending_count = 0
                if isinstance(pel, dict):
                    pending_count = pel.get("pending", 0) or 0
                elif pel:
                    pending_count = int(pel[0])

                inc_recovery_run(pending_count)

                if pending_count > 0:
                    logger.info("recovery_check_pel", pending=pending_count)
                    claimed = await client.xautoclaim(
                        self.stream_name,
                        self.group_name,
                        self.consumer_name,
                        min_idle_time=300000,
                        start_id="0",
                        count=10,
                    )
                    if claimed and len(claimed) > 1 and claimed[1]:
                        reclaimed_count = len(claimed[1])
                        inc_reclaimed(reclaimed_count)
                        logger.info(
                            "recovery_reclaimed",
                            count=reclaimed_count,
                        )
                await asyncio.sleep(self.recovery_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("recovery_loop_error", error=str(e))
                await asyncio.sleep(self.recovery_interval)

    async def run(self):
        """Main consumption loop with separate recovery task."""
        setup_ok = await self.setup()
        if not setup_ok:
            self.redis_disabled_until = time.time() + 3600 * _QUOTA_COOLDOWN_HOURS
            logger.warning(
                "worker_disabled",
                reason="redis_quota_exceeded",
                cooldown_hours=_QUOTA_COOLDOWN_HOURS,
            )
            return

        client = await self._get_client()
        recovery_task = asyncio.create_task(self._recovery_loop())

        logger.info("worker_started", consumer=self.consumer_name)

        try:
            while self.running:
                if self._is_redis_disabled():
                    await asyncio.sleep(_QUOTA_COOLDOWN_SLEEP)
                    continue

                try:
                    response = await client.xreadgroup(
                        self.group_name,
                        self.consumer_name,
                        {self.stream_name: ">"},
                        count=1,
                        block=30000,
                    )
                    if not response:
                        continue

                    for stream, stream_messages in response:
                        for job_id, data in stream_messages:
                            try:
                                started = time.perf_counter()
                                logger.info("job_processing_started", job_id=job_id)
                                await self.process_job(job_id, data)
                                await client.xack(
                                    self.stream_name, self.group_name, job_id
                                )
                                set_pel_size(self.group_name, self.consumer_name, 0)
                                observe_job_duration(time.perf_counter() - started)
                                inc_processed("success", "ok")
                                logger.info("job_acked", job_id=job_id)
                            except Exception as e:
                                try:
                                    body = json.loads(data.get("payload", "{}"))
                                except Exception:
                                    body = {
                                        "job_name": data.get("job_name", "unknown"),
                                        "payload": {},
                                        "meta": {},
                                    }
                                try:
                                    await self._handle_failure(job_id, body, e)
                                except Exception:
                                    logger.error(
                                        "job_processing_crash",
                                        job_id=job_id,
                                        error=str(e),
                                    )
                                    continue
                                inc_processed("failed", type(e).__name__)
                                logger.error(
                                    "job_processing_crash",
                                    job_id=job_id,
                                    error=str(e),
                                )

                except asyncio.CancelledError:
                    break
                except redis.ResponseError as e:
                    error_msg = str(e)
                    if "max requests limit exceeded" in error_msg:
                        self.redis_disabled_until = (
                            time.time() + 3600 * _QUOTA_COOLDOWN_HOURS
                        )
                        inc_quota_block()
                        logger.warning(
                            "redis_quota_exceeded_circuit_breaker",
                            cooldown_hours=_QUOTA_COOLDOWN_HOURS,
                        )
                        with sentry_sdk.push_scope() as scope:
                            scope.set_tag("failure_type", "quota_exceeded")
                            scope.set_tag("worker_phase", "consume")
                            sentry_sdk.capture_message(
                                "upstash_quota_exceeded", level="warning"
                            )
                    else:
                        logger.error("worker_redis_response_error", error=error_msg)
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error("worker_loop_error", error=str(e))
                    await asyncio.sleep(1)
        finally:
            recovery_task.cancel()
            try:
                await recovery_task
            except asyncio.CancelledError:
                pass

    def stop(self):
        self.running = False


async def main():
    if not settings.redis_url:
        print("REDIS_URL not configured. Worker exiting.")
        return

    worker = StreamWorker(settings.redis_url)

    # Handle termination signals for graceful shutdown.
    # loop.add_signal_handler is only available on Unix; use signal.signal as
    # a fallback on Windows (which delivers the handler on the main thread).
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, worker.stop)
    else:
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda _sig, _frame: worker.stop())

    try:
        await worker.run()
    finally:
        print("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
