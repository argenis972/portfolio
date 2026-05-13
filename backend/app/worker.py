"""
Worker process for consuming jobs from Redis Streams.
"""

import asyncio
import json
import os
import signal
from typing import Any, Dict

import structlog
from redis import asyncio as redis

from app.controllers.dependencies import get_send_contact_use_case
from app.settings import settings

logger = structlog.get_logger(__name__)


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

    async def process_job(self, job_id: str, data: Dict[str, Any]):
        """Dispatches the job to the appropriate use case."""
        job_name = data.get("job_name")
        payload_str = data.get("payload")

        if not job_name or not payload_str:
            logger.error("invalid_job_data", job_id=job_id)
            return

        payload = json.loads(payload_str)

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
                # In a real scenario, we might want to retry or move to DLQ
                # For now, we log it and ACK so it doesn't block the stream
                logger.error("email_delivery_failed_in_worker", job_id=job_id)

    async def run(self):
        """Main loop for consuming jobs."""
        await self.setup()
        client = await self._get_client()

        logger.info("worker_started", consumer=self.consumer_name)

        while self.running:
            try:
                # XREADGROUP: Read from stream as part of a group
                # ">" means read new messages never delivered to any other consumer
                # Count 1: Process one by one for simplicity and safety
                # Block 5000: Wait up to 5s if no messages
                response = await client.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    {self.stream_name: ">"},
                    count=1,
                    block=5000,
                )

                if not response:
                    continue

                for stream, messages in response:
                    for job_id, data in messages:
                        try:
                            await self.process_job(job_id, data)
                            # ACK the message so it's removed from PEL (Pending Entries List)
                            await client.xack(self.stream_name, self.group_name, job_id)
                        except Exception as e:
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
