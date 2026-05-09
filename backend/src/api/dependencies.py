"""FastAPI dependency wiring.

This is the single place where the object graph is assembled for an HTTP
request. Routers depend on services through `Depends(...)`, so swapping
an implementation (e.g. for tests) means overriding one provider, not
chasing imports across the codebase.

The Celery layer wires its own object graph in `src.tasks.celery_app` —
duplicating the construction is intentional, because each process has
its own session lifecycle and the two pipelines should not share state.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.db import get_session
from src.repositories.alert_repository import AlertRepository
from src.repositories.file_repository import FileRepository
from src.services.alert_service import AlertService
from src.services.file_service import FileService
from src.services.scan_service import ScanService
from src.storage.base import FileStorage
from src.storage.local import LocalFileStorage


@lru_cache(maxsize=1)
def _build_storage() -> FileStorage:
    # Cached so we don't re-create the storage object (and re-run mkdir)
    # on every request. Reads from get_settings() directly because
    # Settings instances are not hashable (Pydantic models don't implement
    # __hash__) — passing one through lru_cache would TypeError.
    return LocalFileStorage(get_settings().storage_dir)


def get_storage() -> FileStorage:
    return _build_storage()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    # Wrap the core dependency so the rest of the API only imports from
    # this module. Tests can override `get_db_session` to inject a session
    # bound to a sandbox database.
    async for session in get_session():
        yield session


def get_file_service(
    session: AsyncSession = Depends(get_db_session),
    storage: FileStorage = Depends(get_storage),
) -> FileService:
    return FileService(repository=FileRepository(session), storage=storage)


def get_alert_service(
    session: AsyncSession = Depends(get_db_session),
) -> AlertService:
    return AlertService(repository=AlertRepository(session))


def get_scan_service(
    settings: Settings = Depends(get_settings),
) -> ScanService:
    return ScanService(suspicious_size_bytes=settings.suspicious_size_bytes)


# Surface the session itself for endpoints that need to commit at request
# scope (file create / update / delete). Keeping the commit explicit at
# the router avoids hidden auto-commit behaviour and makes failure modes
# obvious to a reader.
def get_request_session(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncSession:
    return session
