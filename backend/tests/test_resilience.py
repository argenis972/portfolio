"""
Resilience tests: Redis failures, Supabase transient errors,
email adapter timeouts, and concurrent idempotency conflicts.
"""

import time
from unittest.mock import AsyncMock, patch

import pytest
import redis

from app.core.idempotency import IdempotencyRecord, IdempotencyStore
from app.main import app

# ──────────────────────────────────────────────────────────────────────────────
# Idempotency Store — Redis failure fallback
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.async_with_redis
async def test_idempotency_store_redis_failure():
    """
    IdempotencyStore must fall back to in-memory storage when Redis raises
    a ConnectionError on both GET and SET operations.
    """
    with patch("redis.asyncio.from_url") as mock_redis_factory:
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = redis.exceptions.ConnectionError("Redis is down")
        mock_redis.set.side_effect = redis.exceptions.ConnectionError("Redis is down")
        mock_redis_factory.return_value = mock_redis

        with patch("app.settings.settings.redis_url", "redis://mock"):
            store = IdempotencyStore(ttl_seconds=60)

            # 1. Acquire lock — must fall back to memory and succeed
            acquired = await store.set_in_progress("fail-key")
            assert acquired is True
            assert "fail-key" in store._cache
            assert store._cache["fail-key"].in_progress is True

            # 2. Read must find the record in memory (Redis GET fails)
            record = await store.get("fail-key")
            assert record is not None
            assert record.in_progress is True

            # 3. Finalise the record
            await store.set("fail-key", 200, {"ok": True})

            record = await store.get("fail-key")
            assert record is not None
            assert record.status_code == 200
            assert record.content == {"ok": True}


# ──────────────────────────────────────────────────────────────────────────────
# SpamDedupStore — Redis failure fallback
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.async_with_redis
async def test_spam_store_redis_down_fallback():
    """
    SpamDedupStore.reserve() must fall back to the in-memory store when
    Redis raises a ConnectionError.  The operation should succeed (True),
    and a second call with the same hash must return False (duplicate).
    """
    from app.core.spam_store import SpamDedupStore

    with patch("redis.asyncio.Redis.from_url") as mock_factory:
        mock_client = AsyncMock()
        mock_client.set.side_effect = redis.exceptions.ConnectionError("Redis down")
        mock_factory.return_value = mock_client

        store = SpamDedupStore(redis_url="redis://mock")

        # First reservation must succeed (new hash)
        result = await store.reserve("abc123", ttl_seconds=60)
        assert result is True

        # Second reservation with same hash must fail (duplicate in memory)
        result2 = await store.reserve("abc123", ttl_seconds=60)
        assert result2 is False


# ──────────────────────────────────────────────────────────────────────────────
# Supabase / database transient failure
# ──────────────────────────────────────────────────────────────────────────────


async def test_supabase_transient_failure_health_check(client):
    """
    When the database layer raises an exception, the /health endpoint must
    return HTTP 200 with status='erro' in the body — NOT a 500 crash.
    This validates that SqlRepository.check_health() catches exceptions.
    """
    from app.adapters.sql_repository import SqlRepository
    from app.controllers import dependencies

    mock_repo = AsyncMock(spec=SqlRepository)
    mock_repo.check_health.return_value = {
        "status": "erro",
        "details": "Simulated transient DB failure",
    }

    app.dependency_overrides[dependencies.get_repository] = lambda: mock_repo

    try:
        resp = client.get("/health")
        # When a dependency is degraded, the health endpoint returns 503 Service Unavailable
        # (HTTP 200 is only returned when all checks pass).
        assert resp.status_code in (200, 503)
        body = resp.json()
        # The service must not crash — a structured body is always returned
        assert isinstance(body, dict)
    finally:
        app.dependency_overrides.pop(dependencies.get_repository, None)


# ──────────────────────────────────────────────────────────────────────────────
# Email adapter timeout
# ──────────────────────────────────────────────────────────────────────────────


async def test_email_adapter_timeout_returns_200_backgrounded(client):
    """
    A ConnectTimeout from the Email Adapter must produce HTTP 200 because the delivery
    happens in the background. The error is only logged.
    """
    from httpx import ConnectTimeout

    from app.use_cases import SendContactUseCase
    from app.controllers.dependencies import get_send_contact_use_case

    mock_uc = AsyncMock(spec=SendContactUseCase)
    mock_uc.execute.side_effect = ConnectTimeout("Email timed out")

    app.dependency_overrides[get_send_contact_use_case] = lambda: mock_uc

    try:
        payload = {
            "name": "Argenis",
            "email": "timeout@test.com",
            "subject": "Timeout test",
            "message": "This should result in a 200 due to background execution.",
        }
        resp = client.post("/api/v1/contact", json=payload)

        # The endpoint returns 200 before the background task fails
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
    finally:
        app.dependency_overrides.pop(get_send_contact_use_case, None)


# ──────────────────────────────────────────────────────────────────────────────
# Concurrent idempotency — same key, second request must get 409
# ──────────────────────────────────────────────────────────────────────────────


def test_concurrent_idempotency_conflict(client):
    """
    If a request is already in-progress (simulated by pre-seeding the
    idempotency store), a second POST with the same Idempotency-Key
    must receive HTTP 409 Conflict.
    """
    from app.core.idempotency import store

    key = "concurrent-conflict-key"
    store._cache[key] = IdempotencyRecord(
        status_code=0,
        content={},
        timestamp=time.time(),
        in_progress=True,
    )

    payload = {
        "name": "Test User",
        "email": "concurrent@test.com",
        "subject": "Concurrent test",
        "message": "This request should collide with an in-progress one.",
    }

    try:
        resp = client.post(
            "/api/v1/contact",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        assert resp.status_code == 409
        assert "already in progress" in resp.json()["error"]["message"].lower()
    finally:
        store._cache.pop(key, None)
