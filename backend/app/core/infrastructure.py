"""
Centralized infrastructure lifecycle management.

Handles graceful startup/shutdown of shared resources (DB engine, Redis connections).

Design decision: uses a module-level registry instead of depending on lru_cache'd
factories in shutdown hooks. This avoids issues when tests replace or mock adapters
because the engine reference is registered at construction time, not resolved at
shutdown time.
"""

import structlog

logger = structlog.get_logger(__name__)

# Registry of async engines to dispose on shutdown.
# Populated by SqlRepository.__init__ via register_engine().
_engine_registry: list = []


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
