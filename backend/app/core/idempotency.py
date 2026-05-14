import threading
import time
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException, Request, status
from pydantic import BaseModel
from redis import asyncio as redis

from app.settings import settings


class IdempotencyRecord(BaseModel):
    """Record of a cached response."""

    status_code: int
    content: Any
    timestamp: float
    in_progress: bool = False


class IdempotencyStore:
    """
    In-memory store for idempotency keys with Redis-backed persistence.
    Falls back to memory if Redis is unavailable (fail-open strategy).
    In production, use Redis to share state across multiple instances.
    """

    def __init__(
        self, max_size: int = 100, ttl_seconds: int = 3600, lock_ttl_seconds: int = 30
    ):
        """
        WARNING: The fallback in-memory cache is only safe when running with a single worker.
        In multi-worker environments this will lead to race conditions unless Redis is configured.

        Args:
            max_size: Maximum number of keys held in the in-memory fallback cache.
            ttl_seconds: TTL for finalized idempotency results (default 1h).
            lock_ttl_seconds: TTL for in-progress locks (default 30s).
                              Kept short so a crashed process does not block retries for 1h.
        """
        self._cache: Dict[str, IdempotencyRecord] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock_ttl_seconds = lock_ttl_seconds
        self._lock = threading.Lock()
        self._redis = None

        if settings.redis_url and not settings.redis_url.startswith("memory://"):
            self._redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                health_check_interval=30,
                socket_timeout=settings.redis_socket_timeout_seconds,
                socket_connect_timeout=settings.redis_connect_timeout_seconds,
            )

    def _redis_key(self, key: str) -> str:
        return f"idempotency:{key}"

    async def _redis_get(self, key: str) -> Optional[IdempotencyRecord]:
        if not self._redis:
            return None

        try:
            payload = await self._redis.get(self._redis_key(key))
        except Exception:
            return None

        if not payload:
            return None

        try:
            return IdempotencyRecord.model_validate_json(payload)
        except Exception:
            await self._redis.delete(self._redis_key(key))
            return None

    def _memory_get(self, key: str) -> Optional[IdempotencyRecord]:
        """Retrieves a record from in-memory cache if not expired."""
        with self._lock:
            record = self._cache.get(key)
            if not record:
                return None

            # Evict expired entries
            if time.time() - record.timestamp > self.ttl_seconds:
                self._cache.pop(key, None)
                return None

            return record

    async def get(self, key: str) -> Optional[IdempotencyRecord]:
        record = await self._redis_get(key)
        if record is not None:
            return record

        return self._memory_get(key)

    async def set_in_progress(self, key: str) -> bool:
        """Marks a key as in-progress (locked). Returns True if successfully acquired."""
        if self._redis:
            record = IdempotencyRecord(
                status_code=0,
                content={},
                timestamp=time.time(),
                in_progress=True,
            )
            try:
                acquired = await self._redis.set(
                    self._redis_key(key),
                    record.model_dump_json(),
                    ex=self.lock_ttl_seconds,  # Short TTL: crash won't block retries for 1h
                    nx=True,
                )
                if acquired:
                    return True
            except Exception:
                pass

        with self._lock:
            if key in self._cache:
                record = self._cache[key]
                if time.time() - record.timestamp <= self.ttl_seconds:
                    return False
                # If expired, overwrite

            if len(self._cache) >= self.max_size:
                first = next(iter(self._cache))
                self._cache.pop(first, None)

            self._cache[key] = IdempotencyRecord(
                status_code=0, content={}, timestamp=time.time(), in_progress=True
            )
            return True

    async def set(self, key: str, status_code: int, content: Any):
        """Stores a finalized idempotency record with the given status code and content."""
        record = IdempotencyRecord(
            status_code=status_code,
            content=content,
            timestamp=time.time(),
            in_progress=False,
        )

        if self._redis:
            try:
                await self._redis.set(
                    self._redis_key(key),
                    record.model_dump_json(),
                    ex=self.ttl_seconds,
                )
                return
            except Exception:
                pass

        with self._lock:
            self._cache[key] = record

    async def release(self, key: str) -> None:
        """Releases an in-progress key to allow safe retries after a failure."""
        if self._redis:
            try:
                await self._redis.delete(self._redis_key(key))
                return
            except Exception:
                pass

        with self._lock:
            self._cache.pop(key, None)


# Global singleton — shared across all requests in the same process
store = IdempotencyStore()


class IdempotencyException(Exception):
    """Internal exception raised to short-circuit request processing and return a cached response."""

    def __init__(self, record: IdempotencyRecord):
        self.record = record
        super().__init__("Idempotency HIT")


async def verify_idempotency(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    legacy_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
):
    """
    FastAPI dependency to enforce idempotency on POST requests.

    Accepts the standard `Idempotency-Key` header or the legacy `X-Idempotency-Key`.
    - If the key has a finalized record: raises `IdempotencyException` with cached response.
    - If the key is already in-progress: raises HTTP 409 Conflict.
    - Otherwise: locks the key and returns it for the controller to finalize.
    """
    if request.method != "POST":
        return None

    effective_key = idempotency_key or legacy_idempotency_key

    if not effective_key:
        return None

    record = await store.get(effective_key)
    if record:
        if record.in_progress:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request already in progress",
            )
        raise IdempotencyException(record)

    # Lock key as in progress
    acquired = await store.set_in_progress(effective_key)
    if not acquired:
        record = await store.get(effective_key)
        if record and not record.in_progress:
            raise IdempotencyException(record)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Request already in progress"
        )

    return effective_key
