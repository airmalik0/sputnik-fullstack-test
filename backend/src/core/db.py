"""Async SQLAlchemy engine and session factory.

The original code instantiated an engine at module import time in two places
(`service.py` and `tasks.py`), which meant two pools per process and surprises
during testing. Here the engine is created lazily and cached, so:

  * Both FastAPI and the Celery worker share a single configured engine per
    process (each, of course, has its own process and therefore its own pool).
  * Tests can swap the engine by overriding `get_settings` before the first
    call to `get_engine`.

`expire_on_commit=False` is intentional: in the API layer we serialise ORM
objects after `await session.commit()`, and re-fetching attributes from a
closed session would otherwise raise.
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a session and guarantees rollback on error.

    The explicit rollback is defensive — SQLAlchemy already rolls back on the
    context manager exit if an exception propagated, but being explicit makes
    the intent obvious to a reader and protects against subtle bugs if a
    handler swallows the exception before it reaches us.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
