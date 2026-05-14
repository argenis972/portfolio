"""
Centralized infrastructure lifecycle management.

Handles graceful startup/shutdown of shared resources (DB engine, Redis connections).

Design decision: uses a module-level registry instead of depending on lru_cache'd
factories in shutdown hooks. This avoids issues when tests replace or mock adapters
because the engine reference is registered at construction time, not resolved at
shutdown time.
"""

import structlog
from redis import asyncio as redis

from app.settings import settings

logger = structlog.get_logger(__name__)

# Registry of async engines to dispose on shutdown.
# Populated by SqlRepository.__init__ via register_engine().
_engine_registry: list = []
_redis_client: redis.Redis | None = None


def register_engine(engine) -> None:
    """Registers an async SQLAlchemy engine for lifecycle management.

    Called by SqlRepository.__init__ so the engine is tracked without
    depending on the DI container at shutdown time.
    """
    _engine_registry.append(engine)
    logger.debug("db_engine_registered", engine_id=id(engine))


async def dispose_all() -> None:
    """Disposes all registered DB connection pools (graceful shutdown).

    Should be called from FastAPI's lifespan context manager on application exit.
    Safe to call multiple times — each engine is disposed and removed from registry.
    """
    while _engine_registry:
        engine = _engine_registry.pop()
        try:
            await engine.dispose()
            logger.info("db_engine_disposed", engine_id=id(engine))
        except Exception as e:
            logger.error(
                "db_engine_dispose_failed",
                engine_id=id(engine),
                error=str(e),
            )

    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
            logger.info("redis_client_closed")
        except Exception as e:
            logger.error("redis_client_close_failed", error=str(e))
        finally:
            _redis_client = None


def init_redis(redis_url: str | None = None) -> redis.Redis | None:
    """Initializes and returns the shared Redis client singleton."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    effective_url = redis_url or settings.redis_url
    if not effective_url:
        logger.warning("redis_not_configured")
        return None

    _redis_client = redis.from_url(
        effective_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    logger.info("redis_client_initialized")
    return _redis_client


def get_redis() -> redis.Redis:
    """Returns the shared Redis client, initializing it if needed."""
    client = init_redis()
    if client is None:
        raise RuntimeError("Redis is not configured")
    return client
