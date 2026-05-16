"""
Worker process for consuming jobs from Redis Streams.
"""

import asyncio
import json
import os
import signal
import time
import random
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from redis import asyncio as redis

from app.controllers.dependencies import get_send_contact_use_case
from app.core.queue import RedisStreamsQueue
from app.settings import settings
from app.worker_metrics import (
    inc_dlq,
    inc_processed,
    inc_retry,
    observe_job_duration,
    set_lag,
    set_pel_size,
)

logger = structlog.get_logger(__name__)
MAX_RETRIES = 3


class StreamWorker:
    """
    Consumer for Redis Streams jobs.
    """

    def __init__(
        self,
        redis_url: str,
        stream_name: str = "contact_jobs",
        group_name: str = "email_workers",
        consumer_name: str = f"worker-{os.getpid()}",
    ):
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.running = True
        self._redis: redis.Redis | None = None

    async def _get_client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=None,  # Workers should not timeout on long polls
            )
        return self._redis

    async def setup(self):
        """Initializes the stream and consumer group."""
        client = await self._get_client()
        try:
            # Create consumer group if it doesn't exist
            # MKSTREAM ensures the stream is created if missing
            await client.xgroup_create(
                self.stream_name, self.group_name, id="0", mkstream=True
            )
            logger.info("consumer_group_created", group=self.group_name)
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info("consumer_group_exists", group=self.group_name)
            else:
                raise

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
            # Composition Root inside the worker
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

            # Check max age (15 min = 900s)
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

            # Re-enqueue before ACK to maintain at-least-once semantics
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

        # For terminal failures, publish to DLQ first, then ACK original.
        # This preserves durability if DLQ publish fails.
        await self._move_to_dlq(job_id, body, str(exc), type(exc).__name__)
        client = await self._get_client()
        await client.xack(self.stream_name, self.group_name, job_id)

    async def run(self):
        """Main loop for consuming jobs."""
        await self.setup()
        client = await self._get_client()

        logger.info("worker_started", consumer=self.consumer_name)

        while self.running:
            try:
                try:
                    pel_summary = await client.xpending(
                        self.stream_name, self.group_name
                    )
                    pending = (
                        pel_summary.get("pending", 0)
                        if isinstance(pel_summary, dict)
                        else int(pel_summary[0])
                        if pel_summary
                        else 0
                    )
                    set_lag(int(pending))
                except Exception:
                    pass

                # XAUTOCLAIM: Reclaim messages stuck in PEL for > 5 minutes
                claim_res = await client.xautoclaim(
                    self.stream_name,
                    self.group_name,
                    self.consumer_name,
                    min_idle_time=300000,
                    start_id="0",
                    count=1,
                )

                messages = []
                if claim_res and len(claim_res) > 1 and claim_res[1]:
                    messages = [(self.stream_name, claim_res[1])]
                    logger.info("job_reclaimed_from_pel", count=len(claim_res[1]))
                else:
                    # XREADGROUP: Read from stream as part of a group
                    response = await client.xreadgroup(
                        self.group_name,
                        self.consumer_name,
                        {self.stream_name: ">"},
                        count=1,
                        block=5000,
                    )
                    if not response:
                        continue
                    messages = response

                for stream, stream_messages in messages:
                    for job_id, data in stream_messages:
                        try:
                            started = time.perf_counter()
                            logger.info("job_processing_started", job_id=job_id)
                            await self.process_job(job_id, data)
                            await client.xack(self.stream_name, self.group_name, job_id)
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
                                    "job_processing_crash", job_id=job_id, error=str(e)
                                )
                                continue
                            inc_processed("failed", type(e).__name__)
                            logger.error(
                                "job_processing_crash", job_id=job_id, error=str(e)
                            )
                            # Note: We don't ACK if it crashes, so it stays in PEL for retry logic
                            # (A separate process would normally check for stale messages in PEL)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("worker_loop_error", error=str(e))
                await asyncio.sleep(1)  # Avoid tight loop on Redis error

    def stop(self):
        self.running = False


async def main():
    if not settings.redis_url:
        print("REDIS_URL not configured. Worker exiting.")
        return

    worker = StreamWorker(settings.redis_url)

    # Handle termination signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    try:
        await worker.run()
    finally:
        print("Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
