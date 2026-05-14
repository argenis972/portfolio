"""Redis-backed temporary storage for contact deduplication."""

from __future__ import annotations

import asyncio
import time

from redis.asyncio import Redis

from app.settings import settings


class SpamDedupStore:
    """Stores short-lived contact hashes outside PostgreSQL."""

    def __init__(self, redis_url: str | None):
        self._redis_client: Redis | None = (
            Redis.from_url(
                redis_url,
                decode_responses=True,
                health_check_interval=30,
                socket_timeout=settings.redis_socket_timeout_seconds,
                socket_connect_timeout=settings.redis_connect_timeout_seconds,
            )
            if redis_url and not redis_url.startswith("memory://")
            else None
        )
        self._memory_store: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _key(self, content_hash: str) -> str:
        return f"contact:dedupe:{content_hash}"

    async def reserve(self, content_hash: str, ttl_seconds: int) -> bool:
        """Returns True only when the hash did not exist yet. Fails open to memory if Redis is down."""
        if self._redis_client is not None:
            try:
                created = await self._redis_client.set(
                    self._key(content_hash),
                    "1",
                    ex=ttl_seconds,
                    nx=True,
                )
                return bool(created)
            except Exception as e:
                import structlog

                logger = structlog.get_logger(__name__)
                logger.warning(
                    "spam_store_redis_failure_falling_back_to_memory", error=str(e)
                )
                # Proceed to memory fallback

        now = time.time()
        async with self._lock:
            expires_at = self._memory_store.get(content_hash)
            if expires_at and expires_at > now:
                return False

            self._memory_store[content_hash] = now + ttl_seconds
            expired_keys = [
                key for key, expiry in self._memory_store.items() if expiry <= now
            ]
            for key in expired_keys:
                self._memory_store.pop(key, None)
            return True

    async def release(self, content_hash: str) -> None:
        """Releases a previously reserved hash after a failed request."""
        if self._redis_client is not None:
            try:
                await self._redis_client.delete(self._key(content_hash))
                return
            except Exception:
                pass

        async with self._lock:
            self._memory_store.pop(content_hash, None)

    async def clear(self) -> None:
        """Clears the in-memory store for test isolation."""
        if self._redis_client is not None:
            return

        async with self._lock:
            self._memory_store.clear()


spam_dedup_store = SpamDedupStore(settings.redis_url)
